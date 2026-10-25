"""Tests for src/train.py (step 5d): Train.train builds the tree from the data."""

import train


def make_character(name, fictional, male, sitelinks=100):
    return {"name": name, "attributes": {"is_fictional": fictional, "is_male": male}, "sitelinks": sitelinks}


CHARACTERS = [
    make_character("Einstein", False, True),
    make_character("Curie", False, False),
    make_character("Batman", True, True),
    make_character("Elsa", True, False),
]
SETTINGS = {"total": 400, "minimum": 20, "seed": 1, "max_depth": 5, "min_sheets": 2}


def test_5d_train_asks_is_fictional_first():
    tree = train.Train.train(CHARACTERS, **SETTINGS)

    assert tree["leaf"] is False
    assert tree["question"] == "is_fictional"


def test_5d_root_counts_cover_every_character():
    tree = train.Train.train(CHARACTERS, **SETTINGS)

    assert set(tree["counts"]) == {"Einstein", "Curie", "Batman", "Elsa"}
    assert sum(tree["counts"].values()) == 400


def test_5d_same_seed_gives_the_same_tree():
    assert train.Train.train(CHARACTERS, **SETTINGS) == train.Train.train(CHARACTERS, **SETTINGS)
