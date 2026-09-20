from datetime import UTC, datetime, timedelta

from ipsd.units import age_days, as_aware, human, pct


def test_human_uses_base_1000_like_ios():
    assert human(0) == "0 o"
    assert human(999) == "999 o"
    assert human(1_000) == "1.0 Ko"
    assert human(1_500_000) == "1.5 Mo"
    assert human(7_178_000_000) == "7.2 Go"


def test_as_aware_makes_naive_afc_dates_comparable():
    naive = datetime(2026, 1, 1, 12, 0)
    aware = as_aware(naive)
    assert aware is not None and aware.tzinfo is not None
    assert as_aware(None) is None


def test_age_days():
    ref = datetime(2026, 9, 20, tzinfo=UTC)
    assert age_days(ref - timedelta(days=10), ref) == 10
    assert age_days(None) is None


def test_pct_handles_zero_division():
    assert pct(5, 0) == 0.0
    assert pct(50, 200) == 25.0
