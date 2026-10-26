from data_loader import load_characters
from questions import CORE_QUESTIONS, FIRST_QUESTION


def test_first_question_is_fictional():
    assert FIRST_QUESTION == "is_fictional"
    assert FIRST_QUESTION in CORE_QUESTIONS


def test_first_question_is_known_for_every_character_and_splits_roster():
    values = [c.attributes[FIRST_QUESTION] for c in load_characters()]

    assert None not in values
    assert True in values and False in values


def test_parent_links_use_existing_questions():
    from questions import PARENTS, QUESTIONS

    assert all(child in QUESTIONS and parent in QUESTIONS for child, parent in PARENTS.items())


def test_a_yes_to_a_child_question_is_never_a_no_to_its_parent():
    # the game skips a child once its parent is answered No, so the data must agree
    from questions import PARENTS

    broken = [(c.name, child, parent) for c in load_characters() for child, parent in PARENTS.items()
              if c.attributes[child] is True and c.attributes[parent] is False]

    assert broken == []
