"""Tests for src/main.py: --arcade chooses the arcade screen, plain lines without it."""

import pytest

import animation
import display
import main


@pytest.fixture(autouse=True)
def plain_screen_and_no_game(monkeypatch):
    monkeypatch.setattr(display.Display, "FANCY", False)
    monkeypatch.setattr(animation.Animation, "ON", False)
    monkeypatch.setattr(main.Game, "play", staticmethod(lambda: None))


def test_arcade_flag_turns_on_the_arcade_screen(monkeypatch):
    monkeypatch.setattr(main.sys, "argv", ["main.py", "--arcade"])

    main.main()

    assert display.Display.FANCY is True and animation.Animation.ON is True


def test_plain_screen_without_the_flag(monkeypatch):
    monkeypatch.setattr(main.sys, "argv", ["main.py"])

    main.main()

    assert display.Display.FANCY is False and animation.Animation.ON is False
