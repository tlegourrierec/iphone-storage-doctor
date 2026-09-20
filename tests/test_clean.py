import pytest

from ipsd.clean import build_plan, run, selectable
from ipsd.rules import MANUAL, REVIEW, SAFE, Finding


def finding(key, tier, paths, count=None):
    return Finding(
        key=key,
        title=key.replace("_", " "),
        tier=tier,
        bytes=sum(len(p) for p in paths),
        detail="",
        action="",
        paths=list(paths),
        count=count if count is not None else len(paths),
    )


SIZES = {"/a.aea": 100, "/b.aea": 200, "/photo.HEIC": 9_000}


def test_plan_lists_only_safe_findings():
    findings = [
        finding("cache", SAFE, ["/a.aea", "/b.aea"]),
        finding("musique", REVIEW, ["/Music/x.m4p"]),
        finding("photos", MANUAL, ["/photo.HEIC"]),
    ]
    plan = build_plan(findings, SIZES)
    assert plan.paths == ["/a.aea", "/b.aea"]
    assert plan.total_bytes == 300
    assert plan.lines() == ["cache — 2 fichiers"]


def test_plan_deduplicates_paths_shared_by_two_findings():
    findings = [
        finding("un", SAFE, ["/a.aea"]),
        finding("deux", SAFE, ["/a.aea", "/b.aea"]),
    ]
    plan = build_plan(findings, SIZES)
    assert plan.paths == ["/a.aea", "/b.aea"]
    assert plan.total_bytes == 300


def test_empty_plan_when_nothing_is_safe():
    plan = build_plan([finding("photos", MANUAL, ["/photo.HEIC"])], SIZES)
    assert plan.is_empty is True
    assert plan.total_bytes == 0


def test_a_manual_finding_is_never_selectable_even_with_paths():
    """Garde-fou : un chemin sous /DCIM ne doit jamais devenir supprimable."""
    assert selectable([finding("photos", MANUAL, ["/DCIM/IMG_1.HEIC"])]) == []
    assert selectable([finding("musique", REVIEW, ["/Music/x.m4p"])]) == []


@pytest.mark.asyncio
async def test_dry_run_reports_the_plan_without_touching_the_device():
    """lockdown=None : si run() ouvrait une connexion, le test planterait."""
    findings = [finding("cache", SAFE, ["/a.aea", "/b.aea"])]
    report = await run(None, findings, dry_run=True, sizes=SIZES)
    assert report.dry_run is True
    assert report.planned == 2
    assert report.planned_bytes == 300
    assert report.deleted == 0
