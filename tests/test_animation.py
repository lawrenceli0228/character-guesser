"""Tests for src/animation.py: timed printing for the arcade screen.

time.sleep is replaced by a recorder, so the tests never actually wait.
"""

import pytest

import animation


@pytest.fixture
def sleeps(monkeypatch):
    calls = []
    monkeypatch.setattr(animation.time, "sleep", calls.append)
    return calls


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setattr(animation.Animation, "ON", True)


def test_off_prints_at_once_without_waiting(sleeps, capsys):
    animation.Animation.show("K.O.", delay=0.1)
    animation.Animation.pause(1.0)
    animation.Animation.frames(["3", "2", "1"], 0.7)

    assert capsys.readouterr().out == "K.O.\n3\n2\n1\n"
    assert sleeps == []


def test_empty_text_prints_nothing(capsys):
    animation.Animation.show("")

    assert capsys.readouterr().out == ""


def test_on_types_one_character_at_a_time(on, sleeps, capsys):
    animation.Animation.show("\033[91mK O\033[0m", delay=0.01)

    assert capsys.readouterr().out == "\033[91mK O\033[0m\n"
    assert sleeps == [0.01, 0.01]       # K and O; no wait for the space or the colour codes


def test_on_pauses_after_each_frame(on, sleeps, capsys):
    animation.Animation.frames(["3", "2", "1"], 0.7)

    assert capsys.readouterr().out == "3\n2\n1\n"
    assert sleeps == [0.7, 0.7, 0.7]


def test_progress_redraws_the_same_line(on, sleeps, capsys):
    animation.Animation.progress(["[░░] 0%", "[▓░] 50%", "[▓▓] 100%"], 0.05)

    out = capsys.readouterr().out
    assert out.count("\r") == 3 and out.endswith("[▓▓] 100%\n")


def test_progress_off_prints_only_the_last_frame(sleeps, capsys):
    animation.Animation.progress(["0%", "50%", "100%"], 0.05)

    assert capsys.readouterr().out == "100%\n"
    assert sleeps == []
