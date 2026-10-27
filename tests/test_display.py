"""Tests for src/display.py: everything the player sees, built as strings (no print/input).

Display.FANCY switches between the arcade screen and plain one-line output; tests for the
arcade screen use the `fancy` fixture and read the text through `seen` (colour codes removed),
the plain tests run with the default.
"""

import pytest

import display


@pytest.fixture
def fancy(monkeypatch):
    monkeypatch.setattr(display.Display, "FANCY", True)


def seen(text):
    """What the player reads: the text without colour codes."""
    return display.Display.visible(text)


def lines_of(text):
    return seen(text).split("\n")


LONG_QUESTION = ("Is this person from North America, including Mexico, Central America and the Caribbean? "
                 "(For a fictional character: was it created there?)")
GUESSES = [("Severus Snape", 0.62), ("Albus Dumbledore", 0.21), ("Harry Potter", 0.15)]
EVERYONE = [("Severus Snape", 0.62), ("Albus Dumbledore", 0.21), ("Harry Potter", 0.15),
            ("Hermione Granger", 0.0105), ("Ron Weasley", 0.0005)]


# --- helpers for the arcade screen -----------------------------------------------------

def test_visible_removes_colour_codes():
    assert display.Display.visible(display.Display.paint("CPU", display.Display.RED)) == "CPU"


def test_box_lines_all_have_the_screen_width():
    box = display.Display.box(["A K I N A T O R", display.Display.paint("at home", display.Display.PURPLE)],
                              display.Display.PURPLE)

    assert {len(line) for line in lines_of(box)} == {display.Display.WIDTH}


def test_long_names_are_not_spaced_out_if_they_would_not_fit():
    assert display.Display.spaced("Hulk") == "H U L K"
    assert display.Display.spaced("Daenerys Targaryen of House Targaryen") == "DAENERYS TARGARYEN OF HOUSE TARGARYEN"


def test_meter_fills_one_cell_per_ten_percent():
    assert seen(display.Display.meter(0.62)) == "▮" * 6 + "▯" * 4
    assert seen(display.Display.meter(1.0)) == "▮" * 10


def test_suspects_count_characters_above_the_minimum_chance():
    assert display.Display.suspects(EVERYONE) == 4


def test_label_turns_a_question_key_into_a_short_clue():
    assert display.Display.label("look_green_skin") == "GREEN SKIN"
    assert display.Display.label("is_fictional") == "FICTIONAL"
    assert display.Display.label("universe_harry_potter") == "HARRY POTTER"


def test_rank_depends_on_questions_used():
    assert display.Display.rank(5).endswith("S")
    assert display.Display.rank(9).endswith("A")
    assert display.Display.rank(15) == "C"


# --- title screen -----------------------------------------------------------------------

def test_title_names_the_game_and_the_rules(fancy):
    title = " ".join(seen(display.Display.title(15, 500)).split())    # wrapping may split a phrase over two lines

    assert "A K I N A T O R" in title
    assert "15 questions" in title
    assert "500" in title
    assert "y = yes" in title and "n = no" in title and "? = not sure" in title


def test_title_fits_the_screen_width(fancy):
    assert all(len(line) <= display.Display.WIDTH for line in lines_of(display.Display.title(15, 500)))


def test_only_the_arcade_screen_waits_for_start(fancy):
    assert "PRESS ENTER" in seen(display.Display.press_start())


def test_plain_screen_starts_without_waiting():
    assert display.Display.press_start() is None


def test_countdown_goes_3_2_1_fight(fancy):
    frames = [seen(frame).strip() for frame in display.Display.ready()]

    assert frames[1:] == ["3", "2", "1", "▶  F I G H T !"]


# --- one question -----------------------------------------------------------------------

def test_progress_bar_fills_one_block_per_question_asked():
    assert display.Display.progress_bar(3, 15) == "▓" * 3 + "░" * 12


def test_question_shows_its_stage_progress_and_text(fancy):
    screen = seen(display.Display.question(3, 15, "Is this person still alive today?"))

    assert "STAGE 03/15" in screen
    assert display.Display.progress_bar(3, 15) in screen
    assert "Is this person still alive today?" in screen


def test_question_shows_the_mind_read_meter_when_guesses_are_given(fancy):
    screen = seen(display.Display.question(3, 15, "Is this person still alive today?", EVERYONE))

    assert "CPU MIND-READ" in screen and "62%" in screen
    assert "4 suspects left" in screen


def test_long_questions_wrap_to_the_screen_width(fancy):
    screen = display.Display.question(4, 15, LONG_QUESTION, EVERYONE)

    assert all(len(line) <= display.Display.WIDTH for line in lines_of(screen))
    assert " ".join(seen(screen).split()).endswith(LONG_QUESTION)


def test_feedback_shows_how_the_mind_read_changed(fancy):
    before = [("Severus Snape", 0.30), ("Harry Potter", 0.20)]

    text = seen(display.Display.feedback("yes", before, GUESSES))

    assert "CLUE ACQUIRED" in text
    assert "30% ▲ 62%" in text


def test_not_sure_gives_no_clue(fancy):
    assert "NO CLUE" in seen(display.Display.feedback("unknown", GUESSES, GUESSES))


def test_plain_screen_has_no_feedback_or_animation_frames():
    assert display.Display.feedback("yes", GUESSES, GUESSES) == ""
    assert display.Display.ready() == [] and display.Display.loading_frames() == []
    assert display.Display.clues([("is_fictional", "yes")]) == []


# --- before the guess -------------------------------------------------------------------

def test_combo_breaker_only_when_guessing_early(fancy):
    assert "C O M B O" in seen(display.Display.final_round(9, 15))
    assert "C O M B O" not in seen(display.Display.final_round(15, 15))


def test_loading_bar_fills_from_0_to_100_percent(fancy):
    frames = [seen(frame) for frame in display.Display.loading_frames()]

    assert frames[0].endswith("0%") and frames[-1].endswith("100%")
    assert "░" not in frames[-1]


def test_clues_list_the_last_yes_answers(fancy):
    asked = [("is_fictional", "yes"), ("is_male", "no"), ("look_green_skin", "yes")]

    assert [seen(clue).strip() for clue in display.Display.clues(asked)] == ["✓ FICTIONAL", "✓ GREEN SKIN"]


# --- the guess ----------------------------------------------------------------------------

def test_result_names_the_answer_then_the_others_with_chances(fancy):
    screen = seen(display.Display.result(GUESSES, 15))

    assert "15 questions used" in screen
    assert "S E V E R U S   S N A P E" in screen
    assert "2P  Albus Dumbledore" in screen and "21%" in screen
    assert "3P  Harry Potter" in screen and "15%" in screen
    assert screen.index("S E V E R U S") < screen.index("Albus Dumbledore") < screen.index("Harry Potter")


def test_result_with_a_single_candidate_has_no_other_list(fancy):
    screen = seen(display.Display.result([("Severus Snape", 1.0)], 15))

    assert "S E V E R U S   S N A P E" in screen
    assert "2P" not in screen


def test_result_fits_the_screen_width(fancy):
    assert all(len(line) <= display.Display.WIDTH for line in lines_of(display.Display.result(GUESSES, 9)))


def test_tiny_chances_show_as_less_than_one_percent_not_zero():
    assert display.Display.chance(0.003) == "<1%"
    assert display.Display.chance(0.21) == "21%"


def test_win_says_how_many_questions_it_took(fancy):
    screen = seen(display.Display.win(15, 0.97))

    assert "15 questions" in screen
    assert "97%" in screen and "C P U   W I N S" in screen


def test_explanation_lists_each_critical_miss(fancy):
    text = seen(display.Display.explanation("Taylor Swift", 3, [("Has this person won a Grammy Award?", "no", "yes")]))

    assert "B A T T L E" in text and "1 critical miss" in text
    assert "Has this person won a Grammy Award?" in text
    assert "P1 NO" in text and "CPU DATA YES" in text


def test_explanation_fits_the_screen_width(fancy):
    text = display.Display.explanation("Hermione Granger", 1, [])

    assert all(len(line) <= display.Display.WIDTH for line in lines_of(text))


def test_score_shows_cpu_against_player(fancy):
    score = {"cpu": 2, "player": 1}

    assert "CPU 2 : 1 P1" in seen(display.Display.play_again(score))
    assert "CPU 2 : 1 P1" in seen(display.Display.goodbye(score))


# --- plain output (the default while testing) ------------------------------------------

def test_plain_question_is_one_line():
    assert display.Display.question(3, 15, "Is this person still alive today?") == "Q3: Is this person still alive today?"


def test_plain_question_ignores_the_guesses():
    assert display.Display.question(3, 15, "Is this person alive?", EVERYONE) == "Q3: Is this person alive?"


def test_retry_on_the_arcade_screen_does_not_redraw_the_question(fancy):
    assert seen(display.Display.retry("Q3: Is this person alive?")).strip() == "PLAYER 1 >"


def test_plain_retry_asks_the_whole_question_again():
    assert display.Display.retry("Q3: Is this person alive?") == "Q3: Is this person alive? (y/n/?) "


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


def test_plain_play_again_and_goodbye_are_unchanged():
    assert display.Display.play_again({"cpu": 1, "player": 0}) == "Play again?"
    assert display.Display.goodbye({"cpu": 1, "player": 0}) == "Thanks for playing!"


def test_unknown_character_says_it_is_not_in_the_dataset():
    assert "Grace Hopper" in display.Display.unknown_character("Grace Hopper", 500)
