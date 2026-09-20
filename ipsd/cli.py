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
from .report import (
    apps_table,
    console,
    device_panel,
    findings_table,
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
            err.print(
                "[bold red]✗[/bold red] L'iPhone a été déconnecté pendant "
                "l'opération.\n"
                "  Rebranche-le, déverrouille-le, puis relance la commande. "
                "Ce qui a déjà été traité l'est définitivement ; le reste ne "
                "l'a pas été."
            )
            sys.exit(2)
        except PyMobileDevice3Exception as exc:
            err.print(
                f"[bold red]✗[/bold red] L'appareil a refusé une opération : "
                f"{type(exc).__name__}.\n"
                "  Vérifie qu'il est déverrouillé et appairé, puis réessaie."
            )
            sys.exit(2)
        except KeyboardInterrupt:
            err.print("\n[yellow]Interrompu.[/yellow]")
            sys.exit(130)

    return wrapper


udid_option = click.option("--udid", default=None, help="Cible un appareil précis.")
json_option = click.option("--json", "as_json", is_flag=True, help="Sortie JSON.")


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="iphone-storage-doctor")
@click.pass_context
def main(ctx):
    """Diagnostic et nettoyage du stockage d'un iPhone branché en USB."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(doctor)


@main.command()
@udid_option
@json_option
@coro
async def storage(udid, as_json):
    """Compteurs de stockage, sans parcourir les fichiers (instantané)."""
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
@click.option("--limit", default=20, show_default=True, help="Nombre d'apps affichées.")
@click.option("--user-only", is_flag=True, help="Exclut les apps système.")
@coro
async def apps_cmd(udid, as_json, limit, user_only):
    """Classe les applications par espace occupé."""
    lockdown = await connect(udid)
    with console.status("Interrogation des applications…"):
        found = await apps_mod.collect(lockdown, include_system=not user_only)
    if as_json:
        click.echo(to_json({"apps": found}))
        return
    apps_table(found, limit=limit)
    total = sum(a.total for a in found)
    console.print(f"\n{len(found)} applications, [bold]{human(total)}[/bold] au total.")


@main.command()
@udid_option
@json_option
@click.option(
    "--profile",
    type=click.Choice(["fast", "deep"]),
    default="deep",
    show_default=True,
    help="« fast » ignore les sous-arbres volumineux de la photothèque.",
)
@click.option("--no-apps", is_flag=True, help="Saute la mesure des applications.")
@click.option("--no-media", is_flag=True, help="Saute le parcours du volume média.")
@coro
async def doctor(udid, as_json, profile, no_apps, no_media):
    """Diagnostic complet : où part la place, et ce qui est récupérable."""
    lockdown = await connect(udid)
    info = await get_info(lockdown)
    disk = await get_disk_usage(lockdown)

    findings = []
    media_bytes = 0
    scan = None
    app_list = []

    if not no_apps:
        with console.status("Mesure des applications (peut prendre ~30 s)…"):
            app_list = await apps_mod.collect(lockdown)
        findings += analyse_apps(app_list)

    if not no_media:
        async with MediaScanner(lockdown, profile=profile) as scanner:
            with console.status("Parcours du volume média…") as status:

                def progress(count, path):
                    status.update(f"Parcours du volume média… {count} fichiers")

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
            f"Batterie : [bold {colour}]{health.health_percent:.0f} %[/bold {colour}] "
            f"de santé, {health.cycle_count} cycles. [dim]{health.verdict()}[/dim]"
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
    console.print(
        "\n[dim]Pour récupérer ce qui est marqué SÛR : [bold]ipsd clean[/bold] "
        "(simulation), puis [bold]ipsd clean --apply[/bold].[/dim]"
    )


@main.command()
@udid_option
@click.option("--apply", "do_apply", is_flag=True, help="Supprime réellement.")
@click.option(
    "--no-quarantine",
    is_flag=True,
    help="Supprime sans copier au préalable sur le Mac.",
)
@click.option(
    "--quarantine-dir",
    type=click.Path(path_type=Path),
    default=None,
    help=f"Dossier d'archivage (défaut : {clean_mod.DEFAULT_QUARANTINE}).",
)
@click.option("--crash", "do_crash", is_flag=True, help="Traite aussi les rapports de plantage.")
@coro
async def clean(udid, do_apply, no_quarantine, quarantine_dir, do_crash):
    """Supprime les fichiers classés SÛR. Simulation par défaut."""
    lockdown = await connect(udid)

    async with MediaScanner(lockdown, profile="deep") as scanner:
        with console.status("Recherche des fichiers récupérables…"):
            scan = await scanner.scan()
    findings = [f for f in analyse_media(scan) if f.tier == SAFE]
    sizes = {f.path: f.size for f in scan.files}

    targets = clean_mod.selectable(findings)
    if not targets and not do_crash:
        console.print("[green]Rien à nettoyer.[/green]")
        return

    for f in targets:
        console.print(f"  [green]•[/green] {f.title} — {human(f.bytes)} ({f.count} fichiers)")

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
        console.print("[dim]Relance avec --apply pour exécuter.[/dim]")
    else:
        console.print(
            f"\n[green]✓[/green] {report.deleted} fichiers supprimés, "
            f"[bold]{human(report.deleted_bytes)}[/bold] libérés."
        )
        if report.quarantine_dir:
            console.print(f"[dim]Copie de sécurité : {report.quarantine_dir}[/dim]")
        for failure in report.failures[:5]:
            console.print(f"[red]✗[/red] {failure}")

    if do_crash:
        dest = (quarantine_dir or clean_mod.DEFAULT_QUARANTINE) / "crash-reports"
        crashes = await crash_mod.collect(lockdown)
        if not crashes.count:
            console.print("\n[dim]Aucun rapport de plantage.[/dim]")
        elif not do_apply:
            console.print(f"\n[yellow]Simulation.[/yellow] {crashes.count} rapports à archiver.")
        else:
            size = await crash_mod.archive_and_clear(lockdown, dest, erase=True)
            console.print(
                f"[green]✓[/green] {crashes.count} rapports archivés dans {dest} "
                f"({human(size)}) puis effacés."
            )


@main.command()
@udid_option
@click.option("--app", "wanted", multiple=True, help="Bundle id ou nom. Répétable.")
@click.option("--top", type=int, default=None, help="Cible les N apps les plus lourdes.")
@click.option(
    "--min-data",
    type=int,
    default=200,
    show_default=True,
    help="Seuil de données en Mo pour qu'une app soit proposée.",
)
@click.option("--apply", "do_apply", is_flag=True, help="Désinstalle réellement.")
@click.option(
    "--force-risky",
    is_flag=True,
    help="Autorise les apps signalées comme risquées (2FA, messageries…).",
)
@click.option("--yes", is_flag=True, help="Passe la confirmation interactive.")
@coro
async def purge(udid, wanted, top, min_data, do_apply, force_risky, yes):
    """Désinstalle des apps pour récupérer leur cache. Simulation par défaut.

    iOS interdit de vider le cache d'une app depuis un Mac. Désinstaller est
    le seul levier — au prix des données locales de l'app.
    """
    lockdown = await connect(udid)
    with console.status("Mesure des applications…"):
        app_list = await apps_mod.collect(lockdown)
    before = await get_disk_usage(lockdown)

    missing: list[str] = []
    if wanted:
        chosen, missing = purge_mod.select(app_list, wanted)
    else:
        pool = purge_mod.candidates(app_list, min_data=min_data * 1_000_000)
        chosen = pool[:top] if top else pool

    for term in missing:
        err.print(f"[yellow]![/yellow] Aucune app ne correspond à « {term} ».")
    if not chosen:
        console.print("[green]Aucune app ne dépasse le seuil.[/green]")
        return

    table = Table(title="Candidates à la désinstallation", show_edge=False, header_style="dim")
    table.add_column("Application")
    table.add_column("Récupéré", justify="right")
    table.add_column("dont données", justify="right")
    table.add_column("Risque")
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
        console.print("\n[yellow]Simulation.[/yellow] Rien n'a été touché.")
        console.print("[dim]Ajoute --apply pour désinstaller.[/dim]")
        return
    if not effective:
        console.print("\n[yellow]Rien à désinstaller.[/yellow]")
        return

    console.print(
        "\n[bold red]Les données locales de ces apps seront effacées "
        "définitivement.[/bold red] Le binaire se retéléchargera depuis l'App Store."
    )
    if not yes:
        answer = click.prompt("Tape SUPPRIMER pour confirmer", default="", show_default=False)
        if answer.strip() != "SUPPRIMER":
            console.print("[yellow]Annulé.[/yellow]")
            return

    with console.status("Désinstallation…"):
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
        f"Espace libre mesuré : {human(before.free)} → [bold]{human(after.free)}[/bold] "
        f"(+{human(report.freed_measured)})"
    )
    for name, reason in report.skipped:
        console.print(f"[yellow]⊘[/yellow] {name} épargnée — {reason}")
    for failure in report.failures:
        console.print(f"[red]✗[/red] {failure}")


@main.command()
@udid_option
@click.option("--yes", is_flag=True, help="Passe la confirmation.")
@coro
async def restart(udid, yes):
    """Redémarre l'iPhone : vide la RAM et les fichiers temporaires."""
    lockdown = await connect(udid)
    console.print(
        "[dim]Un redémarrage libère la mémoire vive et purge les fichiers "
        "temporaires. L'effet sur l'espace disque est faible et temporaire.[/dim]"
    )
    if not yes and not click.confirm("Redémarrer l'iPhone maintenant ?", default=False):
        console.print("[yellow]Annulé.[/yellow]")
        return
    from pymobiledevice3.services.diagnostics import DiagnosticsService

    async with DiagnosticsService(lockdown) as diag:
        await diag.restart()
    console.print("[green]✓[/green] Redémarrage demandé.")


@main.command()
@udid_option
@click.option("--apply", "do_apply", is_flag=True, help="Exécute réellement le nettoyage.")
@click.option("--no-quarantine", is_flag=True, help="Supprime sans copier sur le Mac.")
@coro
async def boost(udid, do_apply, no_quarantine):
    """Relevé avant, nettoyage sûr, relevé après. Le bilan complet en une commande."""
    lockdown = await connect(udid)
    info = await get_info(lockdown)

    before = await get_disk_usage(lockdown)
    health = await battery_mod.collect(lockdown, info.product_type)
    crashes_before = await crash_mod.collect(lockdown)

    device_panel(info, before)
    console.print(Rule("[bold]Avant[/bold]", style="dim"))
    before_tbl = Table(show_edge=False, show_header=False, box=None)
    before_tbl.add_row("Espace libre", f"[bold]{human(before.free)}[/bold]")
    before_tbl.add_row("Espace occupé", human(before.data_used))
    if health is not None:
        colour = {
            battery_mod.HEALTHY: "green",
            battery_mod.AGING: "yellow",
            battery_mod.WORN: "red",
        }[health.state]
        before_tbl.add_row(
            "Santé batterie",
            f"[bold {colour}]{health.health_percent:.0f} %[/bold {colour}] "
            f"[dim]({health.cycle_count} cycles)[/dim]",
        )
    before_tbl.add_row("Rapports de plantage", str(crashes_before.count))
    console.print(before_tbl)

    console.print()
    console.print(Rule("[bold]Nettoyage[/bold]", style="dim"))
    async with MediaScanner(lockdown, profile="deep") as scanner:
        with console.status("Recherche des fichiers récupérables…") as status:

            def progress(count, path):
                status.update(f"Recherche… {count} fichiers examinés")

            scan = await scanner.scan(on_progress=progress)
    findings = [f for f in analyse_media(scan) if f.tier == SAFE]
    sizes = {f.path: f.size for f in scan.files}
    for f in clean_mod.selectable(findings):
        console.print(f"  [green]•[/green] {f.title} — {human(f.bytes)} ({f.count} fichiers)")

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
        console.print("[dim]Relance avec --apply pour exécuter.[/dim]")
        return

    after = await get_disk_usage(lockdown)
    console.print()
    console.print(Rule("[bold]Après[/bold]", style="dim"))

    result = Table(show_edge=False, header_style="dim")
    result.add_column("")
    result.add_column("Avant", justify="right")
    result.add_column("Après", justify="right")
    result.add_column("Écart", justify="right")
    delta_free = after.free - before.free
    result.add_row(
        "Espace libre",
        human(before.free),
        Text(human(after.free), style="bold"),
        Text(
            f"{'+' if delta_free >= 0 else '−'}{human(abs(delta_free))}",
            style="green" if delta_free >= 0 else "red",
        ),
    )
    result.add_row(
        "Espace occupé",
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
        console.print(f"[dim]Copie de sécurité : {report.quarantine_dir}[/dim]")
    for failure in report.failures[:3]:
        console.print(f"[red]✗[/red] {failure}")

    console.print()
    console.print(Rule("[bold]Ce qui reste à gagner[/bold]", style="dim"))
    with console.status("Mesure des applications…"):
        app_list = await apps_mod.collect(lockdown)
    advice = sort_findings(analyse_apps(app_list))
    for f in advice:
        console.print(f"  [yellow]•[/yellow] [bold]{f.title}[/bold] — {human(f.bytes)}")
        console.print(f"    [dim]{f.detail}[/dim]")
    if health is not None and health.throttling_likely:
        console.print(
            f"\n  [red]•[/red] [bold]Batterie à {health.health_percent:.0f} %[/bold] — "
            "c'est ce qui ralentit l'appareil, pas le stockage."
        )
        console.print(f"    [dim]{health.verdict()}[/dim]")


@main.command()
@udid_option
@json_option
@coro
async def battery(udid, as_json):
    """Santé réelle de la batterie — première cause de lenteur d'un appareil ancien."""
    lockdown = await connect(udid)
    info = await get_info(lockdown)
    health = await battery_mod.collect(lockdown, info.product_type)
    if health is None:
        err.print("[yellow]![/yellow] Compteurs de batterie indisponibles sur cet appareil.")
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
        "Santé",
        Text(f"{health.health_percent:.1f} %", style=f"bold {colour}"),
        f"[dim]{health.nominal_capacity} / {health.design_capacity} mAh[/dim]",
    )
    table.add_row(
        "Cycles",
        Text(str(health.cycle_count), style=f"bold {colour}"),
        f"[dim]{health.cycles_ratio * 100:.0f} % des {health.rated_cycles} cycles "
        "prévus par Apple[/dim]",
    )
    table.add_row("Charge", f"{health.charge_percent} %", "")
    if health.temperature_c is not None:
        table.add_row("Température", f"{health.temperature_c:.1f} °C", "")
    console.print(table)
    console.print()
    console.print(Panel(health.verdict(), border_style=colour))
    if health.throttling_likely:
        console.print(
            "\n[dim]Réglages > Batterie > État de la batterie indique si la "
            "gestion des performances est active sur cet appareil.[/dim]"
        )


@main.command()
@udid_option
@coro
async def purgeable(udid):
    """Explique l'écart entre « libre » et « libérable », chiffres à l'appui."""
    lockdown = await connect(udid)
    disk = await get_disk_usage(lockdown)
    console.print(
        f"Libre immédiatement      [bold]{human(disk.free)}[/bold]\n"
        f"Libérable sous pression  [bold]{human(disk.purgeable)}[/bold]\n"
    )
    console.print(
        "[bold]Ce que c'est.[/bold] iOS garde des caches qu'il sait sacrifier "
        "seul quand une écriture manque de place : vignettes, copies iCloud "
        "locales, index de recherche, données d'apps marquées jetables.\n"
    )
    console.print(
        "[bold]Pourquoi on ne peut pas le détailler.[/bold] Aucun service "
        "accessible en USB ne l'expose. Vérifié sur cet appareil : le domaine "
        "com.apple.mobile.storage renvoie vide, les clés mobilegestalt de "
        "stockage sont refusées (DeprecationError), et NANDInfo est un blob "
        "binaire du contrôleur flash — usure et blocs, pas une ventilation.\n"
    )
    console.print(
        "[bold]Ce qu'il faut en faire.[/bold] Rien. Cet espace se libère tout "
        "seul au moment où le système en a besoin. Un outil qui te promet de "
        "« récupérer » ces octets te vend un nettoyage qu'iOS fait déjà.",
        style="dim",
    )


@main.command()
@udid_option
@click.option("--save", "do_save", is_flag=True, help="Enregistre un instantané.")
@coro
async def trend(udid, do_save):
    """Compare l'état actuel aux instantanés précédents."""
    lockdown = await connect(udid)
    info = await get_info(lockdown)
    disk = await get_disk_usage(lockdown)
    with console.status("Mesure des applications…"):
        app_list = await apps_mod.collect(lockdown)
    current = history_mod.snapshot_from(info.udid, disk, app_list)

    previous = history_mod.load_all(info.udid)
    if not previous:
        path = history_mod.save(current)
        console.print(
            f"Premier instantané enregistré : [dim]{path}[/dim]\n"
            "Relance [bold]ipsd trend[/bold] dans quelques jours pour voir la dérive."
        )
        return

    old = previous[0]
    days = max(0.0, (current.taken_at - old.taken_at).total_seconds() / 86400)
    delta_free = current.free - old.free
    arrow = "[green]+[/green]" if delta_free >= 0 else "[red]−[/red]"
    console.print(
        f"Depuis le {old.taken_at:%d/%m/%Y} ({days:.1f} j) : espace libre "
        f"{human(old.free)} → [bold]{human(current.free)}[/bold] "
        f"({arrow}{human(abs(delta_free))})\n"
    )
    changes = history_mod.diff(old, current)
    if not changes:
        console.print("[dim]Aucune app n'a changé de taille.[/dim]")
    else:
        table = Table(show_edge=False, header_style="dim")
        table.add_column("Application")
        table.add_column("Variation", justify="right")
        for name, delta in changes[:15]:
            style = "red" if delta > 0 else "green"
            sign = "+" if delta > 0 else "−"
            table.add_row(name, Text(f"{sign}{human(abs(delta))}", style=style))
        console.print(table)

    if do_save:
        path = history_mod.save(current)
        console.print(f"\n[dim]Instantané enregistré : {path}[/dim]")


@main.command()
@coro
async def devices():
    """Liste les appareils visibles."""
    from .device import list_connected

    found = await list_connected()
    if not found:
        err.print("[yellow]Aucun appareil. Branche l'iPhone et déverrouille-le.[/yellow]")
        sys.exit(1)
    for d in found:
        console.print(f"  {d['udid']}  [dim]{d['connection']}[/dim]")


if __name__ == "__main__":
    main()
