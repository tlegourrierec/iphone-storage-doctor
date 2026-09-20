"""Mesure de l'espace occupé par les applications (installation_proxy).

C'est la partie du stockage qu'AFC ne voit pas, et en pratique la plus grosse.
"""
from __future__ import annotations

from dataclasses import dataclass

from pymobiledevice3.services.installation_proxy import InstallationProxyService


@dataclass(slots=True)
class AppUsage:
    bundle_id: str
    name: str
    app_type: str
    binary_bytes: int
    data_bytes: int

    @property
    def total(self) -> int:
        return self.binary_bytes + self.data_bytes

    @property
    def data_ratio(self) -> float:
        """Part des données (caches, médias) dans le poids total."""
        return 0.0 if not self.total else self.data_bytes / self.total


async def collect(lockdown, include_system: bool = True) -> list[AppUsage]:
    proxy = InstallationProxyService(lockdown)
    apps = await proxy.get_apps(
        application_type="Any" if include_system else "User",
        calculate_sizes=True,
    )
    out: list[AppUsage] = []
    for bundle_id, info in (apps or {}).items():
        if not isinstance(info, dict):
            continue
        out.append(
            AppUsage(
                bundle_id=bundle_id,
                name=info.get("CFBundleDisplayName") or info.get("CFBundleName") or bundle_id,
                app_type=info.get("ApplicationType") or "?",
                binary_bytes=int(info.get("StaticDiskUsage") or 0),
                data_bytes=int(info.get("DynamicDiskUsage") or 0),
            )
        )
    out.sort(key=lambda a: -a.total)
    return out
