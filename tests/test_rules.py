from datetime import UTC, datetime, timedelta

from ipsd.apps import AppUsage
from ipsd.rules import MANUAL, SAFE, analyse_apps, analyse_media, sort_findings
from ipsd.scan import FileEntry, ScanResult

NOW = datetime.now(UTC)


def entry(path, size, days_old=1):
    ts = NOW - timedelta(days=days_old)
    return FileEntry(path=path, size=size, mtime=ts, birthtime=ts)


def scan_of(*files):
    return ScanResult(files=list(files))


def find(findings, key):
    return next((f for f in findings if f.key == key), None)


def test_dcim_photos_are_never_marked_deletable():
    """Garde-fou central : supprimer une photo par AFC corrompt Photos.sqlite."""
    scan = scan_of(entry("/DCIM/100APPLE/IMG_0001.MOV", 900_000_000, days_old=400))
    for f in analyse_media(scan):
        assert not (f.tier == SAFE and any(p.startswith("/DCIM") for p in f.paths))
    video = find(analyse_media(scan), "big_old_videos")
    assert video is not None and video.tier == MANUAL


def test_orphan_sidecar_detected_but_paired_one_is_spared():
    scan = scan_of(
        entry("/DCIM/100APPLE/IMG_0002.HEIC", 2_000_000),
        entry("/DCIM/100APPLE/IMG_0002.AAE", 1_200),   # appairé -> intact
        entry("/DCIM/100APPLE/IMG_0003.AAE", 1_500),   # orphelin -> supprimable
    )
    found = find(analyse_media(scan), "orphan_sidecars")
    assert found is not None
    assert found.tier == SAFE
    assert found.paths == ["/DCIM/100APPLE/IMG_0003.AAE"]


def test_recent_downloads_are_left_alone():
    recent = scan_of(entry("/Downloads/facture.pdf", 5_000_000, days_old=3))
    assert find(analyse_media(recent), "stale_downloads") is None
    old = scan_of(entry("/Downloads/vieux.zip", 5_000_000, days_old=200))
    found = find(analyse_media(old), "stale_downloads")
    assert found is not None and found.tier == SAFE


def test_media_analysis_backups_flagged_safe_above_threshold():
    scan = scan_of(entry("/MediaAnalysis/.backup/ocranalysis.aea", 134_000_000))
    found = find(analyse_media(scan), "media_analysis_backup")
    assert found is not None and found.tier == SAFE
    assert found.bytes == 134_000_000


def test_app_bloat_uses_data_to_code_ratio():
    apps = [
        AppUsage("com.burbn.instagram", "Instagram", "User", 579_000_000, 6_599_000_000),
        AppUsage("com.tiny.app", "Tiny", "User", 10_000_000, 1_000_000),
        AppUsage("com.big.binary", "BigBinary", "User", 900_000_000, 20_000_000),
    ]
    found = find(analyse_apps(apps), "app_cache_bloat")
    assert found is not None
    assert "Instagram" in found.detail
    # Une app lourde mais sans cache ne doit pas être signalée comme gonflée.
    assert "BigBinary" not in found.detail


def test_sort_puts_safe_first_then_biggest():
    scan = scan_of(
        entry("/Downloads/vieux.zip", 5_000_000, days_old=200),
        entry("/DCIM/100APPLE/IMG_0001.MOV", 900_000_000, days_old=400),
    )
    ordered = sort_findings(analyse_media(scan))
    assert ordered[0].tier == SAFE
    assert ordered[-1].tier == MANUAL
