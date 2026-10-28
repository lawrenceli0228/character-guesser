"""Tests for src/evaluate.py: simulated players drive the real game (step 6)."""

import random
from pathlib import Path

import pytest

import evaluate
from dataset import Dataset
from decision_tree import DecisionTree
from probability import Probability

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def game_data():
    questions = Dataset.load_questions(ROOT / "dataset" / "questions.csv")
    parents = Dataset.load_parents(ROOT / "dataset" / "questions.csv")
    characters = Dataset.load_characters(ROOT / "dataset" / "characters.csv")
    tree = DecisionTree.load_dst(ROOT / "model" / "tree.json")
    return tree, questions, characters, Probability.popularity_prior(characters), parents


def test_honest_answers_come_from_the_data():
    character = {"name": "A", "attributes": {"is_male": True, "from_uk": None}}

    assert evaluate.Evaluate.answer(character, "is_male", None) == "yes"
    assert evaluate.Evaluate.answer(character, "from_uk", None) == "unknown"


def test_noisy_answers_are_mostly_right():
    character = {"name": "A", "attributes": {"is_male": True}}
    rng = random.Random(1)

    answers = [evaluate.Evaluate.answer(character, "is_male", rng) for _ in range(2000)]

    assert answers.count("yes") / 2000 == pytest.approx(0.85, abs=0.03)


def test_a_run_over_5_characters_finishes_with_sensible_counts(game_data):
    tree, questions, characters, prior, parents = game_data

    res = evaluate.Evaluate.run(characters[:5], 9001, tree, questions, characters, prior, parents)

    assert res["honest_games"] == 5 and res["noisy_games"] == 15
    assert 0 <= res["noisy_first"] <= res["noisy_top3"] <= 15
    assert res["honest_first"] >= 4          # honest players are guessed almost always


def test_the_same_seed_gives_the_same_counts(game_data):
    tree, questions, characters, prior, parents = game_data

    first = evaluate.Evaluate.run(characters[:3], 7, tree, questions, characters, prior, parents)
    again = evaluate.Evaluate.run(characters[:3], 7, tree, questions, characters, prior, parents)

    assert first == again
