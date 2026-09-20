"""Parcours du volume média via AFC (com.apple.afc).

AFC ne donne accès qu'à /var/mobile/Media. C'est une fraction du stockage :
les données d'apps sont hors de portée et sont mesurées par ipsd.apps.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime

from pymobiledevice3.services.afc import AfcService

from .units import as_aware

# Branches ignorées en profil « fast » : beaucoup de fichiers, peu d'intérêt
# individuel (on les agrège quand même par leur taille de dossier).
FAST_SKIP = (
    "/PhotoData/internal",
    "/PhotoData/Mutations",
    "/PhotoData/CPLAssets",
    "/MotionAssets",
)

# Jamais parcouru : coûteux et sans valeur pour le diagnostic.
ALWAYS_SKIP = ("/.Trashes", "/Photos")


@dataclass(slots=True)
class FileEntry:
    path: str
    size: int
    mtime: datetime | None
    birthtime: datetime | None

    @property
    def name(self) -> str:
        return self.path.rsplit("/", 1)[-1]

    @property
    def ext(self) -> str:
        name = self.name
        return name.rsplit(".", 1)[-1].lower() if "." in name else ""

    @property
    def top(self) -> str:
        """Premier segment du chemin, ex. « /Music »."""
        parts = self.path.strip("/").split("/")
        return "/" + parts[0] if parts and parts[0] else "/"


@dataclass
class ScanResult:
    files: list[FileEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_s: float = 0.0
    truncated: bool = False

    @property
    def total_size(self) -> int:
        return sum(f.size for f in self.files)

    def by_top(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in self.files:
            out[f.top] = out.get(f.top, 0) + f.size
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def _skips(profile: str) -> tuple[str, ...]:
    return ALWAYS_SKIP + (FAST_SKIP if profile == "fast" else ())


class MediaScanner:
    """Parcours récursif d'AFC, robuste aux dossiers interdits."""

    def __init__(self, lockdown, profile: str = "deep", max_files: int = 400_000):
        self.lockdown = lockdown
        self.profile = profile
        self.max_files = max_files
        self._afc: AfcService | None = None

    async def __aenter__(self) -> MediaScanner:
        self._afc = AfcService(self.lockdown)
        return self

    async def __aexit__(self, *exc) -> None:
        if self._afc is not None:
            try:
                await self._afc.aclose()
            except Exception:  # noqa: BLE001 - fermeture best-effort
                pass

    @property
    def afc(self) -> AfcService:
        if self._afc is None:
            raise RuntimeError("MediaScanner doit être utilisé via « async with ».")
        return self._afc

    async def roots(self) -> list[str]:
        entries = await self.afc.listdir("/")
        return ["/" + e.lstrip("/") for e in entries if e not in (".", "..")]

    async def scan(
        self,
        roots: Iterable[str] | None = None,
        on_progress: Callable[[int, str], None] | None = None,
    ) -> ScanResult:
        loop = asyncio.get_running_loop()
        started = loop.time()
        result = ScanResult()
        skips = _skips(self.profile)
        targets = list(roots) if roots is not None else await self.roots()

        for root in targets:
            if any(root.startswith(s) for s in skips):
                continue
            await self._walk(root, result, skips, on_progress)
            if result.truncated:
                break

        result.duration_s = loop.time() - started
        return result

    async def _walk(self, path, result, skips, on_progress, depth: int = 0) -> None:
        if depth > 32 or result.truncated:
            return
        try:
            entries = await self.afc.listdir(path)
        except Exception as exc:  # noqa: BLE001 - dossier illisible = non bloquant
            result.errors.append(f"{path}: {type(exc).__name__}")
            return

        for name in entries:
            if name in (".", ".."):
                continue
            child = path.rstrip("/") + "/" + name
            if any(child.startswith(s) for s in skips):
                continue
            try:
                st = await self.afc.stat(child)
            except Exception:  # noqa: BLE001 - entrée disparue ou interdite
                continue
            fmt = st.get("st_ifmt")
            if fmt == "S_IFDIR":
                await self._walk(child, result, skips, on_progress, depth + 1)
                if result.truncated:
                    return
            elif fmt == "S_IFREG":
                result.files.append(
                    FileEntry(
                        path=child,
                        size=int(st.get("st_size") or 0),
                        mtime=as_aware(st.get("st_mtime")),
                        birthtime=as_aware(st.get("st_birthtime")),
                    )
                )
                if on_progress and len(result.files) % 250 == 0:
                    on_progress(len(result.files), child)
                if len(result.files) >= self.max_files:
                    result.truncated = True
                    return
