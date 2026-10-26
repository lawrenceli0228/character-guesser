"""Load and validate dataset/characters.csv for the game and the evaluation.

Example:
    from data_loader import load_characters
    from questions import QUESTIONS

    characters = load_characters()
    for character in characters:
        print(character.name, character.attributes["is_fictional"])

Every attribute value is True, False or None. None means the fact is unknown
or ambiguous for that character; it must not be treated as False.
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import List, Mapping, Optional, Sequence, Tuple

from questions import QUESTIONS

DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "dataset" / "characters.csv"
NAME_COLUMN = "name"
SOURCE_COLUMN = "source"
SITELINKS_COLUMN = "sitelinks"
META_COLUMNS = (NAME_COLUMN, SOURCE_COLUMN, SITELINKS_COLUMN)
VALUE_MAP = {"true": True, "false": False, "unknown": None}

# (attribute, value, implied attribute, implied value): if the first attribute
# has that value, a *known* implied attribute must have the implied value.
IMPLICATIONS = (
    ("is_human", True, "is_animal", False),
    ("is_alive", True, "died_before_age_40", False),
    ("known_for_football", True, "known_for_sport", True),
    # Question pool vs core questions
    ("award_nobel_peace", True, "won_nobel_prize", True),
    ("award_nobel_physics", True, "won_nobel_prize", True),
    ("sport_basketball", True, "known_for_sport", True),
    ("sport_tennis", True, "known_for_sport", True),
    ("sport_athletics", True, "known_for_sport", True),
    ("sport_cricket", True, "known_for_sport", True),
    ("position_us_president", True, "has_ruled_a_country", True),
    ("universe_harry_potter", True, "is_fictional", True),
    ("universe_dc", True, "is_fictional", True),
    ("universe_tolkien", True, "is_fictional", True),
    ("franchise_disney", True, "is_fictional", True),
    ("franchise_nintendo", True, "is_fictional", True),
    ("franchise_x_men", True, "is_fictional", True),
    ("franchise_avengers", True, "is_fictional", True),
    ("universe_marvel", True, "is_fictional", True),
    ("universe_star_wars", True, "is_fictional", True),
    ("occupation_superhero", True, "is_fictional", True),
    ("occupation_wizard", True, "has_superpowers_or_magic", True),
)


class DataValidationError(ValueError):
    """Raised when the dataset file is missing, malformed or inconsistent."""


@dataclass(frozen=True)
class Character:
    name: str
    # Read-only mapping of attribute name -> True / False / None (unknown).
    attributes: Mapping[str, Optional[bool]] = field(hash=False)
    source: str = ""
    # Popularity: number of Wikipedia/Wikimedia sitelinks (None if the file has no such column).
    sitelinks: Optional[int] = None


def find_inconsistencies(attributes: Mapping[str, Optional[bool]]) -> List[str]:
    """Describe contradictions between known attribute values (unknowns are skipped)."""
    problems = []
    for attribute, value, implied, implied_value in IMPLICATIONS:
        if attribute not in attributes or implied not in attributes:
            continue
        actual = attributes[implied]
        if attributes[attribute] is value and actual is not None and actual is not implied_value:
            problems.append("%s=%s requires %s=%s" % (attribute, value, implied, implied_value))
    return problems


def violated_implications(attributes: Mapping[str, Optional[bool]]):
    """The (attribute, implied attribute) pairs whose rule is broken by known values."""
    return [
        (attribute, implied)
        for attribute, value, implied, implied_value in IMPLICATIONS
        if attribute in attributes and implied in attributes
        and attributes[attribute] is value
        and attributes[implied] is not None and attributes[implied] is not implied_value
    ]


def parse_value(text, name, column):
    value = text.strip().lower()
    if not value:
        raise DataValidationError("%s: value for %s is empty; use 'unknown' for missing facts" % (name, column))
    if value not in VALUE_MAP:
        raise DataValidationError("%s: value %r for %s must be true, false or unknown" % (name, text, column))
    return VALUE_MAP[value]


def _check_header(fieldnames, questions, path):
    columns = list(fieldnames or [])
    duplicated = sorted({c for c in columns if columns.count(c) > 1})
    if duplicated:
        raise DataValidationError("%s has column(s) appearing more than once: %s" % (path, duplicated))
    if NAME_COLUMN not in columns:
        raise DataValidationError("%s has no '%s' column" % (path, NAME_COLUMN))
    attribute_columns = [c for c in columns if c not in META_COLUMNS]
    missing = [q for q in questions if q not in attribute_columns]
    if missing:
        raise DataValidationError("%s is missing attribute column(s): %s" % (path, missing))
    unexplained = [c for c in attribute_columns if c not in questions]
    if unexplained:
        raise DataValidationError("column(s) %s have no question text in questions.py" % unexplained)


def _parse_sitelinks(row, name):
    if SITELINKS_COLUMN not in row:
        return None
    text = (row.get(SITELINKS_COLUMN) or "").strip()
    if not text.isdigit() or not text.isascii():
        raise DataValidationError("%s: sitelinks must be a non-negative whole number, got %r" % (name, text))
    return int(text)


def _parse_row(row, attributes):
    name = (row.get(NAME_COLUMN) or "").strip()
    if not name:
        raise DataValidationError("a row has an empty name")
    if None in row:
        raise DataValidationError("%s: row has extra cells beyond the header: %s" % (name, row[None]))
    values = {column: parse_value(row.get(column) or "", name, column) for column in attributes}
    problems = find_inconsistencies(values)
    if problems:
        raise DataValidationError("%s: contradictory values: %s" % (name, "; ".join(problems)))
    return Character(
        name=name,
        attributes=MappingProxyType(values),
        source=(row.get(SOURCE_COLUMN) or "").strip(),
        sitelinks=_parse_sitelinks(row, name),
    )


def _check_unique_names(characters):
    seen = set()
    for character in characters:
        key = character.name.casefold()
        if key in seen:
            raise DataValidationError("Duplicate name: %s" % character.name)
        seen.add(key)


def load_characters(path=DEFAULT_DATA_PATH, questions=QUESTIONS) -> Tuple[Character, ...]:
    """Read the dataset and return an immutable tuple of validated characters."""
    path = Path(path)
    try:
        # utf-8-sig also accepts files saved by Excel with a byte-order mark.
        with open(path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            _check_header(reader.fieldnames, questions, path)
            characters = tuple(_parse_row(row, list(questions)) for row in reader)
    except FileNotFoundError as error:
        raise DataValidationError("Data file not found: %s" % path) from error
    if not characters:
        raise DataValidationError("%s contains no characters" % path)
    _check_unique_names(characters)
    return characters


def to_feature_matrix(
    characters: Sequence[Character],
    attributes: Optional[Sequence[str]] = None,
    unknown_value: float = float("nan"),
) -> Tuple[List[str], List[str], List[List[float]]]:
    """Return (names, attribute names, rows) with 1.0 for True and 0.0 for False.

    Unknown values become `unknown_value`, which must differ from 0.0 and 1.0
    so unknowns stay distinguishable. scikit-learn 0.24's DecisionTreeClassifier
    rejects NaN, so pass e.g. unknown_value=0.5 there; note that a fitted tree
    then sends every unknown down one fixed branch of each split.
    """
    if not characters:
        raise ValueError("no characters to encode")
    if unknown_value in (0.0, 1.0):
        raise ValueError("unknown_value must not be 0.0 or 1.0, or unknowns would look like False/True")
    chosen = list(attributes) if attributes is not None else list(characters[0].attributes)
    encode = {True: 1.0, False: 0.0, None: unknown_value}
    names = [character.name for character in characters]
    rows = [[encode[character.attributes[a]] for a in chosen] for character in characters]
    return names, chosen, rows
