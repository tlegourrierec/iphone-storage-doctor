"""Heuristiques : transformer un inventaire en constats actionnables.

Trois niveaux de sûreté, volontairement conservateurs :

* SAFE    — supprimable par l'outil ; cache régénéré par iOS, aucune donnée
            utilisateur perdue.
* REVIEW  — récupérable mais c'est un choix : contenu re-téléchargeable
            (musique, podcasts) ou volumineux mais légitime.
* MANUAL  — jamais touché par l'outil. Soit c'est de la donnée utilisateur,
            soit la suppression via AFC corromprait une base iOS.

La règle d'or : tout ce qui est sous /DCIM et /PhotoData est MANUAL. Supprimer
une photo par AFC laisse son entrée dans Photos.sqlite -> bibliothèque
incohérente, vignettes fantômes. Ça se fait dans l'app Photos, pas ici.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .i18n import t
from .units import age_days, human

if TYPE_CHECKING:  # pragma: no cover
    from .apps import AppUsage
    from .scan import FileEntry, ScanResult

SAFE = "SAFE"
REVIEW = "REVIEW"
MANUAL = "MANUAL"

_ORDER = {SAFE: 0, REVIEW: 1, MANUAL: 2}


@dataclass
class Finding:
    """Un constat : quoi, combien, quel risque, quelle action."""

    key: str
    title: str
    tier: str
    bytes: int
    detail: str
    action: str
    paths: list[str] = field(default_factory=list)
    count: int = 0

    @property
    def deletable(self) -> bool:
        return self.tier == SAFE and bool(self.paths)

    def sort_key(self) -> tuple[int, int]:
        return (_ORDER.get(self.tier, 3), -self.bytes)


def _sum(files: list[FileEntry]) -> int:
    return sum(f.size for f in files)


def _under(files: list[FileEntry], *prefixes: str) -> list[FileEntry]:
    return [f for f in files if f.path.startswith(prefixes)]


# --------------------------------------------------------------------------
# Règles sur le volume média (AFC)
# --------------------------------------------------------------------------

def rule_media_analysis(files, **_):
    """Caches d'analyse d'images (OCR, scènes, visages). Reconstruits seuls."""
    backups = _under(files, "/MediaAnalysis/.backup")
    if not backups:
        return None
    size = _sum(backups)
    if size < 20_000_000:
        return None
    return Finding(
        key="media_analysis_backup",
        title=t("rule.media_analysis.title"),
        tier=SAFE,
        bytes=size,
        count=len(backups),
        detail=t("rule.media_analysis.detail"),
        action=t("rule.media_analysis.action"),
        paths=[f.path for f in backups],
    )


def rule_thumbnail_caches(files, **_):
    """Vignettes .ithmb : régénérées, mais leur reconstruction est coûteuse."""
    thumbs = [f for f in _under(files, "/PhotoData/Thumbnails") if f.ext == "ithmb"]
    if not thumbs:
        return None
    size = _sum(thumbs)
    if size < 100_000_000:
        return None
    return Finding(
        key="photo_thumbnails",
        title=t("rule.thumbnails.title"),
        tier=MANUAL,
        bytes=size,
        count=len(thumbs),
        detail=t("rule.thumbnails.detail", size=human(size)),
        action=t("rule.thumbnails.action"),
    )


def rule_stale_downloads(files, max_age_days: int = 60, **_):
    """Téléchargements Safari oubliés dans la zone de transit."""
    old = [
        f for f in _under(files, "/Downloads")
        if (age_days(f.mtime) or 0) > max_age_days
    ]
    if not old:
        return None
    size = _sum(old)
    if size < 1_000_000:
        return None
    return Finding(
        key="stale_downloads",
        title=t("rule.downloads.title"),
        tier=SAFE,
        bytes=size,
        count=len(old),
        detail=t("rule.downloads.detail", count=len(old), days=max_age_days),
        action=t("rule.deletable"),
        paths=[f.path for f in old],
    )


def rule_temp_files(files, **_):
    """Fragments d'écritures interrompues."""
    junk = [
        f for f in files
        if f.ext in ("tmp", "partial", "download", "crdownload")
        or f.name.startswith("._")
        or f.name == ".DS_Store"
    ]
    if not junk:
        return None
    size = _sum(junk)
    return Finding(
        key="temp_files",
        title=t("rule.temp.title"),
        tier=SAFE,
        bytes=size,
        count=len(junk),
        detail=t("rule.temp.detail"),
        action=t("rule.deletable"),
        paths=[f.path for f in junk],
    )


def rule_orphan_sidecars(files, **_):
    """.AAE sans photo associée : la retouche survit à la photo effacée."""
    bases = {f.path.rsplit(".", 1)[0] for f in files if f.ext != "aae"}
    orphans = [
        f for f in files
        if f.ext == "aae" and f.path.rsplit(".", 1)[0] not in bases
    ]
    if not orphans:
        return None
    return Finding(
        key="orphan_sidecars",
        title=t("rule.sidecar.title"),
        tier=SAFE,
        bytes=_sum(orphans),
        count=len(orphans),
        detail=t("rule.sidecar.detail", count=len(orphans)),
        action=t("rule.deletable"),
        paths=[f.path for f in orphans],
    )


def rule_offline_music(files, **_):
    """Apple Music hors-ligne : souvent le plus gros poste du volume média."""
    music = _under(files, "/Music", "/iTunes_Control/Music")
    if not music:
        return None
    size = _sum(music)
    if size < 200_000_000:
        return None
    return Finding(
        key="offline_music",
        title=t("rule.music.title"),
        tier=REVIEW,
        bytes=size,
        count=len(music),
        detail=t("rule.music.detail", size=human(size)),
        action=t("rule.music.action"),
    )


def rule_offline_video(files, **_):
    """Épisodes et vidéos téléchargés, re-téléchargeables."""
    vids = _under(files, "/Podcasts", "/Purchases", "/ManagedPurchases")
    if not vids:
        return None
    size = _sum(vids)
    if size < 100_000_000:
        return None
    return Finding(
        key="offline_video",
        title=t("rule.video.title"),
        tier=REVIEW,
        bytes=size,
        count=len(vids),
        detail=t("rule.video.detail", size=human(size)),
        action=t("rule.video.action"),
    )


def rule_big_old_videos(files, min_size: int = 50_000_000, min_age: int = 180, **_):
    """Grosses vidéos anciennes : candidates au déchargement, pas à l'effacement."""
    vids = [
        f for f in _under(files, "/DCIM")
        if f.ext in ("mov", "mp4", "m4v")
        and f.size >= min_size
        and (age_days(f.mtime) or 0) > min_age
    ]
    if not vids:
        return None
    vids.sort(key=lambda f: -f.size)
    size = _sum(vids)
    return Finding(
        key="big_old_videos",
        title=t("rule.bigvideo.title"),
        tier=MANUAL,
        bytes=size,
        count=len(vids),
        detail=t("rule.bigvideo.detail", count=len(vids), size=human(min_size), months=min_age // 30),
        action=t("rule.bigvideo.action"),
        paths=[f.path for f in vids[:50]],
    )


MEDIA_RULES = (
    rule_media_analysis,
    rule_stale_downloads,
    rule_temp_files,
    rule_orphan_sidecars,
    rule_thumbnail_caches,
    rule_offline_music,
    rule_offline_video,
    rule_big_old_videos,
)


def analyse_media(scan: ScanResult, **options) -> list[Finding]:
    findings = []
    for rule in MEDIA_RULES:
        try:
            found = rule(scan.files, **options)
        except Exception:  # noqa: BLE001 - une règle cassée n'annule pas le reste
            continue
        if found and found.bytes > 0:
            findings.append(found)
    return findings


# --------------------------------------------------------------------------
# Règles sur les applications
# --------------------------------------------------------------------------

def analyse_apps(
    apps: list[AppUsage],
    bloat_ratio: float = 0.55,
    min_data: int = 300_000_000,
) -> list[Finding]:
    """Repère les apps dont les *données* pèsent plus que l'app elle-même.

    Une app dont 80 % du poids est de la donnée accumule du cache. La réinstaller
    (ou vider son cache dans ses réglages) rend cette place immédiatement.
    """
    findings = []
    bloated = [
        a for a in apps
        if a.data_bytes >= min_data and a.data_ratio >= bloat_ratio
    ]
    bloated.sort(key=lambda a: -a.data_bytes)
    if bloated:
        total = sum(a.data_bytes for a in bloated)
        lines = ", ".join(f"{a.name} ({human(a.data_bytes)})" for a in bloated[:5])
        findings.append(
            Finding(
                key="app_cache_bloat",
                title=t("rule.app_bloat.title"),
                tier=REVIEW,
                bytes=total,
                count=len(bloated),
                detail=t("rule.app_bloat.detail", count=len(bloated), list=lines),
                action=t("rule.app_bloat.action"),
            )
        )
    heavy = [a for a in apps if a.total >= 1_000_000_000]
    if heavy:
        findings.append(
            Finding(
                key="heavy_apps",
                title=t("rule.heavy_apps.title"),
                tier=REVIEW,
                bytes=sum(a.total for a in heavy),
                count=len(heavy),
                detail=", ".join(f"{a.name} ({human(a.total)})" for a in heavy[:6]),
                action=t("rule.heavy_apps.action"),
            )
        )
    return findings


def analyse_crashes(summary, bytes_hint: int = 0) -> list[Finding]:
    if not summary or summary.count == 0:
        return []
    return [
        Finding(
            key="crash_reports",
            title=t("rule.crash.title"),
            tier=SAFE,
            bytes=bytes_hint or summary.count * 120_000,
            count=summary.count,
            detail=t("rule.crash.detail", count=summary.count),
            action=t("rule.crash.action"),
        )
    ]


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: f.sort_key())
