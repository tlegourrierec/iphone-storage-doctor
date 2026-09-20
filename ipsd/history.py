"""Historique local : suivre la dérive du stockage dans le temps.

Un instantané est le seul moyen honnête de répondre à « qu'est-ce qui a grossi
depuis la semaine dernière ? ». Rien ne quitte la machine.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DIR = Path.home() / "iphone-storage-doctor" / "snapshots"


@dataclass
class Snapshot:
    taken_at: datetime
    udid: str
    free: int
    used: int
    apps: dict[str, int]

    def to_dict(self) -> dict:
        return {
            "taken_at": self.taken_at.isoformat(),
            "udid": self.udid,
            "free": self.free,
            "used": self.used,
            "apps": self.apps,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Snapshot":
        return cls(
            taken_at=datetime.fromisoformat(data["taken_at"]),
            udid=data.get("udid", "?"),
            free=int(data.get("free", 0)),
            used=int(data.get("used", 0)),
            apps={k: int(v) for k, v in (data.get("apps") or {}).items()},
        )


def save(snapshot: Snapshot, directory: Path | None = None) -> Path:
    directory = directory or DEFAULT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    stamp = snapshot.taken_at.strftime("%Y%m%d-%H%M%S")
    path = directory / f"{snapshot.udid[:12]}-{stamp}.json"
    path.write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")
    return path


def load_all(udid: str | None = None, directory: Path | None = None) -> list[Snapshot]:
    directory = directory or DEFAULT_DIR
    if not directory.exists():
        return []
    out = []
    for path in sorted(directory.glob("*.json")):
        try:
            snap = Snapshot.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001 - un fichier corrompu n'annule pas le reste
            continue
        if udid is None or snap.udid == udid:
            out.append(snap)
    out.sort(key=lambda s: s.taken_at)
    return out


def diff(old: Snapshot, new: Snapshot) -> list[tuple[str, int]]:
    """Variation par app entre deux instantanés, du plus gros gonflement au plus gros dégonflement."""
    keys = set(old.apps) | set(new.apps)
    changes = [(k, new.apps.get(k, 0) - old.apps.get(k, 0)) for k in keys]
    changes = [c for c in changes if c[1] != 0]
    changes.sort(key=lambda c: -c[1])
    return changes


def snapshot_from(udid: str, disk, apps) -> Snapshot:
    return Snapshot(
        taken_at=datetime.now(timezone.utc),
        udid=udid,
        free=disk.free,
        used=disk.data_used,
        apps={a.name: a.total for a in apps},
    )
