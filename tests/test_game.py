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


@pytest.mark.parametrize("text", ["u", "unknown", "?", "？", "not sure", "dont know", "don't know", "maybe"])
def test_5a_not_sure(text):
    assert game.Game.parse_user_input(text) == "unknown"


@pytest.mark.parametrize("text", ["", "yess", "123"])
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



# --- 5j: linked questions ------------------------------------------------------------
# PARENTS: a narrower question -> the broader question it belongs to.

PARENTS = {"from_uk": "from_europe", "from_london": "from_uk", "is_wizard": "has_magic"}


def test_5j_child_of_a_no_is_ruled_out():
    answers = {"from_europe": "no"}

    assert game.Game.ruled_out("from_uk", answers, PARENTS)
    assert game.Game.ruled_out("from_london", answers, PARENTS)      # grandparent No counts too


def test_5j_parent_of_a_yes_is_ruled_out():
    # UK Yes already means Europe Yes; London Yes means UK and Europe Yes
    assert game.Game.ruled_out("from_europe", {"from_uk": "yes"}, PARENTS)
    assert game.Game.ruled_out("from_europe", {"from_london": "yes"}, PARENTS)
    assert not game.Game.ruled_out("from_europe", {"from_uk": "no"}, PARENTS)


def test_5j_child_of_a_yes_or_unanswered_parent_is_not_ruled_out():
    assert not game.Game.ruled_out("from_uk", {"from_europe": "yes"}, PARENTS)
    assert not game.Game.ruled_out("from_uk", {"from_europe": "unknown"}, PARENTS)
    assert not game.Game.ruled_out("from_uk", {}, PARENTS)


def test_5j_focus_question_skips_children_of_a_no():
    # from_uk would split A and B, but Europe was already answered No
    a = make_character("A", from_europe=False, from_uk=True, is_male=True)
    b = make_character("B", from_europe=False, from_uk=False, is_male=False)

    question = game.Game.focus_question([a, b], {"A": 0.5, "B": 0.5}, [("from_europe", "no")], 20, PARENTS)

    assert question == "is_male"


def test_5j_focus_question_follows_up_a_yes_when_nearly_as_good():
    # is_male and is_wizard split A and B equally well; has_magic was just answered Yes
    a = make_character("A", has_magic=True, is_wizard=True, is_male=True)
    b = make_character("B", has_magic=True, is_wizard=False, is_male=False)

    question = game.Game.focus_question([a, b], {"A": 0.5, "B": 0.5}, [("has_magic", "yes")], 20, PARENTS)

    assert question == "is_wizard"


def test_5j_focus_question_does_not_follow_up_a_much_worse_question():
    # is_wizard is the same for A and B, so following up has_magic would waste a question
    a = make_character("A", has_magic=True, is_wizard=True, is_male=True)
    b = make_character("B", has_magic=True, is_wizard=True, is_male=False)

    question = game.Game.focus_question([a, b], {"A": 0.5, "B": 0.5}, [("has_magic", "yes")], 20, PARENTS)

    assert question == "is_male"


def test_5j_choose_question_skips_a_tree_question_that_is_ruled_out():
    a = make_character("A", from_europe=False, from_uk=True, is_male=True)
    b = make_character("B", from_europe=False, from_uk=False, is_male=False)
    node = {"leaf": False, "counts": {"A": 3000, "B": 3000}, "question": "from_uk", "branches": {}}

    question = game.Game.choose_question(node, [a, b], {"A": 0.5, "B": 0.5}, [("from_europe", "no")], PARENTS)

    assert question == "is_male"


def test_5j_no_follow_up_to_a_sibling_of_a_yes():
    # sport Yes, then basketball Yes: asking about football next would be wasted
    # (plays_football splits A and B exactly as well as is_male, so only the sibling rule stops it)
    parents = {"plays_basketball": "sport", "plays_football": "sport"}
    a = make_character("A", is_male=True, sport=True, plays_basketball=True, plays_football=True)
    b = make_character("B", is_male=False, sport=True, plays_basketball=True, plays_football=False)
    asked = [("sport", "yes"), ("plays_basketball", "yes")]

    assert game.Game.focus_question([a, b], {"A": 0.5, "B": 0.5}, asked, 20, parents) == "is_male"


# --- 5k: early guess --------------------------------------------------------------------
# Stop asking once the leader is many times more likely than the runner-up (like akinator.dev).

def test_5k_confident_once_the_leader_is_far_ahead_of_the_runner_up():
    assert game.Game.confident([("Kobe", 0.92), ("LeBron", 0.04)])     # 23x


def test_5k_not_confident_while_the_runner_up_is_close():
    assert not game.Game.confident([("Snape", 0.6), ("Dumbledore", 0.3)])


def test_5k_confident_with_a_single_candidate():
    assert game.Game.confident([("Snape", 1.0)])


# --- 5l: after a wrong guess ----------------------------------------------------------
# The player says who it was; the game shows which answers disagreed with its data.

def test_5l_find_character_ignores_case_and_spaces():
    assert game.Game.find_character(CHARACTERS, "  ada ") is ADA
    assert game.Game.find_character(CHARACTERS, "Grace Hopper") is None


def test_5l_disagreements_list_answers_that_differ_from_the_data():
    asked = [("is_male", "yes"), ("origin_before_1900", "yes")]

    assert game.Game.disagreements(ADA, asked) == [("is_male", "yes", "no")]


def test_5l_not_sure_answers_are_not_disagreements():
    assert game.Game.disagreements(ADA, [("is_male", "unknown")]) == []


# --- 5m: no wasted questions ------------------------------------------------------------

def test_5m_fictional_characters_get_one_year_question_at_most():
    asked_one = {"is_fictional": "yes", "origin_before_1950": "unknown"}

    assert game.Game.over_limit("origin_1960_or_later", asked_one)
    assert not game.Game.over_limit("origin_1960_or_later", {"is_fictional": "yes"})
    assert not game.Game.over_limit("is_male", asked_one)


def test_5m_real_people_get_two_year_questions_at_most():
    assert not game.Game.over_limit("origin_1960_or_later", {"is_fictional": "no", "origin_before_1950": "no"})
    assert game.Game.over_limit("origin_1970_or_later",
                                {"is_fictional": "no", "origin_before_1950": "no", "origin_1960_or_later": "yes"})


def test_5m_focus_question_respects_the_year_limit():
    # the year question would split A and B best, but one was already asked
    a = make_character("A", is_fictional=True, origin_before_1950=True, origin_1960_or_later=False, is_male=True)
    b = make_character("B", is_fictional=True, origin_before_1950=True, origin_1960_or_later=True, is_male=False)
    asked = [("is_fictional", "yes"), ("origin_before_1950", "yes")]

    assert game.Game.focus_question([a, b], {"A": 0.5, "B": 0.5}, asked, 20) == "is_male"


def test_5l_find_character_with_a_middle_name_or_surname_only():
    mark = {"name": "Mark Zuckerberg", "attributes": {}, "sitelinks": 100}
    donald = {"name": "Donald Trump", "attributes": {}, "sitelinks": 300}
    melania = {"name": "Melania Trump", "attributes": {}, "sitelinks": 90}
    people = [mark, donald, melania]

    assert game.Game.find_character(people, "Mark Elliot Zuckerberg") is mark
    assert game.Game.find_character(people, "zuckerberg") is mark
    assert game.Game.find_character(people, "trump") is donald          # the better-known Trump


def test_5l_find_character_forgives_a_typo():
    einstein = {"name": "Albert Einstein", "attributes": {}, "sitelinks": 300}

    assert game.Game.find_character([einstein], "albert einstien") is einstein


# --- 5n: answering the final "Is it X?" -------------------------------------------------
# Only yes or no counts; typing a name means "no, it was this person".

def test_5n_yes_and_no_are_read_as_usual():
    assert game.Game.read_confirm("y") == ("yes", None)
    assert game.Game.read_confirm("No") == ("no", None)


def test_5n_not_sure_is_asked_again():
    assert game.Game.read_confirm("?") == ("again", None)
    assert game.Game.read_confirm("  ") == ("again", None)


def test_5n_a_typed_name_means_no_and_who_it_was():
    assert game.Game.read_confirm("Donald Trump") == ("no", "Donald Trump")
