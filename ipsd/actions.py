"""Traduire un diagnostic en actions exécutables.

Un rapport qui décrit sans proposer oblige l'utilisateur à faire le travail
d'interprétation. Ce module transforme les constats en gestes précis : une
commande à copier, un gain chiffré, un niveau de risque annoncé.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .apps import AppUsage
from .battery import BatteryHealth
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
                title="Nettoyer les caches régénérables",
                gain_bytes=safe_total + (crash.bytes if crash else 0),
                command="ipsd clean --apply --crash",
                kind=AUTO,
                why="Caches d'analyse et rapports de plantage. iOS les reconstruit seul.",
                caveat="Chaque fichier est copié sur le Mac avant d'être retiré.",
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
                title=f"Réinstaller {app.name}",
                gain_bytes=app.total,
                command=f"ipsd purge --app {app.bundle_id} --apply",
                kind=CHOICE,
                why=f"{app.name} porte {_short(app.data_bytes)} de données pour "
                    f"{_short(app.binary_bytes)} de code.",
                caveat="Tu devras te reconnecter. L'app se retélécharge depuis l'App Store.",
            )
        )

    if battery is not None and battery.throttling_likely:
        plan.actions.append(
            Action(
                title="Faire remplacer la batterie",
                gain_bytes=0,
                command=None,
                kind=EXTERNAL,
                why=f"Santé {battery.health_percent:.0f} %, {battery.cycle_count} cycles. "
                    "iOS bride le processeur en dessous de 80 %.",
                caveat="C'est le seul geste qui rend de la vitesse. Aucun "
                       "nettoyage de fichiers n'y changera rien.",
            )
        )

    if disk is not None and disk.total_data_capacity:
        ratio = disk.free / disk.total_data_capacity
        if ratio < LOW_SPACE_RATIO:
            plan.actions.append(
                Action(
                    title="Descendre sous le seuil critique d'espace",
                    gain_bytes=0,
                    command=None,
                    kind=EXTERNAL,
                    why=f"Il reste {ratio * 100:.0f} % d'espace libre. Sous 10 %, "
                        "APFS n'a plus de marge et tout ralentit.",
                    caveat="C'est le seul cas où libérer de la place accélère "
                           "réellement l'appareil.",
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
            title="Simple",
            gain_bytes=sum(a.gain_bytes for a in auto),
            promise="Caches régénérables et rapports de plantage.",
            cost="Aucune perte. iOS reconstruit tout seul.",
            command="ipsd clean --apply --crash",
            actions=list(auto),
        ),
        Level(
            key=ADVANCED,
            title="Avancé",
            gain_bytes=sum(a.gain_bytes for a in auto + advanced_apps),
            promise="Le simple, plus la réinstallation des apps les plus gonflées.",
            cost="Reconnexion nécessaire sur ces apps. Rien d'irremplaçable.",
            command="ipsd purge --top 3 --apply",
            actions=auto + advanced_apps,
        ),
        Level(
            key=MAXIMUM,
            title="Maximum",
            gain_bytes=sum(a.gain_bytes for a in auto + choices),
            promise="Toutes les apps re-téléchargeables sans données locales uniques.",
            cost="Reconnexion sur chaque app concernée.",
            command="ipsd purge --min-data 400 --apply",
            actions=auto + choices,
        ),
    ]
    return levels
