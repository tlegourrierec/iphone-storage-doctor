from datetime import UTC, datetime, timedelta

from ipsd.history import Snapshot, diff, load_all, save


def snap(days_ago, free, apps):
    return Snapshot(
        taken_at=datetime.now(UTC) - timedelta(days=days_ago),
        udid="TESTUDID0001",
        free=free,
        used=100 - free,
        apps=apps,
    )


def test_diff_ranks_growth_first_and_ignores_stable_apps():
    old = snap(7, 10, {"Instagram": 1_000, "Stable": 500, "Gone": 300})
    new = snap(0, 8, {"Instagram": 6_000, "Stable": 500, "New": 200})
    changes = diff(old, new)
    assert changes[0] == ("Instagram", 5_000)
    assert ("Stable", 0) not in changes
    assert ("Gone", -300) in changes


def test_snapshots_round_trip_and_filter_by_udid(tmp_path):
    save(snap(1, 12, {"A": 1}), tmp_path)
    save(snap(0, 15, {"A": 2}), tmp_path)
    loaded = load_all("TESTUDID0001", tmp_path)
    assert len(loaded) == 2
    assert loaded[0].taken_at < loaded[1].taken_at  # trié chronologiquement
    assert loaded[1].apps == {"A": 2}
    assert load_all("AUTRE", tmp_path) == []


def test_corrupt_snapshot_is_skipped_not_fatal(tmp_path):
    save(snap(0, 10, {"A": 1}), tmp_path)
    (tmp_path / "broken.json").write_text("{pas du json", encoding="utf-8")
    assert len(load_all(None, tmp_path)) == 1
