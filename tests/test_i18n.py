"""Le catalogue doit rester complet et cohérent entre les deux langues."""
import re

import pytest

from ipsd import i18n
from ipsd.locales import MESSAGES

PLACEHOLDER = re.compile(r"\{(\w+)")


@pytest.fixture(autouse=True)
def restore_language():
    before = i18n.current()
    yield
    i18n.set_language(before)


def test_every_message_exists_in_both_languages():
    missing = [
        f"{key}:{lang}"
        for key, entry in MESSAGES.items()
        for lang in i18n.SUPPORTED
        if not entry.get(lang)
    ]
    assert missing == [], f"traductions manquantes : {missing}"


def test_both_languages_expect_the_same_variables():
    """Une variable oubliée dans une langue provoquerait un KeyError à l'exécution."""
    mismatched = []
    for key, entry in MESSAGES.items():
        names = {lang: set(PLACEHOLDER.findall(entry[lang])) for lang in i18n.SUPPORTED}
        if len(set(map(frozenset, names.values()))) > 1:
            mismatched.append((key, names))
    assert mismatched == [], f"variables divergentes : {mismatched}"


def test_no_message_is_identical_placeholder_free_french_and_english():
    """Repère les traductions oubliées (texte français laissé en anglais)."""
    suspicious = [
        key
        for key, entry in MESSAGES.items()
        if entry["en"] == entry["fr"] and len(entry["en"]) > 30
    ]
    assert suspicious == []


def test_unknown_key_raises_instead_of_showing_the_key():
    i18n.set_language("en")
    with pytest.raises(i18n.MissingTranslation):
        i18n.t("cette.cle.nexiste.pas")


def test_explicit_language_wins_over_everything(monkeypatch):
    monkeypatch.setenv("IPSD_LANG", "fr")
    assert i18n.resolve("en") == "en"


def test_environment_wins_over_stored_config(monkeypatch):
    monkeypatch.setenv("IPSD_LANG", "fr")
    monkeypatch.setattr(i18n, "configured_language", lambda: "en")
    assert i18n.resolve() == "fr"


def test_stored_config_wins_over_system_locale(monkeypatch):
    monkeypatch.delenv("IPSD_LANG", raising=False)
    monkeypatch.setattr(i18n, "configured_language", lambda: "fr")
    monkeypatch.setattr(i18n, "system_language", lambda: "en")
    assert i18n.resolve() == "fr"


def test_unsupported_language_falls_back_to_english():
    assert i18n.normalise("de") == "en"
    assert i18n.normalise(None) == "en"
    assert i18n.normalise("FR_fr") == "fr"


def test_saving_a_language_round_trips(tmp_path, monkeypatch):
    monkeypatch.setattr(i18n, "CONFIG_PATH", tmp_path / "config.json")
    i18n.save_language("fr")
    assert i18n.configured_language() == "fr"


def test_corrupt_config_does_not_crash(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text("{pas du json", encoding="utf-8")
    monkeypatch.setattr(i18n, "CONFIG_PATH", path)
    assert i18n.configured_language() is None


# --- choix de la langue au premier lancement --------------------------------

def test_first_run_asks_once_then_never_again(monkeypatch, tmp_path):
    import ipsd.cli as cli

    monkeypatch.setattr(i18n, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setattr(cli.sys, "stdin", type("S", (), {"isatty": lambda self: True})())
    asked = []
    monkeypatch.setattr(cli.click, "prompt", lambda *a, **k: asked.append(1) or 2)

    cli.choose_language_once()
    assert asked == [1], "la question doit être posée au premier lancement"
    assert i18n.configured_language() == "fr"

    cli.choose_language_once()
    assert asked == [1], "elle ne doit plus jamais être posée ensuite"


def test_first_run_stays_silent_without_a_terminal(monkeypatch, tmp_path):
    """Dans un script ou un pipe, on ne bloque pas sur une question."""
    import ipsd.cli as cli

    monkeypatch.setattr(i18n, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setattr(cli.sys, "stdin", type("S", (), {"isatty": lambda self: False})())
    monkeypatch.setattr(
        cli.click, "prompt", lambda *a, **k: (_ for _ in ()).throw(AssertionError)
    )
    cli.choose_language_once()
    assert i18n.configured_language() is None
