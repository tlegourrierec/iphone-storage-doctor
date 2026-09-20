"""Désinstallation ciblée : le seul levier qui libère vraiment le cache d'une app.

iOS ne permet pas de vider le cache d'une application depuis un Mac. La seule
action qui rend ces octets, c'est de désinstaller l'app — ce qui efface aussi
ses données locales. Ce module existe pour rendre ce compromis explicite et
mesurable, jamais silencieux.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from pymobiledevice3.services.installation_proxy import InstallationProxyService

from .apps import AppUsage

# Catégories où la désinstallation détruit de l'irrécupérable. Le motif est
# cherché dans le bundle id ET dans le nom affiché.
RISKY: tuple[tuple[str, str], ...] = (
    (
        r"authenticat|authy|2fas|duo\b|otp|yubi",
        "Codes à deux facteurs stockés localement : tu peux perdre l'accès à "
        "tes comptes. Exporte-les d'abord.",
    ),
    (
        r"whatsapp|signal|telegram|threema|wickr|olvid",
        "Historique de conversations stocké sur l'appareil. Perdu sans "
        "sauvegarde préalable.",
    ),
    (
        r"metamask|trust ?wallet|ledger|trezor|exodus|phantom|rainbow|coinbase ?wallet",
        "Clés privées / phrase de récupération locales. Perte définitive des "
        "fonds sans la seed.",
    ),
    (
        r"lightroom|vsco|darkroom|snapseed|procreate|affinity|lumafusion",
        "Projets et retouches non synchronisés stockés localement.",
    ),
    (
        r"dayone|day one|bear|drafts|obsidian|notability|goodnotes|journal",
        "Notes et documents potentiellement locaux uniquement.",
    ),
    (
        r"garmin|strava|health|fitness|clue|flo\b",
        "Historique d'activité ou de santé parfois local uniquement.",
    ),
)

SYSTEM_PROTECTED = "System"


@dataclass
class PurgeCandidate:
    app: AppUsage
    risk: str | None = None

    @property
    def gain(self) -> int:
        return self.app.total

    @property
    def is_risky(self) -> bool:
        return self.risk is not None


@dataclass
class PurgeReport:
    dry_run: bool = True
    removed: list[str] = field(default_factory=list)
    freed_estimate: int = 0
    skipped: list[tuple[str, str]] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    freed_measured: int | None = None


def risk_of(app: AppUsage) -> str | None:
    """Retourne la raison du risque, ou None si la désinstallation est anodine."""
    haystack = f"{app.bundle_id} {app.name}".lower()
    for pattern, reason in RISKY:
        if re.search(pattern, haystack):
            return reason
    return None


def candidates(
    apps: list[AppUsage],
    *,
    min_data: int = 200_000_000,
    include_system: bool = False,
) -> list[PurgeCandidate]:
    """Apps dont la désinstallation rendrait une quantité notable d'espace."""
    out = []
    for app in apps:
        if app.app_type == SYSTEM_PROTECTED and not include_system:
            continue
        if app.data_bytes < min_data:
            continue
        out.append(PurgeCandidate(app=app, risk=risk_of(app)))
    out.sort(key=lambda c: -c.gain)
    return out


def select(
    apps: list[AppUsage], wanted: tuple[str, ...]
) -> tuple[list[PurgeCandidate], list[str]]:
    """Résout des identifiants ou noms saisis par l'utilisateur.

    La correspondance est exacte sur le bundle id, sinon insensible à la casse
    sur le nom affiché. Une saisie ambiguë est signalée plutôt que devinée.
    """
    found, missing = [], []
    for term in wanted:
        low = term.lower()
        exact = [a for a in apps if a.bundle_id.lower() == low]
        matches = exact or [a for a in apps if low in a.name.lower()]
        if not matches:
            missing.append(term)
            continue
        for app in matches:
            if all(c.app.bundle_id != app.bundle_id for c in found):
                found.append(PurgeCandidate(app=app, risk=risk_of(app)))
    return found, missing


async def run(
    lockdown,
    chosen: list[PurgeCandidate],
    *,
    dry_run: bool = True,
    allow_risky: bool = False,
) -> PurgeReport:
    """Désinstalle les apps retenues. Les apps à risque exigent allow_risky."""
    report = PurgeReport(dry_run=dry_run)
    todo = []
    for cand in chosen:
        if cand.is_risky and not allow_risky:
            report.skipped.append((cand.app.name, cand.risk or ""))
            continue
        todo.append(cand)

    report.freed_estimate = sum(c.gain for c in todo)
    if dry_run or not todo:
        report.removed = [c.app.bundle_id for c in todo]
        return report

    proxy = InstallationProxyService(lockdown)
    for cand in todo:
        try:
            await proxy.uninstall(cand.app.bundle_id)
            report.removed.append(cand.app.bundle_id)
        except Exception as exc:  # noqa: BLE001 - on poursuit les suivantes
            report.failures.append(f"{cand.app.name}: {type(exc).__name__}: {exc}")
    report.freed_estimate = sum(
        c.gain for c in todo if c.app.bundle_id in report.removed
    )
    return report
