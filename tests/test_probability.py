"""Tests for src/probability.py (step 2), grouped by sub-step.

Characters use the same format as dataset.load_characters:
{"name": ..., "attributes": {...}, "sitelinks": ...}
"""

from pathlib import Path

import pytest

import dataset
import probability

CHARACTERS_CSV = Path(__file__).resolve().parent.parent / "dataset" / "characters.csv"


def make_character(name, fictional, sitelinks):
    return {"name": name, "attributes": {"is_fictional": fictional}, "sitelinks": sitelinks}


# Real people: median of 400 and 100 is 250. Fictional: median of 40 and 10 is 25.
SAMPLE = [
    make_character("Real A", False, 400),
    make_character("Real B", False, 100),
    make_character("Fictional C", True, 40),
    make_character("Fictional D", True, 10),
]


# --- 2a: normalise ---------------------------------------------------------------

def test_2a_normalise_scales_values_to_sum_one():
    assert probability.normalise({"a": 1.0, "b": 3.0}) == pytest.approx({"a": 0.25, "b": 0.75})


def test_2a_normalise_does_not_change_its_input():
    weights = {"a": 1.0, "b": 3.0}

    probability.normalise(weights)

    assert weights == {"a": 1.0, "b": 3.0}


def test_2a_normalise_rejects_weights_that_sum_to_zero():
    with pytest.raises(ValueError):
        probability.normalise({"a": 0.0, "b": 0.0})


def test_2a_normalise_allows_some_zero_weights():
    # A single zero weight is fine (e.g. a ruled-out character); only a zero TOTAL is a problem.
    assert probability.normalise({"a": 0.0, "b": 1.0}) == pytest.approx({"a": 0.0, "b": 1.0})


# --- 2b: group_medians -----------------------------------------------------------

def test_2b_group_medians_for_real_and_fictional():
    assert probability.group_medians(SAMPLE) == {False: 250, True: 25}


def test_2b_group_medians_with_odd_group_size():
    characters = SAMPLE + [make_character("Real E", False, 1000)]

    assert probability.group_medians(characters)[False] == 400


# --- 2c: popularity_prior --------------------------------------------------------

def test_2c_prior_sums_to_one_and_favours_more_popular():
    prior = probability.popularity_prior(SAMPLE)

    assert sum(prior.values()) == pytest.approx(1.0)
    assert prior["Real A"] > prior["Real B"]
    assert prior["Fictional C"] > prior["Fictional D"]


def test_2c_prior_compares_within_real_and_fictional_groups():
    prior = probability.popularity_prior(SAMPLE)

    # 400 / 250 and 40 / 25 are both 1.6, so A and C get the same weight
    assert prior["Real A"] == pytest.approx(prior["Fictional C"])
    assert prior["Real B"] == pytest.approx(prior["Fictional D"])


def test_2c_prior_uses_square_root_to_soften_differences():
    prior = probability.popularity_prior(SAMPLE)

    # sitelinks differ 4x (400 vs 100), so weights differ sqrt(4) = 2x
    assert prior["Real A"] / prior["Real B"] == pytest.approx(2.0)


def test_2c_prior_on_the_real_dataset():
    characters = dataset.load_characters(CHARACTERS_CSV)

    prior = probability.popularity_prior(characters)

    assert len(prior) == 500
    assert sum(prior.values()) == pytest.approx(1.0)
    assert prior["Barack Obama"] > prior["Ada Lovelace"]
