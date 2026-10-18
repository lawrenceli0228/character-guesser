from data_loader import load_characters
from questions import CORE_QUESTIONS, FIRST_QUESTION


def test_first_question_is_fictional():
    assert FIRST_QUESTION == "is_fictional"
    assert FIRST_QUESTION in CORE_QUESTIONS


def test_first_question_is_known_for_every_character_and_splits_roster():
    values = [c.attributes[FIRST_QUESTION] for c in load_characters()]

    assert None not in values
    assert True in values and False in values
