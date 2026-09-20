"""Rendu terminal et export JSON."""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .rules import MANUAL, REVIEW, SAFE, Finding
from .units import human, pct

console = Console()

TIER_STYLE = {SAFE: "bold green", REVIEW: "bold yellow", MANUAL: "bold red"}
TIER_LABEL = {
    SAFE: "SÛR",
    REVIEW: "À ARBITRER",
    MANUAL: "MANUEL",
}


def device_panel(info, disk) -> None:
    body = Text()
    body.append(f"{info.name}\n", style="bold")
    body.append(f"{info.product_type} · iOS {info.product_version} ({info.build})\n")
    body.append(f"UDID {info.udid}")
    if info.battery_percent is not None:
        body.append(f" · batterie {info.battery_percent} %")
    console.print(Panel(body, title="Appareil", border_style="cyan"))


def storage_table(disk, media_bytes: int, apps_bytes: int, measured: bool = True) -> None:
    """Décomposition honnête : ce qu'on mesure, et ce qu'on ne voit pas."""
    capacity = disk.total_data_capacity or disk.total_disk_capacity
    used = disk.data_used
    unattributed = max(0, used - media_bytes - apps_bytes)

    if not measured:
        # Sans mesure, une ventilation serait un chiffre inventé : on s'abstient.
        _free_summary(disk, capacity)
        console.print(
            "\n[dim]Ventilation par poste : lance [bold]ipsd doctor[/bold].[/dim]"
        )
        return

    table = Table(title="Où part la place", show_edge=False, header_style="dim")
    table.add_column("Poste")
    table.add_column("Taille", justify="right")
    table.add_column("% utilisé", justify="right")
    table.add_column("Source", style="dim")

    def row(label, value, source, style=""):
        table.add_row(
            Text(label, style=style),
            Text(human(value), style=style),
            f"{pct(value, used):.0f} %" if used else "—",
            source,
        )

    row("Applications (code + données)", apps_bytes, "installation_proxy")
    row("Volume média accessible", media_bytes, "AFC")
    row("Non attribué / « Données système »", unattributed, "déduction", "yellow")
    table.add_section()
    row("Total occupé", used, "com.apple.disk_usage", "bold")

    console.print(table)
    console.print()
    _free_summary(disk, capacity)
    if unattributed > capacity * 0.15:
        console.print(
            "\n[yellow]![/yellow] Le poste « non attribué » est important. Il couvre "
            "iOS lui-même, les caches système et iCloud, hors de portée d'une "
            "connexion USB sans jailbreak. Aucun outil ne peut le détailler.",
            style="dim",
        )


def _free_summary(disk, capacity: int) -> None:
    tbl = Table(show_edge=False, show_header=False, box=None)
    tbl.add_row("Capacité données", human(capacity))
    tbl.add_row("Occupé", human(disk.data_used))
    tbl.add_row("[bold]Libre immédiatement[/bold]", f"[bold]{human(disk.free)}[/bold]")
    if disk.purgeable:
        tbl.add_row(
            "Libérable par iOS sous pression",
            f"{human(disk.purgeable)} [dim](caches qu'iOS sacrifiera seul)[/dim]",
        )
    console.print(tbl)


def findings_table(findings: list[Finding]) -> None:
    if not findings:
        console.print("[green]Rien à signaler.[/green]")
        return
    table = Table(title="Constats", show_edge=False, header_style="dim")
    table.add_column("Niveau", no_wrap=True)
    table.add_column("Constat")
    table.add_column("Taille", justify="right", no_wrap=True)
    table.add_column("Que faire")
    for f in findings:
        table.add_row(
            Text(TIER_LABEL.get(f.tier, f.tier), style=TIER_STYLE.get(f.tier, "")),
            f"[bold]{f.title}[/bold]\n[dim]{f.detail}[/dim]",
            human(f.bytes),
            f.action,
        )
    console.print(table)

    reclaimable = sum(f.bytes for f in findings if f.tier == SAFE)
    arbitrable = sum(f.bytes for f in findings if f.tier == REVIEW)
    console.print()
    console.print(
        f"[green]Récupérable sans risque :[/green] [bold]{human(reclaimable)}[/bold]"
        f"   [yellow]Sur arbitrage :[/yellow] [bold]{human(arbitrable)}[/bold]"
    )


def apps_table(apps, limit: int = 20) -> None:
    table = Table(title=f"Top {limit} applications", show_edge=False, header_style="dim")
    table.add_column("Application")
    table.add_column("Total", justify="right")
    table.add_column("Code", justify="right")
    table.add_column("Données", justify="right")
    table.add_column("Part données", justify="right")
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
