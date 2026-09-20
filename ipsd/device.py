"""Connexion au périphérique et lecture des compteurs système."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.usbmux import list_devices


class DeviceError(RuntimeError):
    """Erreur exploitable par l'utilisateur (message déjà en clair)."""


@dataclass
class DiskUsage:
    """Compteurs du domaine com.apple.disk_usage, normalisés."""

    total_disk_capacity: int = 0
    total_data_capacity: int = 0
    total_system_capacity: int = 0
    amount_data_available: int = 0
    total_data_available: int = 0
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def data_used(self) -> int:
        """Espace réellement occupé sur la partition de données."""
        return max(0, self.total_data_capacity - self.amount_data_available)

    @property
    def free(self) -> int:
        """Espace libre immédiat (ce qu'affiche Réglages)."""
        return self.amount_data_available

    @property
    def purgeable(self) -> int:
        """Écart entre le libre « optimiste » d'iOS et le libre immédiat.

        iOS compte ici les caches qu'il sait sacrifier tout seul sous pression.
        """
        return max(0, self.total_data_available - self.amount_data_available)


@dataclass
class DeviceInfo:
    name: str
    udid: str
    product_type: str
    product_version: str
    build: str
    battery_percent: int | None = None


async def list_connected() -> list[dict[str, Any]]:
    """Périphériques visibles par usbmuxd (USB ou Wi-Fi)."""
    out = []
    for dev in await list_devices():
        out.append(
            {
                "udid": getattr(dev, "serial", None) or getattr(dev, "udid", None),
                "connection": getattr(dev, "connection_type", "?"),
            }
        )
    return out


async def connect(udid: str | None = None):
    """Ouvre une session lockdown. Messages d'erreur orientés utilisateur."""
    try:
        return await create_using_usbmux(serial=udid)
    except Exception as exc:  # noqa: BLE001 - on retraduit toutes les causes
        # Le nom de la classe porte l'information quand le message est vide.
        detail = str(exc) or exc.__class__.__name__
        low = f"{exc.__class__.__name__} {detail}".lower().replace("_", "")
        if "nodevice" in low or "no device" in low or "notfound" in low or "not found" in low:
            raise DeviceError(
                "Aucun iPhone détecté. Branche-le en USB, déverrouille-le, "
                "et réponds « Se fier » à la demande d'appairage."
            ) from exc
        if "pair" in low or "password" in low or "trust" in low:
            raise DeviceError(
                "iPhone détecté mais non appairé. Déverrouille l'écran puis "
                "accepte « Se fier à cet ordinateur »."
            ) from exc
        raise DeviceError(f"Connexion impossible : {detail}") from exc


async def get_info(lockdown) -> DeviceInfo:
    battery = None
    try:
        bat = await lockdown.get_value("com.apple.mobile.battery")
        if isinstance(bat, dict):
            battery = bat.get("BatteryCurrentCapacity")
    except Exception:  # noqa: BLE001 - info cosmétique
        pass
    values = {}
    try:
        values = await lockdown.get_value() or {}
    except Exception:  # noqa: BLE001
        values = {}
    return DeviceInfo(
        name=values.get("DeviceName") or getattr(lockdown, "display_name", "iPhone"),
        udid=getattr(lockdown, "udid", "?"),
        product_type=getattr(lockdown, "product_type", "?"),
        product_version=getattr(lockdown, "product_version", "?"),
        build=values.get("BuildVersion", "?"),
        battery_percent=battery,
    )


async def get_disk_usage(lockdown) -> DiskUsage:
    try:
        raw = await lockdown.get_value("com.apple.disk_usage") or {}
    except Exception as exc:  # noqa: BLE001
        raise DeviceError(f"Lecture du stockage impossible : {exc}") from exc
    if not isinstance(raw, dict):
        raise DeviceError("Réponse inattendue du domaine com.apple.disk_usage.")
    clean = {k: v for k, v in raw.items() if isinstance(v, (int, float, str, bool))}
    return DiskUsage(
        total_disk_capacity=int(raw.get("TotalDiskCapacity") or 0),
        total_data_capacity=int(raw.get("TotalDataCapacity") or 0),
        total_system_capacity=int(raw.get("TotalSystemCapacity") or 0),
        amount_data_available=int(raw.get("AmountDataAvailable") or 0),
        total_data_available=int(raw.get("TotalDataAvailable") or 0),
        raw=clean,
    )
