"""Suppression encadrée : simulation par défaut, mise en quarantaine avant effacement."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pymobiledevice3.services.afc import AfcService

from .rules import SAFE, Finding

DEFAULT_QUARANTINE = Path.home() / "iphone-storage-doctor" / "quarantine"


@dataclass
class CleanReport:
    planned: int = 0
    planned_bytes: int = 0
    deleted: int = 0
    deleted_bytes: int = 0
    archived: int = 0
    failures: list[str] = field(default_factory=list)
    dry_run: bool = True
    quarantine_dir: Path | None = None


@dataclass
class Plan:
    """Ce qui serait supprimé, résumé pour être soumis à l'utilisateur."""

    findings: list[Finding] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)
    total_bytes: int = 0

    @property
    def is_empty(self) -> bool:
        return not self.paths

    def lines(self) -> list[str]:
        return [f"{f.title} — {f.count} fichiers" for f in self.findings]


def build_plan(findings: list[Finding], sizes: dict[str, int] | None = None) -> Plan:
    """Construit la liste exacte des fichiers concernés, sans rien supprimer.

    Séparé de l'exécution pour que l'utilisateur voie précisément ce qu'il
    approuve avant que quoi que ce soit ne parte.
    """
    sizes = sizes or {}
    plan = Plan()
    for finding in selectable(findings):
        plan.findings.append(finding)
        for path in finding.paths:
            if path not in plan.paths:
                plan.paths.append(path)
    plan.total_bytes = sum(sizes.get(p, 0) for p in plan.paths)
    return plan


def selectable(findings: list[Finding]) -> list[Finding]:
    """Seuls les constats SAFE assortis de chemins sont supprimables."""
    return [f for f in findings if f.tier == SAFE and f.paths]


async def run(
    lockdown,
    findings: list[Finding],
    *,
    dry_run: bool = True,
    quarantine: bool = True,
    quarantine_dir: Path | None = None,
    sizes: dict[str, int] | None = None,
) -> CleanReport:
    """Archive puis supprime les fichiers des constats SAFE.

    Rien n'est supprimé sans avoir d'abord été copié sur le Mac, sauf si
    quarantine=False est demandé explicitement.
    """
    targets = selectable(findings)
    report = CleanReport(dry_run=dry_run)
    sizes = sizes or {}

    paths: list[str] = []
    for finding in targets:
        for p in finding.paths:
            if p not in paths:
                paths.append(p)
    report.planned = len(paths)
    report.planned_bytes = sum(sizes.get(p, 0) for p in paths)

    if dry_run or not paths:
        return report

    qdir = quarantine_dir or DEFAULT_QUARANTINE
    if quarantine:
        qdir.mkdir(parents=True, exist_ok=True)
        report.quarantine_dir = qdir

    afc = AfcService(lockdown)
    try:
        for path in paths:
            try:
                if quarantine:
                    data = await afc.get_file_contents(path)
                    dest = qdir / path.lstrip("/")
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(data)
                    report.archived += 1
                await afc.rm_single(path)
                report.deleted += 1
                report.deleted_bytes += sizes.get(path, 0)
            except Exception as exc:  # noqa: BLE001 - on continue sur les autres
                report.failures.append(f"{path}: {type(exc).__name__}: {exc}")
    finally:
        try:
            await afc.aclose()
        except Exception:  # noqa: BLE001
            pass
    return report
