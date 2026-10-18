import csv
import math

import pytest

import preprocess
from data_loader import (
    DEFAULT_DATA_PATH,
    DataValidationError,
    find_inconsistencies,
    load_characters,
    to_feature_matrix,
)
from questions import QUESTIONS

SMALL_QUESTIONS = {"is_fictional": "Fictional?", "is_male": "Male?"}


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return path


@pytest.fixture
def small_csv(tmp_path):
    return write_csv(tmp_path / "small.csv", ["name", "is_fictional", "is_male", "source"], [
        ["Ada Lovelace", "false", "false", "Wikidata Q7259"],
        ["Pikachu", "true", "unknown", "Wikidata Q9351"],
    ])


def test_loads_values_as_true_false_or_none(small_csv):
    characters = load_characters(small_csv, questions=SMALL_QUESTIONS)

    assert [c.name for c in characters] == ["Ada Lovelace", "Pikachu"]
    assert characters[0].attributes == {"is_fictional": False, "is_male": False}
    assert characters[1].attributes["is_fictional"] is True
    assert characters[1].attributes["is_male"] is None
    assert characters[1].source == "Wikidata Q9351"


def test_values_are_case_and_whitespace_insensitive(tmp_path):
    path = write_csv(tmp_path / "d.csv", ["name", "is_fictional", "is_male", "source"],
                     [["Ada", " TRUE ", "Unknown", "s"]])

    character = load_characters(path, questions=SMALL_QUESTIONS)[0]

    assert character.attributes == {"is_fictional": True, "is_male": None}


def test_attributes_cannot_be_modified(small_csv):
    character = load_characters(small_csv, questions=SMALL_QUESTIONS)[0]

    with pytest.raises(TypeError):
        character.attributes["is_male"] = True


@pytest.mark.parametrize("bad_value, expected_message", [
    ("", "empty"),
    ("maybe", "maybe"),
    ("yes", "yes"),
])
def test_invalid_or_missing_values_are_rejected(tmp_path, bad_value, expected_message):
    path = write_csv(tmp_path / "d.csv", ["name", "is_fictional", "is_male", "source"],
                     [["Ada", "false", bad_value, "s"]])

    with pytest.raises(DataValidationError) as error:
        load_characters(path, questions=SMALL_QUESTIONS)

    assert "Ada" in str(error.value)
    assert "is_male" in str(error.value)
    assert expected_message in str(error.value)


def test_missing_attribute_column_is_rejected(tmp_path):
    path = write_csv(tmp_path / "d.csv", ["name", "is_fictional", "source"], [["Ada", "false", "s"]])

    with pytest.raises(DataValidationError, match="is_male"):
        load_characters(path, questions=SMALL_QUESTIONS)


def test_missing_name_column_is_rejected(tmp_path):
    path = write_csv(tmp_path / "d.csv", ["is_fictional", "is_male", "source"], [["false", "false", "s"]])

    with pytest.raises(DataValidationError, match="name"):
        load_characters(path, questions=SMALL_QUESTIONS)


def test_column_without_question_text_is_rejected(tmp_path):
    path = write_csv(tmp_path / "d.csv", ["name", "is_fictional", "is_male", "is_tall", "source"],
                     [["Ada", "false", "false", "true", "s"]])

    with pytest.raises(DataValidationError, match="is_tall"):
        load_characters(path, questions=SMALL_QUESTIONS)


def test_duplicate_names_are_rejected_case_insensitively(tmp_path):
    path = write_csv(tmp_path / "d.csv", ["name", "is_fictional", "is_male", "source"],
                     [["Ada", "false", "false", "s"], ["ada", "false", "false", "s"]])

    with pytest.raises(DataValidationError, match="Duplicate"):
        load_characters(path, questions=SMALL_QUESTIONS)


def test_empty_name_is_rejected(tmp_path):
    path = write_csv(tmp_path / "d.csv", ["name", "is_fictional", "is_male", "source"],
                     [["  ", "false", "false", "s"]])

    with pytest.raises(DataValidationError, match="empty name"):
        load_characters(path, questions=SMALL_QUESTIONS)


def test_empty_dataset_is_rejected(tmp_path):
    path = write_csv(tmp_path / "d.csv", ["name", "is_fictional", "is_male", "source"], [])

    with pytest.raises(DataValidationError, match="no characters"):
        load_characters(path, questions=SMALL_QUESTIONS)


def test_missing_file_is_reported_clearly(tmp_path):
    with pytest.raises(DataValidationError, match="not found"):
        load_characters(tmp_path / "missing.csv", questions=SMALL_QUESTIONS)


# --- feature matrix for scikit-learn ----------------------------------------

def test_feature_matrix_encodes_true_false_and_nan_by_default(small_csv):
    characters = load_characters(small_csv, questions=SMALL_QUESTIONS)

    names, attributes, rows = to_feature_matrix(characters)

    assert names == ["Ada Lovelace", "Pikachu"]
    assert attributes == ["is_fictional", "is_male"]
    assert rows[0] == [0.0, 0.0]
    assert rows[1][0] == 1.0
    assert math.isnan(rows[1][1])


def test_feature_matrix_accepts_custom_unknown_value_and_attribute_subset(small_csv):
    characters = load_characters(small_csv, questions=SMALL_QUESTIONS)

    _, attributes, rows = to_feature_matrix(characters, attributes=["is_male"], unknown_value=-1.0)

    assert attributes == ["is_male"]
    assert rows == [[0.0], [-1.0]]


def test_feature_matrix_rejects_unknown_attribute(small_csv):
    characters = load_characters(small_csv, questions=SMALL_QUESTIONS)

    with pytest.raises(KeyError, match="is_tall"):
        to_feature_matrix(characters, attributes=["is_tall"])


# --- the real project dataset ---------------------------------------------

def test_project_dataset_loads_with_every_question_and_popularity():
    characters = load_characters(DEFAULT_DATA_PATH)

    assert len(characters) >= 50
    assert all(set(c.attributes) == set(QUESTIONS) for c in characters)
    assert all(c.sitelinks is not None and c.sitelinks > 0 for c in characters)


# --- popularity (sitelinks) ---------------------------------------------------

def test_sitelinks_column_is_parsed_as_integer(tmp_path):
    path = write_csv(tmp_path / "d.csv", ["name", "is_fictional", "is_male", "sitelinks", "source"],
                     [["Ada", "false", "false", "120", "s"]])

    assert load_characters(path, questions=SMALL_QUESTIONS)[0].sitelinks == 120


def test_sitelinks_are_none_when_column_absent(small_csv):
    assert load_characters(small_csv, questions=SMALL_QUESTIONS)[0].sitelinks is None


@pytest.mark.parametrize("bad", ["", "-3", "many", "1.5"])
def test_invalid_sitelinks_are_rejected(tmp_path, bad):
    path = write_csv(tmp_path / "d.csv", ["name", "is_fictional", "is_male", "sitelinks", "source"],
                     [["Ada", "false", "false", bad, "s"]])

    with pytest.raises(DataValidationError, match="sitelinks"):
        load_characters(path, questions=SMALL_QUESTIONS)


def test_project_dataset_is_up_to_date_with_roster(tmp_path):
    regenerated = tmp_path / "characters.csv"

    preprocess.write_dataset(preprocess.build_dataset(), regenerated)

    expected = list(csv.DictReader(open(regenerated, encoding="utf-8")))
    actual = list(csv.DictReader(open(DEFAULT_DATA_PATH, encoding="utf-8")))
    changed = [
        "%s.%s: %s -> %s" % (new.get("name"), column, old.get(column), new.get(column))
        for old, new in zip(actual, expected)
        for column in new
        if old.get(column) != new.get(column)
    ]
    assert len(actual) == len(expected) and not changed, \
        "dataset/characters.csv is stale (run `python data_pipeline/src/preprocess.py`); first changes: %s" % changed[:10]


# --- review follow-ups ------------------------------------------------------

def test_duplicate_header_columns_are_rejected(tmp_path):
    path = write_csv(tmp_path / "d.csv", ["name", "is_fictional", "is_male", "is_male", "source"],
                     [["Ada", "false", "false", "true", "s"]])

    with pytest.raises(DataValidationError, match="more than once"):
        load_characters(path, questions=SMALL_QUESTIONS)


def test_rows_with_extra_cells_are_rejected(tmp_path):
    path = write_csv(tmp_path / "d.csv", ["name", "is_fictional", "is_male", "source"],
                     [["Ada", "false", "false", "s", "shifted"]])

    with pytest.raises(DataValidationError, match="extra"):
        load_characters(path, questions=SMALL_QUESTIONS)


def test_contradictory_attributes_are_rejected(tmp_path):
    questions = {"is_human": "Human?", "is_animal": "Animal?"}
    path = write_csv(tmp_path / "d.csv", ["name", "is_human", "is_animal", "source"],
                     [["Odd", "true", "true", "s"]])

    with pytest.raises(DataValidationError, match="is_animal"):
        load_characters(path, questions=questions)


def test_utf8_bom_is_accepted(tmp_path, small_csv):
    small_csv.write_bytes(b"\xef\xbb\xbf" + small_csv.read_bytes())

    assert len(load_characters(small_csv, questions=SMALL_QUESTIONS)) == 2


def test_find_inconsistencies_ignores_unknown_values():
    assert find_inconsistencies({"origin_before_1500": True, "origin_before_1800": None}) == []
    assert find_inconsistencies({"origin_before_1500": True, "origin_before_1800": False}) != []


@pytest.mark.parametrize("unknown_value", [0.0, 1.0])
def test_feature_matrix_rejects_unknown_value_that_hides_unknowns(small_csv, unknown_value):
    characters = load_characters(small_csv, questions=SMALL_QUESTIONS)

    with pytest.raises(ValueError, match="unknown_value"):
        to_feature_matrix(characters, unknown_value=unknown_value)


def test_feature_matrix_rejects_empty_input():
    with pytest.raises(ValueError, match="no characters"):
        to_feature_matrix([])



def test_exported_questions_match_question_definitions():
    exported = list(csv.DictReader(open(preprocess.QUESTIONS_OUTPUT_PATH, encoding="utf-8")))

    assert exported == preprocess.question_rows()
    assert [row["attribute"] for row in exported] == list(QUESTIONS)
