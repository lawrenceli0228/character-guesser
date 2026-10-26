"""Tests for src/display.py: everything the player sees, built as strings (no print/input).

Display.FANCY switches between the game screen and plain one-line output; tests for the
game screen use the `fancy` fixture, the plain tests run with the default.
"""

import pytest

import display


@pytest.fixture
def fancy(monkeypatch):
    monkeypatch.setattr(display.Display, "FANCY", True)

LONG_QUESTION = ("Is this person from North America, including Mexico, Central America and the Caribbean? "
                 "(For a fictional character: was it created there?)")
GUESSES = [("Severus Snape", 0.62), ("Albus Dumbledore", 0.21), ("Harry Potter", 0.15)]


def lines_of(text):
    return text.split("\n")


# --- title screen -----------------------------------------------------------------

def test_title_names_the_game_and_the_rules(fancy):
    title = display.Display.title(15, 500)

    assert "CHARACTER GUESSER" in title
    assert "15 questions" in title
    assert "500" in title
    assert "y = yes" in title and "n = no" in title and "? = not sure" in title


def test_title_fits_the_screen_width(fancy):
    assert all(len(line) <= display.Display.WIDTH for line in lines_of(display.Display.title(15, 500)))


# --- one question -----------------------------------------------------------------

def test_progress_bar_fills_one_box_per_question_asked():
    assert display.Display.progress_bar(3, 15) == "■" * 3 + "□" * 12


def test_question_shows_its_number_progress_and_text(fancy):
    screen = display.Display.question(3, 15, "Is this person still alive today?")

    assert "Question 3 of 15" in screen
    assert display.Display.progress_bar(3, 15) in screen
    assert "Is this person still alive today?" in screen


def test_long_questions_wrap_to_the_screen_width(fancy):
    screen = display.Display.question(4, 15, LONG_QUESTION)

    assert all(len(line) <= display.Display.WIDTH for line in lines_of(screen))
    assert " ".join(screen.split()).endswith(LONG_QUESTION)


# --- the guess --------------------------------------------------------------------

def test_result_names_the_answer_then_the_others_with_chances(fancy):
    screen = display.Display.result(GUESSES, 15)

    assert "15 questions used" in screen
    assert "My answer: Severus Snape" in screen
    assert "2. Albus Dumbledore (21%)" in screen
    assert "3. Harry Potter (15%)" in screen
    assert screen.index("Severus Snape") < screen.index("Albus Dumbledore") < screen.index("Harry Potter")


def test_result_with_a_single_candidate_has_no_other_list(fancy):
    screen = display.Display.result([("Severus Snape", 1.0)], 15)

    assert "My answer: Severus Snape" in screen
    assert "Other possibilities" not in screen


def test_tiny_chances_show_as_less_than_one_percent_not_zero():
    assert display.Display.chance(0.003) == "<1%"
    assert display.Display.chance(0.21) == "21%"


def test_win_says_how_many_questions_it_took(fancy):
    assert "15 questions" in display.Display.win(15)


# --- plain output (the default while testing) ------------------------------------

def test_plain_question_is_one_line():
    assert display.Display.question(3, 15, "Is this person still alive today?") == "Q3: Is this person still alive today?"


def test_plain_prompt_keeps_the_answer_on_the_same_line():
    assert display.Display.prompt("Q3: Is this person alive?") == "Q3: Is this person alive? (y/n/?) "


def test_plain_result_lists_the_answer_and_the_others():
    assert display.Display.result(GUESSES, 15) == (
        "15 questions used, time to guess!\n"
        "My answer: Severus Snape\n"
        "Other possibilities:\n"
        "  2. Albus Dumbledore (21%)\n"
        "  3. Harry Potter (15%)"
    )


def test_plain_explanation_lists_each_disagreement():
    text = display.Display.explanation("Taylor Swift", 3, [("Has this person won a Grammy Award?", "no", "yes")])

    assert "Taylor Swift" in text and "3" in text
    assert "Has this person won a Grammy Award?" in text
    assert "you said no" in text and "my data says yes" in text


def test_plain_explanation_when_every_answer_matched():
    assert "matched" in display.Display.explanation("Taylor Swift", 2, [])


def test_unknown_character_says_it_is_not_in_the_dataset():
    assert "Grace Hopper" in display.Display.unknown_character("Grace Hopper", 500)
