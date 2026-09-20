"""Traduire un diagnostic en actions exécutables.

Un rapport qui décrit sans proposer oblige l'utilisateur à faire le travail
d'interprétation. Ce module transforme les constats en gestes précis : une
commande à copier, un gain chiffré, un niveau de risque annoncé.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .apps import AppUsage
from .battery import BatteryHealth
from .i18n import t
from .purge import risk_of
from .rules import SAFE, Finding

# Qui exécute l'action, et donc quel risque l'utilisateur prend.
AUTO = "AUTO"        # l'outil le fait, sans perte de donnée
CHOICE = "CHOICE"    # l'outil le fait, mais la donnée locale part
EXTERNAL = "EXTERNAL"  # l'outil ne peut pas : c'est à faire ailleurs

# En dessous, APFS manque de marge et l'appareil ralentit réellement.
LOW_SPACE_RATIO = 0.10


@dataclass
class Action:
    title: str
    gain_bytes: int
    command: str | None
    kind: str
    why: str
    caveat: str = ""

    @property
    def sort_key(self) -> tuple[int, int]:
        order = {AUTO: 0, CHOICE: 1, EXTERNAL: 2}
        return (order.get(self.kind, 3), -self.gain_bytes)


@dataclass
class ActionPlan:
    actions: list[Action] = field(default_factory=list)

    @property
    def reclaimable_now(self) -> int:
        """Ce que l'outil peut libérer sans que l'utilisateur perde quoi que ce soit."""
        return sum(a.gain_bytes for a in self.actions if a.kind == AUTO)

    @property
    def reclaimable_total(self) -> int:
        return sum(a.gain_bytes for a in self.actions if a.kind in (AUTO, CHOICE))


def build(
    findings: list[Finding],
    apps: list[AppUsage],
    battery: BatteryHealth | None,
    disk=None,
    *,
    max_apps: int = 3,
    min_app_data: int = 400_000_000,
) -> ActionPlan:
    plan = ActionPlan()

    safe_total = sum(f.bytes for f in findings if f.tier == SAFE and f.paths)
    crash = next((f for f in findings if f.key == "crash_reports"), None)
    if safe_total or crash:
        plan.actions.append(
            Action(
                title=t("action.clean.title"),
                gain_bytes=safe_total + (crash.bytes if crash else 0),
                command="ipsd clean --apply --crash",
                kind=AUTO,
                why=t("action.clean.why"),
                caveat=t("action.clean.caveat"),
            )
        )

    # Les apps dont les données dominent : seule la désinstallation les rend.
    heavy = [
        a for a in apps
        if a.data_bytes >= min_app_data and a.app_type != "System" and risk_of(a) is None
    ]
    for app in heavy[:max_apps]:
        plan.actions.append(
            Action(
                title=t("action.reinstall.title", app=app.name),
                gain_bytes=app.total,
                command=f"ipsd purge --app {app.bundle_id} --apply",
                kind=CHOICE,
                why=t(
                    "action.reinstall.why",
                    app=app.name,
                    data=_short(app.data_bytes),
                    code=_short(app.binary_bytes),
                ),
                caveat=t("action.reinstall.caveat"),
            )
        )

    if battery is not None and battery.throttling_likely:
        plan.actions.append(
            Action(
                title=t("action.battery.title"),
                gain_bytes=0,
                command=None,
                kind=EXTERNAL,
                why=t(
                    "action.battery.why",
                    health=f"{battery.health_percent:.0f}",
                    cycles=battery.cycle_count,
                ),
                caveat=t("action.battery.caveat"),
            )
        )

    if disk is not None and disk.total_data_capacity:
        ratio = disk.free / disk.total_data_capacity
        if ratio < LOW_SPACE_RATIO:
            plan.actions.append(
                Action(
                    title=t("action.lowspace.title"),
                    gain_bytes=0,
                    command=None,
                    kind=EXTERNAL,
                    why=t("action.lowspace.why", pct=f"{ratio * 100:.0f}"),
                    caveat=t("action.lowspace.caveat"),
                )
            )

    plan.actions.sort(key=lambda a: a.sort_key)
    return plan


def _short(size: int) -> str:
    from .units import human

    return human(size)


# --------------------------------------------------------------------------
# Les trois niveaux de nettoyage
# --------------------------------------------------------------------------

SIMPLE = "simple"
ADVANCED = "avance"
MAXIMUM = "maximum"


@dataclass
class Level:
    """Un palier de nettoyage : ce qu'il fait, ce qu'il rapporte, ce qu'il coûte."""

    key: str
    title: str
    gain_bytes: int
    promise: str
    cost: str
    command: str
    actions: list[Action] = field(default_factory=list)

    @property
    def is_lossless(self) -> bool:
        return all(a.kind == AUTO for a in self.actions)


def build_levels(
    findings: list[Finding],
    apps: list[AppUsage],
    battery: BatteryHealth | None = None,
    disk=None,
) -> list[Level]:
    """Trois paliers cumulatifs, du sans-risque au maximum récupérable.

    Aucun palier ne touche aux photos, aux bases iOS, ni aux applications
    porteuses de données irremplaçables : ces exclusions sont structurelles,
    pas des options.
    """
    plan = build(findings, apps, battery, disk, max_apps=99)
    auto = [a for a in plan.actions if a.kind == AUTO]
    choices = [a for a in plan.actions if a.kind == CHOICE]

    # Palier 2 : les apps dont les données écrasent le code, les pires d'abord.
    advanced_apps = choices[:3]
    levels = [
        Level(
            key=SIMPLE,
            title=t("levels.simple.title"),
            gain_bytes=sum(a.gain_bytes for a in auto),
            promise=t("levels.simple.promise"),
            cost=t("levels.simple.cost"),
            command="ipsd clean --apply --crash",
            actions=list(auto),
        ),
        Level(
            key=ADVANCED,
            title=t("levels.advanced.title"),
            gain_bytes=sum(a.gain_bytes for a in auto + advanced_apps),
            promise=t("levels.advanced.promise"),
            cost=t("levels.advanced.cost"),
            command="ipsd purge --top 3 --apply",
            actions=auto + advanced_apps,
        ),
        Level(
            key=MAXIMUM,
            title=t("levels.maximum.title"),
            gain_bytes=sum(a.gain_bytes for a in auto + choices),
            promise=t("levels.maximum.promise"),
            cost=t("levels.maximum.cost"),
            command="ipsd purge --min-data 400 --apply",
            actions=auto + choices,
        ),
    ]
    return levels
