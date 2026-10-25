"""Tests for src/game.py (step 5): the game logic, without input() or print()."""

import pytest

import game

LEAF_EINSTEIN = {"leaf": True, "counts": {"Einstein": 4}}
LEAF_CURIE = {"leaf": True, "counts": {"Curie": 4}}
TREE = {
    "leaf": False,
    "counts": {"Einstein": 4, "Curie": 4},
    "question": "is_male",
    "branches": {"yes": LEAF_EINSTEIN, "no": LEAF_CURIE, "unknown": {"leaf": True, "counts": {"Einstein": 4, "Curie": 4}}},
}


# --- 5a: Game.parse_user_input ------------------------------------------------------------

@pytest.mark.parametrize("text", ["y", "yes", "Y", "YES", " yes "])
def test_5a_yes(text):
    assert game.Game.parse_user_input(text) == "yes"


@pytest.mark.parametrize("text", ["n", "no", "N", "No"])
def test_5a_no(text):
    assert game.Game.parse_user_input(text) == "no"


@pytest.mark.parametrize("text", ["u", "unknown", "?", "not sure", "dont know"])
def test_5a_not_sure(text):
    assert game.Game.parse_user_input(text) == "unknown"


@pytest.mark.parametrize("text", ["", "maybe", "yess", "123"])
def test_5a_anything_else_is_none(text):
    assert game.Game.parse_user_input(text) is None


# --- 5b: Game.next_quest-------------------------------------------------------------

def test_5b_next_node_follows_the_answer():
    assert game.Game.next_quest(TREE, "yes") == LEAF_EINSTEIN
    assert game.Game.next_quest(TREE, "no") == LEAF_CURIE


def test_5b_next_node_does_not_change_the_tree():
    before = repr(TREE)

    game.Game.next_quest(TREE, "yes")

    assert repr(TREE) == before


# --- 5c: Game.guess_who------------------------------------------------------------

def test_5c_top_guesses_are_sorted_by_probability():
    node = {"leaf": True, "counts": {"Curie": 1, "Einstein": 6, "Obama": 3}}

    guesses = game.Game.guess_who(node, 3)

    assert [name for name, _ in guesses] == ["Einstein", "Obama", "Curie"]
    assert [p for _, p in guesses] == pytest.approx([0.6, 0.3, 0.1])


def test_5c_top_guesses_returns_at_most_k():
    node = {"leaf": True, "counts": {"a": 5, "b": 3, "c": 1, "d": 1}}

    assert len(game.Game.guess_who(node, 2)) == 2


def test_5c_top_guesses_with_fewer_names_than_k():
    assert game.Game.guess_who(LEAF_EINSTEIN, 3) == [("Einstein", 1.0)]


def test_5c_ties_are_broken_by_name_so_results_are_stable():
    node = {"leaf": True, "counts": {"b": 2, "a": 2}}

    assert [name for name, _ in game.Game.guess_who(node, 2)] == ["a", "b"]


def test_5c_works_on_question_nodes_too():
    # every node has counts, so the game can show the current favourites mid-game
    assert [name for name, _ in game.Game.guess_who(TREE, 2)] == ["Curie", "Einstein"]


# --- 5e: Game.score_guesses ---------------------------------------------------------
# Score every character with ALL answers: prior x P(answer | true value) for each question.

def make_character(name, **attributes):
    return {"name": name, "attributes": attributes, "sitelinks": 100}


ADA = make_character("Ada", is_male=False, origin_before_1900=True)
ALAN = make_character("Alan", is_male=True, origin_before_1900=False)
CHARACTERS = [ADA, ALAN]
EQUAL_PRIOR = {"Ada": 0.5, "Alan": 0.5}


def test_5e_answers_decide_the_order():
    guesses = game.Game.score_guesses(CHARACTERS, EQUAL_PRIOR, [("is_male", "yes")], 2)

    # Alan: 0.5 * 0.85, Ada: 0.5 * 0.05 -> normalised 0.85/0.90 and 0.05/0.90
    assert [name for name, _ in guesses] == ["Alan", "Ada"]
    assert [p for _, p in guesses] == pytest.approx([0.85 / 0.90, 0.05 / 0.90])


def test_5e_one_wrong_answer_lowers_but_does_not_rule_out():
    guesses = dict(game.Game.score_guesses(CHARACTERS, EQUAL_PRIOR, [("is_male", "yes")], 2))

    assert guesses["Ada"] > 0


def test_5e_year_questions_use_the_year_model():
    guesses = game.Game.score_guesses(CHARACTERS, EQUAL_PRIOR, [("origin_before_1900", "yes")], 2)

    # Ada: 0.50 (YEAR_MODEL True -> yes), Alan: 0.10 (YEAR_MODEL False -> yes)
    assert [p for _, p in guesses] == pytest.approx([0.50 / 0.60, 0.10 / 0.60])


def test_5e_prior_breaks_ties_between_matching_answers():
    prior = {"Ada": 0.8, "Alan": 0.2}

    guesses = game.Game.score_guesses(CHARACTERS, prior, [], 2)

    assert guesses == [("Ada", pytest.approx(0.8)), ("Alan", pytest.approx(0.2))]


def test_5e_returns_at_most_k():
    assert len(game.Game.score_guesses(CHARACTERS, EQUAL_PRIOR, [("is_male", "yes")], 1)) == 1
