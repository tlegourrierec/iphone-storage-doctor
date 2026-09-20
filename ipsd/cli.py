"""Interface en ligne de commande.

    ipsd            diagnostic complet
    ipsd storage    juste les compteurs, instantané
    ipsd apps       classement des applications
    ipsd clean      nettoyage (simulation par défaut)
"""
from __future__ import annotations

import asyncio
import functools
import sys
from pathlib import Path

import click
from pymobiledevice3.exceptions import (
    DeviceNotFoundError,
    PyMobileDevice3Exception,
)
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from . import (
    __version__,
)
from . import (
    actions as actions_mod,
)
from . import (
    apps as apps_mod,
)
from . import (
    battery as battery_mod,
)
from . import (
    clean as clean_mod,
)
from . import (
    crash as crash_mod,
)
from . import (
    history as history_mod,
)
from . import (
    purge as purge_mod,
)
from .device import DeviceError, connect, get_disk_usage, get_info
from .i18n import (
    SUPPORTED,
    configured_language,
    current,
    save_language,
    set_language,
    t,
)
from .report import (
    action_plan,
    apps_table,
    console,
    device_panel,
    findings_table,
    levels_table,
    storage_table,
    to_json,
)
from .rules import SAFE, analyse_apps, analyse_crashes, analyse_media, sort_findings
from .scan import MediaScanner
from .units import human

err = Console(stderr=True)


def coro(fn):
    """Adapte une commande asynchrone à click.

    Une opération longue survit rarement au débranchement du câble. Plutôt
    qu'une trace Python, on dit ce qui s'est passé et ce qui a déjà été fait.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return asyncio.run(fn(*args, **kwargs))
        except DeviceError as exc:
            err.print(f"[bold red]✗[/bold red] {exc}")
            sys.exit(2)
        except DeviceNotFoundError:
            err.print("[bold red]✗[/bold red] " + t("device.disconnected"))
            sys.exit(2)
        except (BrokenPipeError, ConnectionError, TimeoutError) as exc:
            # Le lien USB a lâché en cours d'échange : câble, veille de
            # l'appareil, ou session lockdown fermée par iOS.
            err.print("[bold red]✗[/bold red] " + t("device.link_lost"))
            err.print(f"[dim]{type(exc).__name__}[/dim]")
            sys.exit(2)
        except PyMobileDevice3Exception as exc:
            err.print(
                "[bold red]✗[/bold red] "
                + t("device.refused", name=type(exc).__name__)
            )
            sys.exit(2)
        except KeyboardInterrupt:
            err.print("\n[yellow]" + t("cli.interrupted") + "[/yellow]")
            sys.exit(130)

    return wrapper


def confirm_deletion(what: str, count: int, size: str, assume_yes: bool) -> bool:
    """Demande l'accord avant toute suppression sur l'appareil.

    Rien n'est jamais supprimé sur la seule présence de --apply. Hors terminal
    interactif, on refuse plutôt que de supposer un accord.
    """
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        err.print("[bold red]✗[/bold red] " + t("cli.confirm.no_tty"))
        return False
    console.print(
        "\n" + t("cli.confirm.header", count=count, size=size, what=what)
    )
    console.print("[dim]" + t("cli.confirm.copy_note") + "[/dim]")
    return click.confirm(t("cli.confirm.question"), default=False)


udid_option = click.option("--udid", default=None, help="Target a specific device.")
json_option = click.option("--json", "as_json", is_flag=True, help="JSON output.")


LANGUAGE_NAMES = {"en": "English", "fr": "Français"}


def choose_language_once() -> None:
    """Demande la langue au tout premier lancement, puis la mémorise.

    Homebrew et pipx ne peuvent rien demander pendant l'installation : c'est
    donc ici que ça se joue. Hors terminal, on se rabat silencieusement sur la
    locale du système.
    """
    if configured_language() is not None or not sys.stdin.isatty():
        return
    options = list(SUPPORTED)
    console.print()
    console.print("[bold]Choose your language / Choisis ta langue[/bold]")
    for index, code in enumerate(options, start=1):
        console.print(f"  {index}. {LANGUAGE_NAMES[code]}")
    answer = click.prompt(
        "  ", type=click.IntRange(1, len(options)), default=1, show_default=False
    )
    chosen = options[answer - 1]
    set_language(chosen)
    save_language(chosen)
    console.print("[green]OK[/green] " + t("cli.lang.saved") + "\n")


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="iphone-storage-doctor")
@click.option(
    "--lang",
    type=click.Choice(SUPPORTED),
    default=None,
    help="Language for this run (en, fr).",
)
@click.pass_context
def main(ctx, lang):
    """Diagnose and clean an iPhone's storage over USB."""
    set_language(lang)
    if not lang and ctx.invoked_subcommand != "lang":
        choose_language_once()
    if ctx.invoked_subcommand is None:
        ctx.invoke(doctor)


@main.command("lang")
@click.argument("language", type=click.Choice(SUPPORTED), required=False)
def lang_cmd(language):
    """Show or change the interface language."""
    if language:
        set_language(language)
        path = save_language(language)
        console.print("[green]OK[/green] " + t("cli.lang.saved"))
        console.print(f"[dim]{path}[/dim]")
        return
    console.print(t("cli.lang.current", lang=LANGUAGE_NAMES[current()]))
    console.print(f"[dim]ipsd lang {' | '.join(SUPPORTED)}[/dim]")


@main.command()
@udid_option
@json_option
@coro
async def storage(udid, as_json):
    """Storage counters, without walking the files (instant)."""
    lockdown = await connect(udid)
    info = await get_info(lockdown)
    disk = await get_disk_usage(lockdown)
    if as_json:
        click.echo(to_json({"device": info, "disk": disk}))
        return
    device_panel(info, disk)
    storage_table(disk, media_bytes=0, apps_bytes=0, measured=False)


@main.command("apps")
@udid_option
@json_option
@click.option("--limit", default=20, show_default=True, help="How many apps to show.")
@click.option("--user-only", is_flag=True, help="Exclude system apps.")
@coro
async def apps_cmd(udid, as_json, limit, user_only):
    """Rank applications by the space they occupy."""
    lockdown = await connect(udid)
    with console.status(t("cli.status.apps")):
        found = await apps_mod.collect(lockdown, include_system=not user_only)
    if as_json:
        click.echo(to_json({"apps": found}))
        return
    apps_table(found, limit=limit)
    total = sum(a.total for a in found)
    console.print("\n" + t("cli.apps.total", count=len(found), size=human(total)))


@main.command()
@udid_option
@json_option
@click.option(
    "--profile",
    type=click.Choice(["fast", "deep"]),
    default="deep",
    show_default=True,
    help="'fast' skips the largest photo-library subtrees.",
)
@click.option("--no-apps", is_flag=True, help="Skip measuring applications.")
@click.option("--no-media", is_flag=True, help="Skip walking the media volume.")
@coro
async def doctor(udid, as_json, profile, no_apps, no_media):
    """Full diagnosis: where the space went, and what is reclaimable."""
    lockdown = await connect(udid)
    info = await get_info(lockdown)
    disk = await get_disk_usage(lockdown)

    findings = []
    media_bytes = 0
    scan = None
    app_list = []

    if not no_apps:
        with console.status(t("cli.status.apps_slow")):
            app_list = await apps_mod.collect(lockdown)
        findings += analyse_apps(app_list)

    if not no_media:
        async with MediaScanner(lockdown, profile=profile) as scanner:
            with console.status(t("cli.status.media")) as status:

                def progress(count, path):
                    status.update(t("cli.status.media_count", count=count))

                scan = await scanner.scan(on_progress=progress)
        media_bytes = scan.total_size
        findings += analyse_media(scan)

    health = await battery_mod.collect(lockdown, info.product_type)

    try:
        crashes = await crash_mod.collect(lockdown)
        findings += analyse_crashes(crashes)
    except Exception:  # noqa: BLE001 - service optionnel
        pass

    findings = sort_findings(findings)
    apps_bytes = sum(a.total for a in app_list)

    if as_json:
        click.echo(
            to_json(
                {
                    "device": info,
                    "disk": disk,
                    "media_bytes": media_bytes,
                    "apps_bytes": apps_bytes,
                    "battery": health,
                    "findings": findings,
                    "apps": app_list[:50],
                }
            )
        )
        return

    device_panel(info, disk)
    storage_table(disk, media_bytes=media_bytes, apps_bytes=apps_bytes)
    if health is not None:
        colour = {
            battery_mod.HEALTHY: "green",
            battery_mod.AGING: "yellow",
            battery_mod.WORN: "red",
        }[health.state]
        console.print()
        console.print(
            t("battery.label.health")
            + f": [bold {colour}]{health.health_percent:.0f} %[/bold {colour}], "
            + f"{health.cycle_count} "
            + t("battery.label.cycles").lower()
            + f". [dim]{health.verdict()}[/dim]"
        )
    console.print()
    findings_table(findings)
    if app_list:
        console.print()
        apps_table(app_list, limit=10)
    if scan is not None:
        console.print(
            f"\n[dim]{len(scan.files)} fichiers parcourus en {scan.duration_s:.0f} s"
            + (f", {len(scan.errors)} dossiers illisibles" if scan.errors else "")
            + ".[/dim]"
        )
    action_plan(actions_mod.build(findings, app_list, health, disk))


@main.command()
@udid_option
@click.option("--apply", "do_apply", is_flag=True, help="Actually delete.")
@click.option(
    "--no-quarantine",
    is_flag=True,
    help="Delete without copying to the Mac first.",
)
@click.option(
    "--quarantine-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Archive directory (default: ~/iphone-storage-doctor/quarantine).",
)
@click.option("--crash", "do_crash", is_flag=True, help="Also handle crash reports.")
@click.option("--yes", is_flag=True, help="Skip the confirmation (for scripts).")
@coro
async def clean(udid, do_apply, no_quarantine, quarantine_dir, do_crash, yes):
    """Delete files classified SAFE. Dry run by default."""
    lockdown = await connect(udid)

    async with MediaScanner(lockdown, profile="deep") as scanner:
        with console.status(t("cli.status.searching")):
            scan = await scanner.scan()
    findings = [f for f in analyse_media(scan) if f.tier == SAFE]
    sizes = {f.path: f.size for f in scan.files}

    targets = clean_mod.selectable(findings)
    if not targets and not do_crash:
        console.print("[green]" + t("cli.clean.nothing") + "[/green]")
        return

    for f in targets:
        console.print(f"  [green]•[/green] {f.title} — {human(f.bytes)} ({f.count} fichiers)")

    plan = clean_mod.build_plan(findings, sizes)
    if do_apply and not plan.is_empty:
        if not confirm_deletion(
            ", ".join(f.title.lower() for f in plan.findings),
            len(plan.paths),
            human(plan.total_bytes),
            yes,
        ):
            console.print("[yellow]" + t("cli.cancelled") + "[/yellow]")
            return

    report = await clean_mod.run(
        lockdown,
        findings,
        dry_run=not do_apply,
        quarantine=not no_quarantine,
        quarantine_dir=quarantine_dir,
        sizes=sizes,
    )

    if not do_apply:
        console.print(
            f"\n[yellow]Simulation.[/yellow] {report.planned} fichiers, "
            f"[bold]{human(report.planned_bytes)}[/bold] seraient libérés."
        )
        console.print("[dim]" + t("cli.clean.rerun") + "[/dim]")
    else:
        console.print(
            f"\n[green]✓[/green] {report.deleted} fichiers supprimés, "
            f"[bold]{human(report.deleted_bytes)}[/bold] libérés."
        )
        if report.quarantine_dir:
            console.print("[dim]" + t("cli.clean.backup", path=report.quarantine_dir) + "[/dim]")
        for failure in report.failures[:5]:
            console.print(f"[red]✗[/red] {failure}")

    if do_crash:
        dest = (quarantine_dir or clean_mod.DEFAULT_QUARANTINE) / "crash-reports"
        crashes = await crash_mod.collect(lockdown)
        if not crashes.count:
            console.print("\n[dim]" + t("cli.crash.none") + "[/dim]")
        elif not do_apply:
            console.print("\n[yellow]" + t("cli.crash.dry_run", count=crashes.count) + "[/yellow]")
        elif not confirm_deletion(
            t("cli.crash.label"), crashes.count, "", yes
        ):
            console.print("[yellow]" + t("cli.crash.kept") + "[/yellow]")
        else:
            size = await crash_mod.archive_and_clear(lockdown, dest, erase=True)
            console.print(
                f"[green]✓[/green] {crashes.count} rapports archivés dans {dest} "
                f"({human(size)}) puis effacés."
            )


@main.command()
@udid_option
@click.option("--app", "wanted", multiple=True, help="Bundle id or name. Repeatable.")
@click.option("--top", type=int, default=None, help="Target the N heaviest apps.")
@click.option(
    "--min-data",
    type=int,
    default=200,
    show_default=True,
    help="Data threshold in MB for an app to be offered.",
)
@click.option("--apply", "do_apply", is_flag=True, help="Actually uninstall.")
@click.option(
    "--force-risky",
    is_flag=True,
    help="Allow apps flagged as risky (2FA, messengers...).",
)
@click.option("--yes", is_flag=True, help="Skip the interactive confirmation.")
@coro
async def purge(udid, wanted, top, min_data, do_apply, force_risky, yes):
    """Uninstall apps to reclaim their cache. Dry run by default.

    iOS does not let a Mac clear an app's cache. Uninstalling is the only
    lever - at the cost of that app's local data.
    """
    lockdown = await connect(udid)
    with console.status(t("cli.status.apps")):
        app_list = await apps_mod.collect(lockdown)
    before = await get_disk_usage(lockdown)

    missing: list[str] = []
    if wanted:
        chosen, missing = purge_mod.select(app_list, wanted)
    else:
        pool = purge_mod.candidates(app_list, min_data=min_data * 1_000_000)
        chosen = pool[:top] if top else pool

    for term in missing:
        err.print("[yellow]![/yellow] " + t("cli.purge.no_match", term=term))
    if not chosen:
        console.print("[green]" + t("cli.purge.below_threshold") + "[/green]")
        return

    table = Table(title=t("cli.purge.title"), show_edge=False, header_style="dim")
    table.add_column(t("report.col.app"))
    table.add_column(t("cli.purge.col.reclaimed"), justify="right")
    table.add_column(t("cli.purge.col.of_data"), justify="right")
    table.add_column(t("cli.purge.col.risk"))
    for c in chosen:
        risky = c.is_risky
        table.add_row(
            Text(c.app.name, style="red" if risky else ""),
            human(c.gain),
            human(c.app.data_bytes),
            Text("⚠ " + (c.risk or ""), style="red") if risky else Text("—", style="dim"),
        )
    console.print(table)

    safe = [c for c in chosen if not c.is_risky]
    risky = [c for c in chosen if c.is_risky]
    effective = chosen if force_risky else safe
    console.print(
        f"\nGain estimé : [bold]{human(sum(c.gain for c in effective))}[/bold]"
        f" sur {len(effective)} app(s)."
    )
    if risky and not force_risky:
        console.print(
            f"[yellow]{len(risky)} app(s) écartée(s)[/yellow] pour risque de perte "
            "de données. [dim]--force-risky pour passer outre, à tes risques.[/dim]"
        )

    if not do_apply:
        console.print("\n[yellow]" + t("cli.purge.untouched") + "[/yellow]")
        console.print("[dim]" + t("cli.purge.add_apply") + "[/dim]")
        return
    if not effective:
        console.print("\n[yellow]" + t("cli.purge.nothing") + "[/yellow]")
        return

    console.print(
        "\n[bold red]Les données locales de ces apps seront effacées "
        "définitivement.[/bold red] Le binaire se retéléchargera depuis l'App Store."
    )
    if not yes:
        word = t("cli.purge.confirm_word")
        answer = click.prompt(
            t("cli.purge.confirm_prompt", word=word), default="", show_default=False
        )
        if answer.strip() != word:
            console.print("[yellow]" + t("cli.cancelled") + "[/yellow]")
            return

    with console.status(t("cli.status.uninstalling")):
        report = await purge_mod.run(
            lockdown, chosen, dry_run=False, allow_risky=force_risky
        )
        after = await get_disk_usage(lockdown)

    report.freed_measured = max(0, after.free - before.free)
    console.print(
        f"\n[green]✓[/green] {len(report.removed)} app(s) désinstallée(s), "
        f"estimation [bold]{human(report.freed_estimate)}[/bold]."
    )
    console.print(
        t(
            "cli.purge.measured",
            before=human(before.free),
            after=human(after.free),
            delta=human(report.freed_measured),
        )
    )
    for name, reason in report.skipped:
        console.print("[yellow]-[/yellow] " + t("cli.purge.spared", name=name, reason=reason))
    for failure in report.failures:
        console.print(f"[red]✗[/red] {failure}")


@main.command()
@udid_option
@click.option("--yes", is_flag=True, help="Skip the confirmation.")
@coro
async def restart(udid, yes):
    """Restart the iPhone: frees RAM and purges temporary files."""
    lockdown = await connect(udid)
    console.print("[dim]" + t("cli.restart.note") + "[/dim]")
    if not yes and not click.confirm(t("cli.restart.confirm"), default=False):
        console.print("[yellow]" + t("cli.cancelled") + "[/yellow]")
        return
    from pymobiledevice3.services.diagnostics import DiagnosticsService

    async with DiagnosticsService(lockdown) as diag:
        await diag.restart()
    console.print("[green]OK[/green] " + t("cli.restart.done"))


@main.command()
@udid_option
@json_option
@coro
async def plan(udid, as_json):
    """The three cleaning levels, and what each one reclaims."""
    lockdown = await connect(udid)
    info = await get_info(lockdown)
    disk = await get_disk_usage(lockdown)
    health = await battery_mod.collect(lockdown, info.product_type)

    with console.status(t("cli.status.apps")):
        app_list = await apps_mod.collect(lockdown)
    async with MediaScanner(lockdown, profile="deep") as scanner:
        with console.status(t("cli.status.media")) as status:

            def progress(count, path):
                status.update(t("cli.status.media_count", count=count))

            scan = await scanner.scan(on_progress=progress)

    findings = analyse_media(scan)
    try:
        findings += analyse_crashes(await crash_mod.collect(lockdown))
    except Exception:  # noqa: BLE001 - service optionnel
        pass

    levels = actions_mod.build_levels(findings, app_list, health, disk)
    if as_json:
        click.echo(to_json({"device": info, "disk": disk, "levels": levels}))
        return

    device_panel(info, disk)
    levels_table(levels, free_before=disk.free)


@main.command()
@udid_option
@click.option("--apply", "do_apply", is_flag=True, help="Actually run the cleanup.")
@click.option("--no-quarantine", is_flag=True, help="Delete without copying to the Mac.")
@click.option("--yes", is_flag=True, help="Skip the confirmation (for scripts).")
@coro
async def boost(udid, do_apply, no_quarantine, yes):
    """Measure, clean safely, measure again. The whole report in one command."""
    lockdown = await connect(udid)
    info = await get_info(lockdown)

    before = await get_disk_usage(lockdown)
    health = await battery_mod.collect(lockdown, info.product_type)
    crashes_before = await crash_mod.collect(lockdown)

    device_panel(info, before)
    console.print(Rule("[bold]" + t("cli.boost.before") + "[/bold]", style="dim"))
    before_tbl = Table(show_edge=False, show_header=False, box=None)
    before_tbl.add_row(t("cli.boost.free"), f"[bold]{human(before.free)}[/bold]")
    before_tbl.add_row(t("cli.boost.used"), human(before.data_used))
    if health is not None:
        colour = {
            battery_mod.HEALTHY: "green",
            battery_mod.AGING: "yellow",
            battery_mod.WORN: "red",
        }[health.state]
        before_tbl.add_row(
            t("cli.boost.battery"),
            f"[bold {colour}]{health.health_percent:.0f} %[/bold {colour}] "
            f"[dim]({health.cycle_count} cycles)[/dim]",
        )
    before_tbl.add_row(t("cli.boost.crashes"), str(crashes_before.count))
    console.print(before_tbl)

    console.print()
    console.print(Rule("[bold]" + t("cli.boost.cleaning") + "[/bold]", style="dim"))
    async with MediaScanner(lockdown, profile="deep") as scanner:
        with console.status(t("cli.status.searching")) as status:

            def progress(count, path):
                status.update(t("cli.status.media_count", count=count))

            scan = await scanner.scan(on_progress=progress)
    findings = [f for f in analyse_media(scan) if f.tier == SAFE]
    sizes = {f.path: f.size for f in scan.files}
    for f in clean_mod.selectable(findings):
        console.print(f"  [green]•[/green] {f.title} — {human(f.bytes)} ({f.count} fichiers)")

    plan = clean_mod.build_plan(findings, sizes)
    if do_apply and (not plan.is_empty or crashes_before.count):
        what = ", ".join(f.title.lower() for f in plan.findings) or "rapports de plantage"
        if not confirm_deletion(
            what,
            len(plan.paths) + crashes_before.count,
            human(plan.total_bytes),
            yes,
        ):
            console.print("[yellow]" + t("cli.cancelled") + "[/yellow]")
            return

    report = await clean_mod.run(
        lockdown,
        findings,
        dry_run=not do_apply,
        quarantine=not no_quarantine,
        sizes=sizes,
    )
    crash_bytes = 0
    if do_apply and crashes_before.count:
        dest = clean_mod.DEFAULT_QUARANTINE / "crash-reports"
        crash_bytes = await crash_mod.archive_and_clear(lockdown, dest, erase=True)
        console.print(
            f"  [green]•[/green] Rapports de plantage — {crashes_before.count} "
            f"archivés puis effacés"
        )

    if not do_apply:
        console.print(
            f"\n[yellow]Simulation.[/yellow] {report.planned} fichiers, "
            f"[bold]{human(report.planned_bytes)}[/bold] seraient libérés."
        )
        console.print("[dim]" + t("cli.clean.rerun") + "[/dim]")
        return

    after = await get_disk_usage(lockdown)
    console.print()
    console.print(Rule("[bold]" + t("cli.boost.after") + "[/bold]", style="dim"))

    result = Table(show_edge=False, header_style="dim")
    result.add_column("")
    result.add_column(t("cli.boost.before"), justify="right")
    result.add_column(t("cli.boost.after"), justify="right")
    result.add_column(t("cli.boost.delta"), justify="right")
    delta_free = after.free - before.free
    result.add_row(
        t("cli.boost.free"),
        human(before.free),
        Text(human(after.free), style="bold"),
        Text(
            f"{'+' if delta_free >= 0 else '−'}{human(abs(delta_free))}",
            style="green" if delta_free >= 0 else "red",
        ),
    )
    result.add_row(
        t("cli.boost.used"),
        human(before.data_used),
        human(after.data_used),
        human(abs(after.data_used - before.data_used)),
    )
    console.print(result)

    console.print(
        f"\n[green]✓[/green] {report.deleted} fichiers supprimés "
        f"({human(report.deleted_bytes + crash_bytes)} de contenu retiré)."
    )
    if report.quarantine_dir:
        console.print("[dim]" + t("cli.clean.backup", path=report.quarantine_dir) + "[/dim]")
    for failure in report.failures[:3]:
        console.print(f"[red]✗[/red] {failure}")

    with console.status(t("cli.status.apps")):
        app_list = await apps_mod.collect(lockdown)
    remaining = analyse_media(scan) + analyse_apps(app_list)
    action_plan(actions_mod.build(remaining, app_list, health, after))


@main.command()
@udid_option
@json_option
@coro
async def battery(udid, as_json):
    """Real battery health - the top cause of slowness on an older device."""
    lockdown = await connect(udid)
    info = await get_info(lockdown)
    health = await battery_mod.collect(lockdown, info.product_type)
    if health is None:
        err.print("[yellow]![/yellow] " + t("battery.unavailable"))
        sys.exit(1)
    if as_json:
        click.echo(to_json({"device": info, "battery": health}))
        return

    colour = {
        battery_mod.HEALTHY: "green",
        battery_mod.AGING: "yellow",
        battery_mod.WORN: "red",
    }[health.state]
    table = Table(show_edge=False, show_header=False, box=None)
    table.add_row(
        t("battery.label.health"),
        Text(f"{health.health_percent:.1f} %", style=f"bold {colour}"),
        f"[dim]{health.nominal_capacity} / {health.design_capacity} mAh[/dim]",
    )
    table.add_row(
        t("battery.label.cycles"),
        Text(str(health.cycle_count), style=f"bold {colour}"),
        "[dim]"
        + t(
            "battery.cycles_detail",
            pct=f"{health.cycles_ratio * 100:.0f}",
            rated=health.rated_cycles,
        )
        + "[/dim]",
    )
    table.add_row(t("battery.label.charge"), f"{health.charge_percent} %", "")
    if health.temperature_c is not None:
        table.add_row(t("battery.label.temperature"), f"{health.temperature_c:.1f} °C", "")
    console.print(table)
    console.print()
    console.print(Panel(health.verdict(), border_style=colour))
    if health.throttling_likely:
        console.print("\n[dim]" + t("battery.settings_hint") + "[/dim]")


@main.command()
@udid_option
@coro
async def purgeable(udid):
    """Explain the gap between "free" and "purgeable", with the numbers."""
    lockdown = await connect(udid)
    disk = await get_disk_usage(lockdown)
    console.print(
        t("cli.purgeable.free_now")
        + f"  [bold]{human(disk.free)}[/bold]\n"
        + t("cli.purgeable.under_pressure")
        + f"  [bold]{human(disk.purgeable)}[/bold]\n"
    )
    console.print(t("cli.purgeable.what") + "\n")
    console.print(t("cli.purgeable.why") + "\n")
    console.print(t("cli.purgeable.advice"), style="dim")


@main.command()
@udid_option
@click.option("--save", "do_save", is_flag=True, help="Save a snapshot.")
@coro
async def trend(udid, do_save):
    """Compare the current state against earlier snapshots."""
    lockdown = await connect(udid)
    info = await get_info(lockdown)
    disk = await get_disk_usage(lockdown)
    with console.status(t("cli.status.apps")):
        app_list = await apps_mod.collect(lockdown)
    current = history_mod.snapshot_from(info.udid, disk, app_list)

    previous = history_mod.load_all(info.udid)
    if not previous:
        path = history_mod.save(current)
        console.print(
            t("cli.trend.first", path=path)
        )
        return

    old = previous[0]
    days = max(0.0, (current.taken_at - old.taken_at).total_seconds() / 86400)
    delta_free = current.free - old.free
    arrow = "[green]+[/green]" if delta_free >= 0 else "[red]−[/red]"
    console.print(
        t(
            "cli.trend.since",
            date=f"{old.taken_at:%d/%m/%Y}",
            days=f"{days:.1f}",
            before=human(old.free),
            after=human(current.free),
        )
        + f" ({arrow}{human(abs(delta_free))})\n"
    )
    changes = history_mod.diff(old, current)
    if not changes:
        console.print("[dim]" + t("cli.trend.stable") + "[/dim]")
    else:
        table = Table(show_edge=False, header_style="dim")
        table.add_column(t("report.col.app"))
        table.add_column(t("cli.trend.col.change"), justify="right")
        for name, delta in changes[:15]:
            style = "red" if delta > 0 else "green"
            sign = "+" if delta > 0 else "−"
            table.add_row(name, Text(f"{sign}{human(abs(delta))}", style=style))
        console.print(table)

    if do_save:
        path = history_mod.save(current)
        console.print("\n[dim]" + t("cli.trend.saved", path=path) + "[/dim]")


@main.command()
@coro
async def devices():
    """List visible devices."""
    from .device import list_connected

    found = await list_connected()
    if not found:
        err.print("[yellow]" + t("cli.no_device") + "[/yellow]")
        sys.exit(1)
    for d in found:
        console.print(f"  {d['udid']}  [dim]{d['connection']}[/dim]")


if __name__ == "__main__":
    main()
