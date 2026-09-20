import pytest

from ipsd.actions import (
    ADVANCED,
    AUTO,
    CHOICE,
    EXTERNAL,
    MAXIMUM,
    SIMPLE,
    build,
    build_levels,
)
from ipsd.apps import AppUsage
from ipsd.battery import BatteryHealth
from ipsd.i18n import set_language
from ipsd.rules import MANUAL, SAFE, Finding


@pytest.fixture(autouse=True)
def _french():
    """Ces tests vérifient le contenu des messages : on fixe la langue."""
    set_language("fr")


def finding(key, tier=SAFE, size=100_000_000, paths=("/a.aea",)):
    return Finding(key, key, tier, size, "", "", list(paths), len(paths))


def app(bundle, name, binary=100_000_000, data=2_000_000_000, kind="User"):
    return AppUsage(bundle, name, kind, binary, data)


def battery(health=74.0, cycles=1431):
    return BatteryHealth(3076, int(3076 * health / 100), cycles, 70, 40.0, 500)


class Disk:
    def __init__(self, free, capacity=100_000_000_000):
        self.free = free
        self.total_data_capacity = capacity


def titles(plan):
    return [a.title for a in plan.actions]


def test_safe_findings_become_a_one_command_action():
    plan = build([finding("cache")], [], None)
    action = plan.actions[0]
    assert action.kind == AUTO
    assert action.command == "ipsd clean --apply --crash"
    assert plan.reclaimable_now == 100_000_000


def test_manual_findings_never_produce_an_action():
    plan = build([finding("photos", tier=MANUAL, paths=("/DCIM/IMG.HEIC",))], [], None)
    assert plan.actions == []


def test_risky_apps_are_not_offered_as_actions():
    """Un Authenticator ne doit jamais apparaître dans un plan d'action."""
    apps = [app("com.authy.authy", "Authy"), app("com.zhiliaoapp.musically", "TikTok")]
    plan = build([], apps, None)
    assert titles(plan) == ["Réinstaller TikTok"]
    assert plan.actions[0].kind == CHOICE


def test_small_apps_are_below_the_threshold():
    plan = build([], [app("com.tiny", "Tiny", data=10_000_000)], None)
    assert plan.actions == []


def test_worn_battery_adds_an_action_the_tool_cannot_perform():
    plan = build([], [], battery(health=74.0))
    action = plan.actions[0]
    assert action.kind == EXTERNAL
    assert action.command is None
    assert action.gain_bytes == 0


def test_healthy_battery_adds_nothing():
    assert build([], [], battery(health=95.0, cycles=100)).actions == []


def test_low_free_space_is_flagged_only_under_ten_percent():
    assert build([], [], None, Disk(free=5_000_000_000)).actions[0].kind == EXTERNAL
    assert build([], [], None, Disk(free=30_000_000_000)).actions == []


def test_actions_are_ordered_safest_first_then_by_gain():
    apps = [
        app("com.a", "Grosse", data=5_000_000_000),
        app("com.b", "Moyenne", data=1_000_000_000),
    ]
    plan = build([finding("cache")], apps, battery(health=70.0))
    kinds = [a.kind for a in plan.actions]
    assert kinds == [AUTO, CHOICE, CHOICE, EXTERNAL]
    assert titles(plan)[1] == "Réinstaller Grosse"


# --- les trois niveaux ------------------------------------------------------


def sample_apps():
    return [
        app("com.zhiliaoapp.musically", "TikTok", data=1_800_000_000),
        app("com.facebook.Facebook", "Facebook", data=660_000_000),
        app("com.linkedin.LinkedIn", "LinkedIn", data=590_000_000),
        app("com.curio.app", "Curio", data=830_000_000),
        app("com.authy.authy", "Authy", data=900_000_000),
        app("com.adobe.lrmobilephone", "Lightroom", data=1_000_000_000),
    ]


def test_levels_are_cumulative():
    levels = build_levels([finding("cache")], sample_apps(), None)
    gains = [lv.gain_bytes for lv in levels]
    assert gains[0] < gains[1] <= gains[2]
    assert [lv.key for lv in levels] == [SIMPLE, ADVANCED, MAXIMUM]


def test_simple_level_loses_nothing():
    simple = build_levels([finding("cache")], sample_apps(), None)[0]
    assert simple.is_lossless is True
    assert simple.gain_bytes == 100_000_000


def test_no_level_ever_includes_an_app_holding_unique_data():
    """Authy et Lightroom ne doivent apparaître dans AUCUN palier, même le maximum."""
    for level in build_levels([finding("cache")], sample_apps(), None):
        names = " ".join(a.title for a in level.actions)
        assert "Authy" not in names
        assert "Lightroom" not in names


def test_no_level_ever_includes_photos():
    photos = finding("photos", tier=MANUAL, size=9_000_000_000, paths=("/DCIM/IMG.HEIC",))
    for level in build_levels([photos], sample_apps(), None):
        assert all("/DCIM" not in (a.command or "") for a in level.actions)
        assert level.gain_bytes < 9_000_000_000


def test_maximum_covers_every_eligible_app():
    levels = build_levels([], sample_apps(), None)
    eligible = {"TikTok", "Facebook", "LinkedIn", "Curio"}
    covered = {t for a in levels[2].actions for t in eligible if t in a.title}
    assert covered == eligible
