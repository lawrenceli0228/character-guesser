"""Tests for src/game.py (step 5): the game logic, without input() or print()."""

import pytest

import decision_tree
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


# --- 5f: DecisionTree.expected_entropy-------------------------------------------------
# Average uncertainty left among the top candidates after asking one question,
# weighted by how likely each answer is (the same idea as T2 in ID3).

TWO_EQUAL = [("Ada", 0.5), ("Alan", 0.5)]
ATTRIBUTES_OF = {"Ada": ADA["attributes"], "Alan": ALAN["attributes"]}


def test_5f_question_with_the_same_answer_leaves_all_uncertainty():
    ada_twin = {"is_male": False, "origin_before_1900": True}

    entropy = decision_tree.DecisionTree.expected_entropy(TWO_EQUAL, {"Ada": ADA["attributes"], "Alan": ada_twin}, "is_male")

    # both answer "no", so whatever the player says, it is still 50/50: 1 bit
    assert entropy == pytest.approx(1.0)


def test_5f_question_that_splits_the_candidates_removes_most_uncertainty():
    entropy = decision_tree.DecisionTree.expected_entropy(TWO_EQUAL, ATTRIBUTES_OF, "is_male")

    # yes -> mostly Alan, no -> mostly Ada; only "not sure" (10%) stays 50/50
    assert entropy < 0.5


def test_5f_splitting_question_beats_non_splitting_question():
    same = {"Ada": {"is_male": False}, "Alan": {"is_male": False}}

    assert decision_tree.DecisionTree.expected_entropy(TWO_EQUAL, ATTRIBUTES_OF, "is_male") < \
        decision_tree.DecisionTree.expected_entropy(TWO_EQUAL, same, "is_male")


# --- 5g: Game.focus_question --------------------------------------------------------

def test_5g_focus_question_picks_the_question_that_splits_the_leaders():
    a = make_character("A", is_male=True, is_wizard=True)
    b = make_character("B", is_male=True, is_wizard=False)
    prior = {"A": 0.5, "B": 0.5}

    # is_male is the same for both, is_wizard tells them apart
    assert game.Game.focus_question([a, b], prior, [], 20) == "is_wizard"


def test_5g_focus_question_never_repeats_a_question():
    a = make_character("A", is_male=True, is_wizard=True)
    b = make_character("B", is_male=False, is_wizard=False)
    prior = {"A": 0.5, "B": 0.5}

    assert game.Game.focus_question([a, b], prior, [("is_wizard", "yes")], 20) == "is_male"


def test_5g_focus_question_only_looks_at_the_top_candidates():
    # over all six, splits_leaders_from_rest is better; among the top two (A, B)
    # only splits_a_from_b helps, so top_n=2 must pick it
    a = make_character("A", splits_a_from_b=True, splits_leaders_from_rest=True)
    b = make_character("B", splits_a_from_b=False, splits_leaders_from_rest=True)
    rest = [make_character(n, splits_a_from_b=True, splits_leaders_from_rest=False) for n in "CDEF"]
    prior = {"A": 0.3, "B": 0.3, "C": 0.1, "D": 0.1, "E": 0.1, "F": 0.1}

    assert game.Game.focus_question([a, b] + rest, prior, [], 6) == "splits_leaders_from_rest"
    assert game.Game.focus_question([a, b] + rest, prior, [], 2) == "splits_a_from_b"


# --- 5h: Game.choose_question -------------------------------------------------------
# The tree asks while its node still has plenty of training sheets; after that
# (or once the tree has run out), focus mode picks the question.

BIG_NODE = {"leaf": False, "counts": {"A": 3000, "B": 2000}, "question": "is_male", "branches": {}}
SMALL_NODE = {"leaf": False, "counts": {"A": 30, "B": 20}, "question": "is_male", "branches": {}}


def test_5h_tree_question_while_the_node_has_many_sheets():
    a = make_character("A", is_male=True, is_wizard=True)
    b = make_character("B", is_male=True, is_wizard=False)

    assert game.Game.choose_question(BIG_NODE, [a, b], {"A": 0.5, "B": 0.5}, []) == "is_male"


def test_5h_focus_question_once_the_node_has_few_sheets():
    a = make_character("A", is_male=True, is_wizard=True)
    b = make_character("B", is_male=True, is_wizard=False)

    assert game.Game.choose_question(SMALL_NODE, [a, b], {"A": 0.5, "B": 0.5}, []) == "is_wizard"


def test_5h_focus_question_after_the_tree_has_ended():
    a = make_character("A", is_male=True, is_wizard=True)
    b = make_character("B", is_male=True, is_wizard=False)

    assert game.Game.choose_question(None, [a, b], {"A": 0.5, "B": 0.5}, []) == "is_wizard"

