"""Tests for src/simulate.py (step 3): simulated answer sheets for training ID3.

Randomness uses random.Random(seed), so every run gives the same sheets.
Frequency checks draw many answers and allow a small tolerance.
"""

import random
from collections import Counter

import pytest

import simulate

DRAWS = 20000
TOLERANCE = 0.02


def answer_shares(value, seed=1):
    rng = random.Random(seed)
    counts = Counter(simulate.simulate_answer(value, rng) for _ in range(DRAWS))
    return {answer: counts[answer] / DRAWS for answer in ("yes", "no", "unknown")}


def make_character(name, **attributes):
    return {"name": name, "attributes": attributes, "sitelinks": 100}


# --- 3a: simulate_answer --------------------------------------------------------

def test_3a_answers_are_yes_no_or_unknown():
    rng = random.Random(0)

    answers = {simulate.simulate_answer(value, rng) for value in (True, False, None) for _ in range(200)}

    assert answers == {"yes", "no", "unknown"}


def test_3a_true_is_mostly_answered_yes():
    shares = answer_shares(True)

    assert shares["yes"] == pytest.approx(0.85, abs=TOLERANCE)
    assert shares["no"] == pytest.approx(0.05, abs=TOLERANCE)
    assert shares["unknown"] == pytest.approx(0.10, abs=TOLERANCE)


def test_3a_false_is_mostly_answered_no():
    shares = answer_shares(False)

    assert shares["no"] == pytest.approx(0.85, abs=TOLERANCE)
    assert shares["yes"] == pytest.approx(0.05, abs=TOLERANCE)


def test_3a_unknown_value_is_often_answered_not_sure():
    shares = answer_shares(None)

    assert shares["unknown"] == pytest.approx(0.40, abs=TOLERANCE)
    assert shares["yes"] == pytest.approx(0.30, abs=TOLERANCE)
    assert shares["no"] == pytest.approx(0.30, abs=TOLERANCE)


def test_3a_same_seed_gives_same_answers():
    first = [simulate.simulate_answer(True, random.Random(42)) for _ in range(5)]
    second = [simulate.simulate_answer(True, random.Random(42)) for _ in range(5)]

    assert first == second


# --- 3b: make_sheet -------------------------------------------------------------

def test_3b_sheet_answers_every_attribute_and_carries_the_name():
    character = make_character("Ada", is_fictional=False, is_male=False, from_uk=True)

    answers, name = simulate.make_sheet(character, random.Random(0))

    assert name == "Ada"
    assert set(answers) == {"is_fictional", "is_male", "from_uk"}
    assert set(answers.values()) <= {"yes", "no", "unknown"}


def test_3b_sheets_mostly_match_the_character():
    character = make_character("Ada", is_fictional=False, from_uk=True)
    rng = random.Random(3)

    sheets = [simulate.make_sheet(character, rng)[0] for _ in range(2000)]

    assert sum(sheet["is_fictional"] == "no" for sheet in sheets) / 2000 == pytest.approx(0.85, abs=0.03)
    assert sum(sheet["from_uk"] == "yes" for sheet in sheets) / 2000 == pytest.approx(0.85, abs=0.03)


def test_3b_year_questions_are_often_answered_not_sure():
    # players rarely know exact birth years, so origin_* questions use YEAR_MODEL
    character = make_character("Ada", origin_before_1900=True, from_uk=True)
    rng = random.Random(5)

    sheets = [simulate.make_sheet(character, rng)[0] for _ in range(4000)]

    year_answers = Counter(sheet["origin_before_1900"] for sheet in sheets)
    assert year_answers["unknown"] / 4000 == pytest.approx(0.40, abs=0.03)
    assert year_answers["yes"] / 4000 == pytest.approx(0.50, abs=0.03)
    assert sum(sheet["from_uk"] == "unknown" for sheet in sheets) / 4000 == pytest.approx(0.10, abs=0.03)


def test_3b_year_model_is_a_valid_answer_model():
    for value in (True, False, None):
        assert sum(simulate.YEAR_MODEL[value].values()) == pytest.approx(1.0)


def test_3b_answer_model_picks_the_year_model_for_year_questions():
    assert simulate.answer_model("origin_before_1900") is simulate.YEAR_MODEL
    assert simulate.answer_model("is_male") is simulate.ANSWER_MODEL


# --- 3c: sheet_counts -------------------------------------------------------------

def test_3c_counts_follow_the_prior():
    counts = simulate.sheet_counts({"a": 0.75, "b": 0.25}, total=100, minimum=1)

    assert counts == {"a": 75, "b": 25}


def test_3c_counts_are_rounded_not_truncated():
    # 0.29 * 100 is 28.999999999999996 in floating point; truncating would give 28
    counts = simulate.sheet_counts({"a": 0.29, "b": 0.71}, total=100, minimum=1)

    assert counts == {"a": 29, "b": 71}


def test_3c_every_character_gets_at_least_the_minimum():
    counts = simulate.sheet_counts({"famous": 0.99, "obscure": 0.01}, total=100, minimum=20)

    assert counts["obscure"] == 20
    assert counts["famous"] == 99


# --- 3d: make_sheets ----------------------------------------------------------------

def test_3d_make_sheets_uses_the_counts_and_is_reproducible():
    characters = [make_character("Ada", is_male=False), make_character("Alan", is_male=True)]
    prior = {"Ada": 0.5, "Alan": 0.5}

    sheets = simulate.make_sheets(characters, prior, total=40, minimum=5, seed=7)
    again = simulate.make_sheets(characters, prior, total=40, minimum=5, seed=7)

    assert len(sheets) == 40
    assert Counter(name for _, name in sheets) == {"Ada": 20, "Alan": 20}
    assert sheets == again


def test_3d_different_seeds_give_different_sheets():
    characters = [make_character("Ada", is_male=False, from_uk=True)]
    prior = {"Ada": 1.0}

    first = simulate.make_sheets(characters, prior, total=50, minimum=1, seed=1)
    second = simulate.make_sheets(characters, prior, total=50, minimum=1, seed=2)

    assert first != second


def test_3b_award_questions_use_the_award_model():
    # players often do not know who won an Oscar or a Grammy
    assert simulate.answer_model("award_oscar") is simulate.AWARD_MODEL
    assert simulate.answer_model("award_grammy") is simulate.AWARD_MODEL
    assert simulate.answer_model("won_nobel_prize") is simulate.ANSWER_MODEL


def test_3b_award_model_is_a_valid_answer_model():
    for value in (True, False, None):
        assert sum(simulate.AWARD_MODEL[value].values()) == pytest.approx(1.0)
