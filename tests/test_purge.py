import pytest

from ipsd.apps import AppUsage
from ipsd.i18n import set_language
from ipsd.purge import candidates, risk_of, run, select


@pytest.fixture(autouse=True)
def _french():
    """Ces tests vérifient le contenu des messages : on fixe la langue."""
    set_language("fr")


def app(bundle, name, binary=100_000_000, data=500_000_000, kind="User"):
    return AppUsage(bundle, name, kind, binary, data)


@pytest.mark.parametrize(
    "bundle,name",
    [
        ("com.microsoft.azureauthenticator", "Authenticator"),
        ("net.whatsapp.WhatsAppSMB", "WA Business"),
        ("io.metamask.MetaMask", "MetaMask"),
        ("com.adobe.lrmobilephone", "Lightroom"),
    ],
)
def test_apps_holding_irreplaceable_data_are_flagged(bundle, name):
    assert risk_of(app(bundle, name)) is not None


@pytest.mark.parametrize(
    "bundle,name",
    [("com.zhiliaoapp.musically", "TikTok"), ("com.facebook.Facebook", "Facebook")],
)
def test_ordinary_apps_are_not_flagged(bundle, name):
    assert risk_of(app(bundle, name)) is None


def test_system_apps_are_excluded_by_default():
    apps = [app("com.apple.mobilesafari", "Safari", data=749_000_000, kind="System")]
    assert candidates(apps) == []
    assert len(candidates(apps, include_system=True)) == 1


def test_candidates_respect_the_data_threshold_and_sort_by_gain():
    apps = [
        app("a.small", "Small", data=10_000_000),
        app("b.big", "Big", binary=1_000_000_000, data=900_000_000),
        app("c.mid", "Mid", data=300_000_000),
    ]
    got = candidates(apps, min_data=200_000_000)
    assert [c.app.name for c in got] == ["Big", "Mid"]


def test_select_matches_bundle_id_exactly_then_falls_back_to_name():
    apps = [app("com.zhiliaoapp.musically", "TikTok"), app("com.other.tik", "Tik Helper")]
    found, missing = select(apps, ("com.zhiliaoapp.musically",))
    assert [c.app.bundle_id for c in found] == ["com.zhiliaoapp.musically"]
    assert missing == []

    found, missing = select(apps, ("inconnue",))
    assert found == [] and missing == ["inconnue"]


@pytest.mark.asyncio
async def test_risky_apps_are_skipped_unless_explicitly_allowed():
    risky = candidates([app("com.authy.authy", "Authy")], min_data=1)
    report = await run(None, risky, dry_run=True, allow_risky=False)
    assert report.removed == []
    assert report.skipped and "deux facteurs" in report.skipped[0][1]

    report = await run(None, risky, dry_run=True, allow_risky=True)
    assert report.removed == ["com.authy.authy"]


@pytest.mark.asyncio
async def test_dry_run_never_touches_the_device():
    """run() en simulation ne doit instancier aucun service : lockdown=None."""
    chosen = candidates([app("com.zhiliaoapp.musically", "TikTok")], min_data=1)
    report = await run(None, chosen, dry_run=True)
    assert report.dry_run is True
    assert report.freed_estimate == 600_000_000
