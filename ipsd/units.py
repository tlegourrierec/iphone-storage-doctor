"""Formatage et petites conversions partagées."""
from __future__ import annotations

from datetime import UTC, datetime

_UNITS = ("o", "Ko", "Mo", "Go", "To")


def human(size: float) -> str:
    """Formate une taille en base 1000 (comme le fait iOS/Finder)."""
    value = float(size)
    for unit in _UNITS:
        if abs(value) < 1000 or unit == _UNITS[-1]:
            if unit == "o":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1000
    return f"{value:.1f} To"


def now() -> datetime:
    return datetime.now(UTC)


def as_aware(dt: datetime | None) -> datetime | None:
    """AFC renvoie des datetimes naïfs; on les rend comparables."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def age_days(dt: datetime | None, reference: datetime | None = None) -> float | None:
    dt = as_aware(dt)
    if dt is None:
        return None
    reference = reference or now()
    return (reference - dt).total_seconds() / 86400.0


def pct(part: float, whole: float) -> float:
    return 0.0 if not whole else 100.0 * part / whole
