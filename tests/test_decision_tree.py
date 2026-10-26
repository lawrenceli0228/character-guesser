"""Tests for src/decision_tree.py (step 4): building a decision tree with ID3.

A sheet is (answers, name), as made by simulate.make_sheet, e.g.
({"is_male": "yes", "is_fictional": "no"}, "Albert Einstein").

A tree is nested dictionaries:
- leaf:  {"leaf": True,  "counts": {name: number of sheets}}
- node:  {"leaf": False, "counts": {...}, "question": attribute,
          "branches": {"yes": tree, "no": tree, "unknown": tree}}
"counts" on every node lets the game show the most likely names at any point.
"""

import math

import pytest

import decision_tree


def sheet(name, **answers):
    return (answers, name)


# Two people that "is_male" separates perfectly; "is_fictional" separates nobody.
EINSTEIN = [sheet("Einstein", is_male="yes", is_fictional="no") for _ in range(4)]
CURIE = [sheet("Curie", is_male="no", is_fictional="no") for _ in range(4)]
TWO_PEOPLE = EINSTEIN + CURIE


# --- 4a: entropy ------------------------------------------------------------------

def test_4a_entropy_of_one_name_is_zero():
    assert decision_tree.DecisionTree.entropy(["Einstein", "Einstein", "Einstein"]) == 0


def test_4a_entropy_of_two_equal_names_is_one():
    assert decision_tree.DecisionTree.entropy(["Einstein", "Curie"]) == pytest.approx(1.0)


def test_4a_entropy_of_eight_equal_names_is_three():
    assert decision_tree.DecisionTree.entropy(list("abcdefgh")) == pytest.approx(3.0)


def test_4a_entropy_of_unequal_shares():
    # 3/4 a, 1/4 b: -(0.75 log2 0.75 + 0.25 log2 0.25)
    expected = -(0.75 * math.log2(0.75) + 0.25 * math.log2(0.25))

    assert decision_tree.DecisionTree.entropy(["a", "a", "a", "b"]) == pytest.approx(expected)


def test_4a_entropy_of_nothing_is_zero():
    assert decision_tree.DecisionTree.entropy([]) == 0


# --- 4b: split --------------------------------------------------------------------

def test_4b_split_groups_sheets_by_answer():
    sheets = [sheet("A", q="yes"), sheet("B", q="no"), sheet("C", q="unknown"), sheet("D", q="yes")]

    groups = decision_tree.DecisionTree.split(sheets, "q")

    assert [name for _, name in groups["yes"]] == ["A", "D"]
    assert [name for _, name in groups["no"]] == ["B"]
    assert [name for _, name in groups["unknown"]] == ["C"]


def test_4b_split_always_has_three_groups():
    groups = decision_tree.DecisionTree.split([sheet("A", q="yes")], "q")

    assert groups == {"yes": [sheet("A", q="yes")], "no": [], "unknown": []}


# --- 4c: information_gain -----------------------------------------------------------

def test_4c_a_perfect_question_gains_all_the_entropy():
    assert decision_tree.DecisionTree.information_gain(TWO_PEOPLE, "is_male") == pytest.approx(1.0)


def test_4c_a_useless_question_gains_nothing():
    assert decision_tree.DecisionTree.information_gain(TWO_PEOPLE, "is_fictional") == pytest.approx(0.0)


def test_4c_a_partly_useful_question_gains_something():
    noisy = EINSTEIN + CURIE[:3] + [sheet("Curie", is_male="yes", is_fictional="no")]  # one wrong answer

    gain = decision_tree.DecisionTree.information_gain(noisy, "is_male")

    assert 0 < gain < 1


# --- 4d: best_question --------------------------------------------------------------

def test_4d_best_question_picks_the_highest_gain():
    assert decision_tree.DecisionTree.best_question(TWO_PEOPLE, ["is_fictional", "is_male"]) == "is_male"


def test_4d_best_question_is_none_when_nothing_helps():
    assert decision_tree.DecisionTree.best_question(TWO_PEOPLE, ["is_fictional"]) is None


def test_4d_ties_go_to_the_first_question_in_the_list():
    sheets = [sheet("A", p="yes", q="yes"), sheet("B", p="no", q="no")]

    assert decision_tree.DecisionTree.best_question(sheets, ["q", "p"]) == "q"


# --- 4e: build_tree ------------------------------------------------------------------

ATTRIBUTES = ["is_fictional", "is_male"]


def test_4e_tree_asks_the_useful_question_and_ends_in_pure_leaves():
    tree = decision_tree.DecisionTree.build_tree(TWO_PEOPLE, ATTRIBUTES, max_depth=10, min_sheets=1)

    assert tree["leaf"] is False
    assert tree["question"] == "is_male"
    assert tree["counts"] == {"Einstein": 4, "Curie": 4}
    assert tree["branches"]["yes"] == {"leaf": True, "counts": {"Einstein": 4}}
    assert tree["branches"]["no"] == {"leaf": True, "counts": {"Curie": 4}}


def test_4e_empty_branch_becomes_a_leaf_with_the_parent_counts():
    tree = decision_tree.DecisionTree.build_tree(TWO_PEOPLE, ATTRIBUTES, max_depth=10, min_sheets=1)

    # Nobody answered "unknown" to is_male, so that branch falls back to the parent's counts.
    assert tree["branches"]["unknown"] == {"leaf": True, "counts": {"Einstein": 4, "Curie": 4}}


def test_4e_one_name_gives_a_single_leaf():
    assert decision_tree.DecisionTree.build_tree(EINSTEIN, ATTRIBUTES, max_depth=10, min_sheets=1) == {"leaf": True, "counts": {"Einstein": 4}}


def test_4e_depth_limit_stops_the_tree():
    assert decision_tree.DecisionTree.build_tree(TWO_PEOPLE, ATTRIBUTES, max_depth=0, min_sheets=1)["leaf"] is True


def test_4e_too_few_sheets_stops_the_tree():
    assert decision_tree.DecisionTree.build_tree(TWO_PEOPLE, ATTRIBUTES, max_depth=10, min_sheets=100)["leaf"] is True


def test_4e_a_question_is_not_asked_twice_on_one_path():
    sheets = TWO_PEOPLE + [sheet("Hulk", is_male="yes", is_fictional="yes") for _ in range(4)]

    tree = decision_tree.DecisionTree.build_tree(sheets, ATTRIBUTES, max_depth=10, min_sheets=1)
    inner = [child for child in tree["branches"].values() if not child["leaf"]]

    assert len(inner) == 1                       # one branch still mixes two people
    assert inner[0]["question"] != tree["question"]


def test_4e_first_question_can_be_fixed():
    tree = decision_tree.DecisionTree.build_tree(TWO_PEOPLE, ATTRIBUTES, max_depth=10, min_sheets=1, first_question="is_fictional")

    assert tree["question"] == "is_fictional"
    assert tree["branches"]["no"]["question"] == "is_male"   # information gain takes over below the root


def test_4e_tree_depth_never_exceeds_the_limit():
    sheets = [sheet(name, **{"q%d" % i: ("yes" if (n >> i) & 1 else "no") for i in range(6)})
              for n, name in enumerate("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@")]

    tree = decision_tree.DecisionTree.build_tree(sheets, ["q%d" % i for i in range(6)], max_depth=3, min_sheets=1)

    def depth(node):
        return 0 if node["leaf"] else 1 + max(depth(child) for child in node["branches"].values())

    assert depth(tree) == 3


# --- 4f: save_dst / load_dst ---------------------------------------------------------

def test_4f_saved_tree_loads_back_unchanged(tmp_path):
    tree = decision_tree.DecisionTree.build_tree(TWO_PEOPLE, ATTRIBUTES, max_depth=10, min_sheets=1)
    path = tmp_path / "tree.json"

    decision_tree.DecisionTree.save_dst(tree, path)

    assert decision_tree.DecisionTree.load_dst(path) == tree
