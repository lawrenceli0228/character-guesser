"""Tests for src/dataset.py, grouped by step.

`import dataset` (instead of importing each function) lets every test run on
its own: until a function is written, only its own tests fail.
"""

import csv
from pathlib import Path

import pytest

import dataset

DATASET_DIR = Path(__file__).resolve().parent.parent / "dataset"
CHARACTERS_CSV = DATASET_DIR / "characters.csv"
QUESTIONS_CSV = DATASET_DIR / "questions.csv"


def write_csv(path, header, rows):
    """Small helper: write a tiny CSV file for a test."""
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return path


# --- 1a: parse_value -----------------------------------------------------------

def test_1a_parse_value_turns_text_into_true_false_or_none():
    assert dataset.Dataset.parse_value("true") is True
    assert dataset.Dataset.parse_value("false") is False
    assert dataset.Dataset.parse_value("unknown") is None


def test_1a_parse_value_rejects_anything_else():
    with pytest.raises(ValueError):
        dataset.Dataset.parse_value("maybe")


# --- 1b: load_questions ---------------------------------------------------------

def test_1b_load_questions_returns_attribute_to_question(tmp_path):
    path = write_csv(tmp_path / "questions.csv", ["attribute", "question", "group"], [
        ["is_fictional", "Is this a fictional character?", "core"],
        ["is_male", "Is this person male?", "core"],
    ])

    questions = dataset.Dataset.load_questions(path)

    assert questions == {"is_fictional": "Is this a fictional character?", "is_male": "Is this person male?"}


def test_1b_load_questions_keeps_file_order(tmp_path):
    path = write_csv(tmp_path / "questions.csv", ["attribute", "question", "group"], [
        ["b_question", "B?", "core"],
        ["a_question", "A?", "pool"],
    ])

    assert list(dataset.Dataset.load_questions(path)) == ["b_question", "a_question"]


# --- 1c: load_characters --------------------------------------------------------

SMALL_HEADER = ["name", "is_fictional", "is_male", "sitelinks", "source"]


def test_1c_load_characters_builds_one_dictionary_per_row(tmp_path):
    path = write_csv(tmp_path / "characters.csv", SMALL_HEADER, [
        ["Ada Lovelace", "false", "false", "120", "Wikidata Q7259"],
        ["Pikachu", "true", "unknown", "84", "Wikidata Q9351"],
    ])

    characters = dataset.Dataset.load_characters(path)

    assert characters == [
        {"name": "Ada Lovelace", "attributes": {"is_fictional": False, "is_male": False}, "sitelinks": 120},
        {"name": "Pikachu", "attributes": {"is_fictional": True, "is_male": None}, "sitelinks": 84},
    ]


def test_1c_sitelinks_is_a_number_not_text(tmp_path):
    path = write_csv(tmp_path / "characters.csv", SMALL_HEADER, [["Ada Lovelace", "false", "false", "120", "s"]])

    assert dataset.Dataset.load_characters(path)[0]["sitelinks"] == 120


def test_1c_source_column_is_not_an_attribute(tmp_path):
    path = write_csv(tmp_path / "characters.csv", SMALL_HEADER, [["Ada Lovelace", "false", "false", "120", "s"]])

    assert "source" not in dataset.Dataset.load_characters(path)[0]["attributes"]


def test_1c_bad_value_is_reported(tmp_path):
    path = write_csv(tmp_path / "characters.csv", SMALL_HEADER, [["Ada Lovelace", "maybe", "false", "120", "s"]])

    with pytest.raises(ValueError):
        dataset.Dataset.load_characters(path)


# --- 1d: the real dataset ---------------------------------------------------------

def test_1d_real_dataset_has_500_characters():
    characters = dataset.Dataset.load_characters(CHARACTERS_CSV)

    assert len(characters) == 500
    einstein = characters[0]
    assert einstein["name"] == "Albert Einstein"
    assert einstein["attributes"]["is_fictional"] is False
    assert einstein["attributes"]["is_male"] is True
    assert einstein["sitelinks"] == 322


def test_1d_unknown_values_become_none_not_false():
    characters = {c["name"]: c for c in dataset.Dataset.load_characters(CHARACTERS_CSV)}

    assert characters["Harry Potter"]["attributes"]["is_alive"] is None


def test_1d_every_attribute_has_a_question():
    characters = dataset.Dataset.load_characters(CHARACTERS_CSV)
    questions = dataset.Dataset.load_questions(QUESTIONS_CSV)

    assert len(questions) == 175
    assert list(questions) == list(characters[0]["attributes"])


def test_1d_fictional_characters_have_a_known_origin_year():
    # first-appearance years were filled in by hand where Wikidata had none (Wolverine: 1974)
    characters = {c["name"]: c for c in dataset.Dataset.load_characters(CHARACTERS_CSV)}

    assert characters["Wolverine"]["attributes"]["origin_before_1900"] is False
    unknown = [name for name, c in characters.items() if c["attributes"]["origin_before_1900"] is None]
    assert unknown == ["Morgoth"]


def test_1d_new_questions_tell_common_look_alikes_apart():
    # event, work and look questions added instead of birth decades
    characters = {c["name"]: c["attributes"] for c in dataset.Dataset.load_characters(CHARACTERS_CSV)}

    for a, b in [("Donald Trump", "George W. Bush"), ("Richard Nixon", "Gerald Ford"), ("Bugs Bunny", "Daffy Duck"),
                 ("Tarzan", "Zorro"), ("Hulk", "Spider-Man"), ("Dwight D. Eisenhower", "Ulysses S. Grant"),
                 ("Cristiano Ronaldo", "José Mourinho"), ("Homer Simpson", "Peter Griffin"), ("The Joker", "Two-Face"),
                 ("Jeff Bezos", "Mark Zuckerberg"), ("Selena Gomez", "Jennifer Lopez"), ("Brad Pitt", "Robert De Niro")]:
        assert any(characters[a][q] is not None and characters[b][q] is not None and characters[a][q] != characters[b][q]
                   for q in characters[a]), (a, b)


def test_1d_main_harry_potter_characters_can_be_told_apart():
    # before the role/age/teacher questions, Harry, Ron, Dumbledore and Sirius had identical answers
    characters = {c["name"]: c for c in dataset.Dataset.load_characters(CHARACTERS_CSV)}
    names = ["Harry Potter", "Ron Weasley", "Albus Dumbledore", "Severus Snape", "Sirius Black"]

    answer_sets = {tuple(characters[name]["attributes"].values()) for name in names}

    assert len(answer_sets) == len(names)


# --- parent questions (linked questions) ------------------------------------------

def test_load_parents_reads_only_rows_with_a_parent(tmp_path):
    path = write_csv(tmp_path / "questions.csv", ["attribute", "question", "group", "parent"], [
        ["from_europe", "Europe?", "core", ""],
        ["from_uk", "UK?", "core", "from_europe"],
    ])

    assert dataset.Dataset.load_parents(path) == {"from_uk": "from_europe"}


def test_real_dataset_links_countries_to_regions():
    parents = dataset.Dataset.load_parents(QUESTIONS_CSV)

    assert parents["from_uk"] == "from_europe"
    assert parents["universe_harry_potter"] == "first_appeared_in_book"
