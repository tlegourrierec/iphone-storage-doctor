"""Rendu terminal et export JSON."""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from .i18n import t
from .rules import MANUAL, REVIEW, SAFE, Finding
from .units import human, pct

console = Console()

TIER_STYLE = {SAFE: "bold green", REVIEW: "bold yellow", MANUAL: "bold red"}
TIER_KEY = {SAFE: "tier.safe", REVIEW: "tier.review", MANUAL: "tier.manual"}


def device_panel(info, disk) -> None:
    body = Text()
    body.append(f"{info.name}\n", style="bold")
    body.append(f"{info.product_type} · iOS {info.product_version} ({info.build})\n")
    body.append(f"UDID {info.udid}")
    if info.battery_percent is not None:
        body.append(f" · {t('report.battery_short')} {info.battery_percent} %")
    console.print(Panel(body, title=t("report.device"), border_style="cyan"))


def storage_table(disk, media_bytes: int, apps_bytes: int, measured: bool = True) -> None:
    """Décomposition honnête : ce qu'on mesure, et ce qu'on ne voit pas."""
    capacity = disk.total_data_capacity or disk.total_disk_capacity
    used = disk.data_used
    unattributed = max(0, used - media_bytes - apps_bytes)

    if not measured:
        # Sans mesure, une ventilation serait un chiffre inventé : on s'abstient.
        _free_summary(disk, capacity)
        console.print(f"\n[dim]{t('report.breakdown_hint')}[/dim]")
        return

    table = Table(title=t("report.where.title"), show_edge=False, header_style="dim")
    table.add_column(t("report.col.item"))
    table.add_column(t("report.col.size"), justify="right")
    table.add_column(t("report.col.pct_used"), justify="right")
    table.add_column(t("report.col.source"), style="dim")

    def row(label, value, source, style=""):
        table.add_row(
            Text(label, style=style),
            Text(human(value), style=style),
            f"{pct(value, used):.0f} %" if used else "—",
            source,
        )

    row(t("report.row.apps"), apps_bytes, "installation_proxy")
    row(t("report.row.media"), media_bytes, "AFC")
    row(t("report.row.unattributed"), unattributed, t("report.source.deduction"), "yellow")
    table.add_section()
    row(t("report.row.total"), used, "com.apple.disk_usage", "bold")

    console.print(table)
    console.print()
    _free_summary(disk, capacity)
    if unattributed > capacity * 0.15:
        console.print(
            f"\n[yellow]![/yellow] {t('report.unattributed_note')}", style="dim"
        )


def _free_summary(disk, capacity: int) -> None:
    tbl = Table(show_edge=False, show_header=False, box=None)
    tbl.add_row(t("report.free.capacity"), human(capacity))
    tbl.add_row(t("report.free.used"), human(disk.data_used))
    tbl.add_row(f"[bold]{t('report.free.free')}[/bold]", f"[bold]{human(disk.free)}[/bold]")
    if disk.purgeable:
        tbl.add_row(
            t("report.free.purgeable"),
            f"{human(disk.purgeable)} [dim]{t('report.free.purgeable_hint')}[/dim]",
        )
    console.print(tbl)


def findings_table(findings: list[Finding]) -> None:
    if not findings:
        console.print(f"[green]{t('report.nothing')}[/green]")
        return
    table = Table(title=t("report.findings.title"), show_edge=False, header_style="dim")
    table.add_column(t("report.col.level"), no_wrap=True)
    table.add_column(t("report.col.finding"))
    table.add_column(t("report.col.size"), justify="right", no_wrap=True)
    table.add_column(t("report.col.what"))
    for f in findings:
        table.add_row(
            Text(t(TIER_KEY[f.tier]) if f.tier in TIER_KEY else f.tier, style=TIER_STYLE.get(f.tier, "")),
            f"[bold]{f.title}[/bold]\n[dim]{f.detail}[/dim]",
            human(f.bytes),
            f.action,
        )
    console.print(table)

    reclaimable = sum(f.bytes for f in findings if f.tier == SAFE)
    arbitrable = sum(f.bytes for f in findings if f.tier == REVIEW)
    console.print()
    console.print(
        f"[green]{t('report.reclaimable')}[/green] [bold]{human(reclaimable)}[/bold]"
        f"   [yellow]{t('report.arbitrable')}[/yellow] [bold]{human(arbitrable)}[/bold]"
    )


def apps_table(apps, limit: int = 20) -> None:
    table = Table(title=t("report.apps.title", limit=limit), show_edge=False, header_style="dim")
    table.add_column(t("report.col.app"))
    table.add_column(t("report.col.total"), justify="right")
    table.add_column(t("report.col.code"), justify="right")
    table.add_column(t("report.col.data"), justify="right")
    table.add_column(t("report.col.data_share"), justify="right")
    for a in apps[:limit]:
        ratio = a.data_ratio
        style = "yellow" if ratio > 0.6 and a.data_bytes > 300_000_000 else ""
        table.add_row(
            Text(a.name, style=style),
            human(a.total),
            human(a.binary_bytes),
            Text(human(a.data_bytes), style=style),
            f"{ratio * 100:.0f} %",
        )
    console.print(table)


def action_plan(plan) -> None:
    """Le plan d'action : une commande par ligne, un gain, un risque annoncé."""
    from .actions import AUTO, CHOICE, EXTERNAL

    if not plan.actions:
        console.print(f"[green]{t('actions.none')}[/green]")
        return

    label = {
        AUTO: t("actions.kind.auto"),
        CHOICE: t("actions.kind.choice"),
        EXTERNAL: t("actions.kind.external"),
    }
    style = {AUTO: "bold green", CHOICE: "bold yellow", EXTERNAL: "bold cyan"}

    console.print()
    console.print(Rule(f"[bold]{t('actions.title')}[/bold]", style="dim"))
    console.print()

    for index, action in enumerate(plan.actions, start=1):
        gain = human(action.gain_bytes) if action.gain_bytes else "—"
        head = Text()
        head.append(f" {index}. ", style="bold")
        head.append(action.title, style="bold")
        head.append(f"   {gain}", style="bold green" if action.gain_bytes else "dim")
        head.append(f"   {label.get(action.kind, '')}", style=style.get(action.kind, ""))
        console.print(head)
        console.print(f"    [dim]{action.why}[/dim]")
        if action.command:
            console.print(f"    [bold cyan]{action.command}[/bold cyan]")
        if action.caveat:
            console.print(f"    [dim]{action.caveat}[/dim]")
        console.print()

    if plan.reclaimable_total:
        console.print(
            f" [green]{t('actions.reclaim_now')}[/green] "
            f"[bold]{human(plan.reclaimable_now)}[/bold]"
            f"    [yellow]{t('actions.reclaim_total')}[/yellow] "
            f"[bold]{human(plan.reclaimable_total)}[/bold]"
        )


def levels_table(levels, free_before: int = 0) -> None:
    """Les trois paliers, avec ce que chacun rapporte et ce qu'il coûte."""
    console.print()
    console.print(Rule(f"[bold]{t('levels.title')}[/bold]", style="dim"))
    console.print()

    for level in levels:
        head = Text()
        head.append(f" {level.title.upper()}", style="bold")
        head.append(f"   +{human(level.gain_bytes)}", style="bold green")
        if free_before:
            head.append(
                "   " + t(
                    "levels.free_after",
                    before=human(free_before),
                    after=human(free_before + level.gain_bytes),
                ),
                style="dim",
            )
        console.print(head)
        console.print(f"    {level.promise}")
        console.print(
            f"    [{'green' if level.is_lossless else 'yellow'}]{level.cost}[/]"
        )
        console.print(f"    [bold cyan]{level.command}[/bold cyan]")
        console.print()

    console.print(f" [dim]{t('levels.footer')}[/dim]")


def _encode(obj: Any) -> Any:
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _encode(v) for k, v in asdict(obj).items()}
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _encode(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_encode(v) for v in obj]
    return obj


def to_json(payload: dict) -> str:
    payload = dict(payload)
    payload.setdefault("generated_at", datetime.now(UTC).isoformat())
    return json.dumps(_encode(payload), indent=2, ensure_ascii=False)
