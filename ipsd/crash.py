"""Rapports de plantage : ils s'accumulent et se suppriment sans risque."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pymobiledevice3.services.crash_reports import CrashReportsManager


@dataclass(slots=True)
class CrashSummary:
    count: int
    entries: list[str]
    bytes_estimate: int = 0


async def collect(lockdown) -> CrashSummary:
    async with CrashReportsManager(lockdown) as mgr:
        try:
            entries = await mgr.ls("/")
        except Exception:  # noqa: BLE001 - service parfois indisponible
            return CrashSummary(count=0, entries=[])
    entries = [e for e in entries if not e.rstrip("/").endswith((".", ".."))]
    return CrashSummary(count=len(entries), entries=entries)


async def archive_and_clear(lockdown, dest: Path, erase: bool) -> int:
    """Copie les rapports dans « dest », puis les efface si demandé.

    Retourne le nombre d'octets récupérés sur le Mac (donc libérés sur l'iPhone
    quand erase est vrai).
    """
    dest.mkdir(parents=True, exist_ok=True)
    async with CrashReportsManager(lockdown) as mgr:
        await mgr.pull(str(dest), erase=erase, progress_bar=False)
    return sum(p.stat().st_size for p in dest.rglob("*") if p.is_file())
