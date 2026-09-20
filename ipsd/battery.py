"""Santé de la batterie — la vraie cause de lenteur d'un iPhone ancien.

Quand une batterie usée ne tient plus les pics de courant, iOS active la
« gestion des performances » : il plafonne la fréquence du processeur pour
éviter les extinctions brutales. Le téléphone devient lent, et aucun nettoyage
de fichiers n'y changera quoi que ce soit.

Ce module lit les compteurs du contrôleur de charge et calcule la santé réelle,
sans l'arrondi que Réglages applique à son affichage.
"""
from __future__ import annotations

from dataclasses import dataclass

from pymobiledevice3.services.diagnostics import DiagnosticsService

from .i18n import t

# Cycles pour lesquels Apple garantit 80 % de capacité restante.
# Les modèles à partir de l'iPhone 15 sont donnés pour 1000.
RATED_CYCLES_LEGACY = 500
RATED_CYCLES_MODERN = 1000
MODERN_FROM_GENERATION = 16  # iPhone16,x = iPhone 15

HEALTHY = "HEALTHY"
AGING = "AGING"
WORN = "WORN"


@dataclass
class BatteryHealth:
    design_capacity: int
    nominal_capacity: int
    cycle_count: int
    charge_percent: int
    temperature_c: float | None
    rated_cycles: int

    @property
    def health_percent(self) -> float:
        """Capacité restante en pourcentage de la capacité d'origine."""
        if not self.design_capacity:
            return 0.0
        return 100.0 * self.nominal_capacity / self.design_capacity

    @property
    def cycles_ratio(self) -> float:
        return 0.0 if not self.rated_cycles else self.cycle_count / self.rated_cycles

    @property
    def state(self) -> str:
        if self.health_percent < 80 or self.cycles_ratio >= 1.0:
            return WORN
        if self.health_percent < 90 or self.cycles_ratio >= 0.7:
            return AGING
        return HEALTHY

    @property
    def throttling_likely(self) -> bool:
        """Sous 80 %, Apple documente l'activation possible du bridage."""
        return self.health_percent < 80

    def verdict(self) -> str:
        if self.state == WORN:
            return t("battery.verdict.worn")
        if self.state == AGING:
            return t("battery.verdict.aging")
        return t("battery.verdict.healthy")


def rated_cycles_for(product_type: str) -> int:
    """iPhone14,2 -> 500 cycles ; iPhone16,1 et au-delà -> 1000."""
    try:
        generation = int(product_type.lower().replace("iphone", "").split(",")[0])
    except (ValueError, AttributeError):
        return RATED_CYCLES_LEGACY
    return RATED_CYCLES_MODERN if generation >= MODERN_FROM_GENERATION else RATED_CYCLES_LEGACY


async def collect(lockdown, product_type: str = "") -> BatteryHealth | None:
    async with DiagnosticsService(lockdown) as diag:
        try:
            raw = await diag.get_battery()
        except Exception:  # noqa: BLE001 - service absent sur certains modèles
            return None
    if not isinstance(raw, dict) or not raw.get("DesignCapacity"):
        return None
    temperature = raw.get("Temperature")
    return BatteryHealth(
        design_capacity=int(raw.get("DesignCapacity") or 0),
        nominal_capacity=int(raw.get("NominalChargeCapacity") or 0),
        cycle_count=int(raw.get("CycleCount") or 0),
        charge_percent=int(raw.get("CurrentCapacity") or 0),
        # Le contrôleur renvoie des centièmes de degré.
        temperature_c=(temperature / 100.0) if isinstance(temperature, int) else None,
        rated_cycles=rated_cycles_for(product_type),
    )
