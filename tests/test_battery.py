import pytest

from ipsd.battery import AGING, HEALTHY, WORN, BatteryHealth, rated_cycles_for
from ipsd.i18n import set_language


@pytest.fixture(autouse=True)
def _french():
    """Ces tests vérifient le contenu des messages : on fixe la langue."""
    set_language("fr")


def battery(design=3076, nominal=2288, cycles=1431, rated=500):
    return BatteryHealth(
        design_capacity=design,
        nominal_capacity=nominal,
        cycle_count=cycles,
        charge_percent=70,
        temperature_c=40.0,
        rated_cycles=rated,
    )


def test_health_is_computed_from_raw_capacities_not_rounded():
    """Réglages arrondit ; on veut le rapport brut."""
    assert round(battery().health_percent, 1) == 74.4


def test_worn_battery_predicts_throttling():
    worn = battery()
    assert worn.state == WORN
    assert worn.throttling_likely is True
    assert "bride le processeur" in worn.verdict()


def test_healthy_battery_points_the_user_elsewhere():
    fresh = battery(nominal=3000, cycles=120)
    assert fresh.state == HEALTHY
    assert fresh.throttling_likely is False
    assert "vient d'ailleurs" in fresh.verdict()


def test_aging_battery_sits_between_the_two():
    aging = battery(nominal=2650, cycles=380)  # 86 %, 76 % des cycles
    assert aging.state == AGING


def test_cycle_rating_depends_on_the_model_generation():
    assert rated_cycles_for("iPhone14,2") == 500   # iPhone 13 Pro
    assert rated_cycles_for("iPhone16,1") == 1000  # iPhone 15 Pro
    assert rated_cycles_for("iPhone17,3") == 1000
    assert rated_cycles_for("nimporte quoi") == 500


def test_missing_design_capacity_does_not_divide_by_zero():
    assert battery(design=0).health_percent == 0.0
    assert battery(rated=0).cycles_ratio == 0.0
