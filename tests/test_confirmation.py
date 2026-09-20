"""Le consentement ne doit jamais pouvoir être contourné par accident."""
import pytest

import ipsd.cli as cli


class FakeStdin:
    def __init__(self, tty):
        self._tty = tty

    def isatty(self):
        return self._tty


def test_no_terminal_means_no_deletion(monkeypatch, capsys):
    """En arrière-plan ou dans un pipe, on refuse plutôt que de supposer un oui."""
    monkeypatch.setattr(cli.sys, "stdin", FakeStdin(tty=False))
    called = []
    monkeypatch.setattr(cli.click, "confirm", lambda *a, **k: called.append(1) or True)
    assert cli.confirm_deletion("caches", 4, "270 Mo", assume_yes=False) is False
    assert called == [], "aucune question ne doit être posée hors terminal"


def test_user_saying_no_blocks_the_deletion(monkeypatch):
    monkeypatch.setattr(cli.sys, "stdin", FakeStdin(tty=True))
    monkeypatch.setattr(cli.click, "confirm", lambda *a, **k: False)
    assert cli.confirm_deletion("caches", 4, "270 Mo", assume_yes=False) is False


def test_user_saying_yes_allows_it(monkeypatch):
    monkeypatch.setattr(cli.sys, "stdin", FakeStdin(tty=True))
    monkeypatch.setattr(cli.click, "confirm", lambda *a, **k: True)
    assert cli.confirm_deletion("caches", 4, "270 Mo", assume_yes=False) is True


def test_explicit_yes_flag_skips_the_prompt_but_nothing_else_does(monkeypatch):
    monkeypatch.setattr(cli.sys, "stdin", FakeStdin(tty=False))
    monkeypatch.setattr(
        cli.click, "confirm", lambda *a, **k: (_ for _ in ()).throw(AssertionError)
    )
    assert cli.confirm_deletion("caches", 4, "270 Mo", assume_yes=True) is True


def test_prompt_defaults_to_no(monkeypatch):
    """Une pression sur Entrée ne doit rien supprimer."""
    monkeypatch.setattr(cli.sys, "stdin", FakeStdin(tty=True))
    seen = {}

    def fake_confirm(text, default=None, **kwargs):
        seen["default"] = default
        return default

    monkeypatch.setattr(cli.click, "confirm", fake_confirm)
    assert cli.confirm_deletion("caches", 4, "270 Mo", assume_yes=False) is False
    assert seen["default"] is False


def test_socket_errors_are_translated_not_dumped(monkeypatch, capsys):
    """Un câble qui lâche ne doit jamais produire une trace Python."""

    import ipsd.cli as cli

    @cli.coro
    async def boom():
        raise BrokenPipeError(32, "Broken pipe")

    with pytest.raises(SystemExit) as exit_info:
        boom()
    assert exit_info.value.code == 2
    printed = capsys.readouterr()
    assert "Traceback" not in printed.out + printed.err
    assert "BrokenPipeError" in printed.out + printed.err
