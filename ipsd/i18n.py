"""Choix de la langue et résolution des messages.

La langue est demandée une fois, à la première exécution, puis mémorisée.
Homebrew et pipx ne peuvent pas poser de question pendant l'installation :
c'est donc le premier lancement qui s'en charge.

Ordre de résolution, du plus explicite au plus implicite :
    --lang  >  IPSD_LANG  >  fichier de config  >  locale système  >  anglais
"""
from __future__ import annotations

import json
import locale
import os
from pathlib import Path

from .locales import MESSAGES

SUPPORTED = ("en", "fr")
FALLBACK = "en"

CONFIG_PATH = Path.home() / ".config" / "ipsd" / "config.json"

_current: str | None = None


class MissingTranslation(KeyError):
    """Levée quand une clé n'existe pas : un message manquant est un bug."""


def system_language() -> str:
    """Devine la langue depuis l'environnement, sans jamais échouer."""
    for value in (os.environ.get("LC_ALL"), os.environ.get("LANG")):
        if value and value[:2].lower() in SUPPORTED:
            return value[:2].lower()
    try:
        tag = locale.getlocale()[0] or ""
    except (ValueError, TypeError):  # pragma: no cover - locale exotique
        tag = ""
    return tag[:2].lower() if tag[:2].lower() in SUPPORTED else FALLBACK


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_language(lang: str) -> Path:
    lang = normalise(lang)
    config = load_config()
    config["language"] = lang
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return CONFIG_PATH


def normalise(lang: str | None) -> str:
    if not lang:
        return FALLBACK
    short = lang[:2].lower()
    return short if short in SUPPORTED else FALLBACK


def configured_language() -> str | None:
    """Langue mémorisée, ou None si l'utilisateur n'a jamais choisi."""
    stored = load_config().get("language")
    return normalise(stored) if stored in SUPPORTED else None


def resolve(explicit: str | None = None) -> str:
    if explicit:
        return normalise(explicit)
    env = os.environ.get("IPSD_LANG")
    if env:
        return normalise(env)
    stored = configured_language()
    if stored:
        return stored
    return system_language()


def set_language(lang: str | None) -> str:
    global _current
    _current = resolve(lang)
    return _current


def current() -> str:
    return _current or resolve()


def t(key: str, **fmt) -> str:
    """Message traduit dans la langue courante.

    L'absence de traduction lève plutôt que de renvoyer la clé : un texte
    manquant doit casser les tests, pas s'afficher à l'utilisateur.
    """
    entry = MESSAGES.get(key)
    if entry is None:
        raise MissingTranslation(key)
    text = entry.get(current()) or entry.get(FALLBACK)
    if text is None:
        raise MissingTranslation(f"{key} ({current()})")
    return text.format(**fmt) if fmt else text
