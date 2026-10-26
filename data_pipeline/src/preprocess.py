"""Build dataset/characters.csv, the binary dataset used by the game.

Usage:
    python src/preprocess.py

Combines
- raw/roster.csv: hand-curated, reviewed entries;
- raw/roster_auto.csv (optional): entries generated from Wikidata by
  scripts/build_auto_roster.py;
- raw/question_pool.csv: extra questions generated from Wikidata and
  reviewed by hand (see question_pool.py);
- raw/wikidata_snapshot.json: facts and sitelinks (popularity), saved by
  scripts/fetch_wikidata.py;
and writes dataset/characters.csv, where every attribute in questions.QUESTIONS
is stored as "true", "false" or "unknown", followed by a sitelinks column.
Missing or ambiguous facts stay "unknown"; they are never turned into "false".
Roster parsing and validation live in roster.py.
"""

import csv
import json
import sys
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

from data_loader import find_inconsistencies, violated_implications
from question_pool import (
    POOL_PATH, PoolQuestion, check_pool, claim_set, load_pool, pool_value, required_properties,
)
from questions import CORE_QUESTIONS, PARENTS, QUESTIONS
from roster import (  # noqa: F401  (parse_roster_row and load_roster are re-exported for callers)
    AUTO_ROSTER_PATH, COUNTRY_FEATURES, DOMAIN_FEATURES, MEDIA_FEATURES, REGION_FEATURES,
    ROSTER_PATH, SPECIES_TO_HUMAN_ANIMAL, TAG_FEATURES, UNKNOWN,
    RosterEntry, RosterError, check_unique, default_countries, load_roster, parse_roster_row,
)

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_PATH = ROOT / "raw" / "wikidata_snapshot.json"
DATASET_DIR = ROOT.parent / "dataset"  # the finished dataset the game reads
OUTPUT_PATH = DATASET_DIR / "characters.csv"
QUESTIONS_OUTPUT_PATH = DATASET_DIR / "questions.csv"

# (feature, first year, first year after): the character's origin year falls in [first, after).
# One easy question only: players rarely know birth decades, but they know if someone is historical.
YEAR_FEATURES = (
    ("origin_before_1900", None, 1900),
)
YOUNG_DEATH_AGE = 40
VALUE_TEXT = {True: "true", False: "false", None: "unknown"}


# --- attribute derivation --------------------------------------------------

def _died_young(entry):
    if entry.alive == "yes":
        return False
    if entry.alive == "no" and entry.age_at_death is not None:
        return entry.age_at_death < YOUNG_DEATH_AGE
    return None  # fictional, living status unknown, or age unknown


def _identity_attributes(entry):
    is_human, is_animal = SPECIES_TO_HUMAN_ANIMAL[entry.species]
    gender_to_male = {"male": True, "female": False, "unknown": None}
    alive_to_bool = {"yes": True, "no": False, "unknown": None, "na": None}
    return {
        "is_fictional": entry.is_fictional,
        "is_male": gender_to_male[entry.gender],
        "is_human": is_human,
        "is_animal": is_animal,
        "is_alive": alive_to_bool[entry.alive],
        "died_before_age_40": _died_young(entry),
    }


def _time_attributes(entry):
    year = entry.origin_year
    if year is None:
        return {feature: None for feature, _, _ in YEAR_FEATURES}
    return {
        feature: (first is None or year >= first) and year < after
        for feature, first, after in YEAR_FEATURES
    }


def _membership(value_set, key):
    """True if key is the only value, None if one of several (debatable), else False."""
    if key not in value_set:
        return False
    return True if len(value_set) == 1 else None


def _country_flag(entry, names, countries_table):
    if entry.countries:
        if entry.countries <= names:
            return True   # e.g. {China, Taiwan} is wholly within the Chinese-speaking world
        return None if entry.countries & names else False
    # Country unknown: possible only if one of its countries lies in a candidate region.
    possible = not entry.regions or any(countries_table.get(name) in entry.regions for name in names)
    return None if possible else False


def _place_attributes(entry, countries_table):
    if entry.regions:
        regions = {feature: _membership(entry.regions, region) for region, feature in REGION_FEATURES.items()}
    else:
        regions = {feature: None for feature in REGION_FEATURES.values()}
    countries = {feature: _country_flag(entry, names, countries_table) for feature, names in COUNTRY_FEATURES.items()}
    return {**regions, **countries}


def _flag_attributes(entry):
    domains = {feature: key in entry.domains for key, feature in DOMAIN_FEATURES.items()}
    tags = {feature: key in entry.tags for key, feature in TAG_FEATURES.items()}
    if entry.media == UNKNOWN:
        media = {feature: None for feature in MEDIA_FEATURES.values()}
    else:
        media = {feature: key == entry.media for key, feature in MEDIA_FEATURES.items()}
    return {**domains, **tags, **media}


def _apply_overrides(entry, derived):
    absent = [feature for feature, _ in entry.overrides if feature not in derived]
    if absent:
        raise RosterError("%s: override(s) for %s, which are not being derived" % (entry.name, absent))
    stale = [feature for feature, value in entry.overrides if derived[feature] is value]
    if stale:
        raise RosterError("%s: override(s) %s have no effect; remove them" % (entry.name, stale))
    return {**derived, **dict(entry.overrides)}


def _core_attributes(entry, countries_table):
    derived = {
        **_identity_attributes(entry),
        **_time_attributes(entry),
        **_place_attributes(entry, countries_table),
        **_flag_attributes(entry),
    }
    if set(derived) != set(CORE_QUESTIONS):
        raise AssertionError("derived attributes do not match CORE_QUESTIONS: %s"
                             % (set(derived) ^ set(CORE_QUESTIONS)))
    return derived


def _soften_contradictions(attributes):
    """Generated rows only: when Wikidata facts contradict each other (e.g. a fictional
    character with an in-universe Nobel Prize), mark the triggering value unknown.
    Curated rows are not softened: a contradiction there is a review mistake."""
    triggers = {attribute for attribute, _ in violated_implications(attributes)}
    return {feature: (None if feature in triggers else value) for feature, value in attributes.items()}


def derive_attributes(
    entry: RosterEntry,
    pool: Sequence[PoolQuestion] = (),
    claims: FrozenSet[Tuple[str, str]] = frozenset(),
    countries_table: Optional[Dict[str, str]] = None,
) -> Dict[str, Optional[bool]]:
    """Return a new dict of attribute -> True/False/None: core questions, then pool questions."""
    table = countries_table if countries_table is not None else default_countries()
    description = entry.notes if entry.is_generated else None
    pool_values = {
        question.attribute: pool_value(question, entry.name, claims, description, entry.is_fictional)
        for question in pool
    }
    attributes = _apply_overrides(entry, {**_core_attributes(entry, table), **pool_values})
    if entry.is_generated:
        attributes = _soften_contradictions(attributes)
    problems = find_inconsistencies(attributes)
    if problems:
        raise RosterError("%s: contradictory values: %s" % (entry.name, "; ".join(problems)))
    order = list(CORE_QUESTIONS) + [question.attribute for question in pool]
    return {feature: attributes[feature] for feature in order}


def format_row(
    entry: RosterEntry,
    sitelinks: int,
    pool: Sequence[PoolQuestion] = (),
    claims: FrozenSet[Tuple[str, str]] = frozenset(),
) -> Dict[str, str]:
    attributes = derive_attributes(entry, pool, claims)
    values = {feature: VALUE_TEXT[value] for feature, value in attributes.items()}
    review = "generated automatically" if entry.is_generated else "manually reviewed"
    source = "Wikidata %s (CC0); %s" % (entry.wikidata_id, review)
    if entry.popularity_id:
        source += "; popularity from %s" % entry.popularity_id
    return {"name": entry.name, **values, "sitelinks": str(sitelinks), "source": source}


# --- Wikidata snapshot -----------------------------------------------------

def load_snapshot(path=SNAPSHOT_PATH) -> Dict[str, dict]:
    try:
        snapshot = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RosterError("%s not found; run `python scripts/fetch_wikidata.py`" % path) from error
    except ValueError as error:  # invalid JSON
        raise RosterError("%s is not valid JSON (%s); run `python scripts/fetch_wikidata.py`" % (path, error)) from error
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("entities"), dict):
        raise RosterError("%s has no 'entities' table; run `python scripts/fetch_wikidata.py`" % path)
    return snapshot["entities"]


def _entity(entities, qid):
    if qid not in entities:
        raise RosterError("%s is not in the Wikidata snapshot; run `python scripts/fetch_wikidata.py`" % qid)
    return entities[qid]


def sitelinks_for(entry: RosterEntry, entities: Dict[str, dict]) -> int:
    """Popularity: sitelinks of the entry, or of popularity_wikidata_id when given."""
    qid = entry.popularity_id or entry.wikidata_id
    sitelinks = _entity(entities, qid).get("sitelinks")
    if not isinstance(sitelinks, int) or sitelinks < 0:
        raise RosterError("%s has no valid sitelinks in the snapshot; run `python scripts/fetch_wikidata.py`" % qid)
    return sitelinks


# --- building the dataset --------------------------------------------------

def load_all_entries(roster_path=ROSTER_PATH, auto_roster_path=AUTO_ROSTER_PATH) -> Tuple[RosterEntry, ...]:
    """Curated entries first, then generated ones (if the generated file exists)."""
    entries = load_roster(roster_path)
    if auto_roster_path is not None and Path(auto_roster_path).exists():
        entries += load_roster(auto_roster_path, is_generated=True)
    elif auto_roster_path is not None:
        print("Note: %s not found; building the curated roster only" % auto_roster_path, file=sys.stderr)
    check_unique(entries)
    return entries


def check_country_features(countries_table):
    """Every country named by a core question must exist in countries.csv; a renamed
    row would otherwise silently make that question False for everyone."""
    missing = sorted({name for names in COUNTRY_FEATURES.values() for name in names} - set(countries_table))
    if missing:
        raise RosterError("countries.csv has no row for %s, used by COUNTRY_FEATURES" % missing)


def build_dataset(
    roster_path=ROSTER_PATH,
    pool_path=POOL_PATH,
    snapshot_path=SNAPSHOT_PATH,
    auto_roster_path=AUTO_ROSTER_PATH,
) -> List[Dict[str, str]]:
    """Combine rosters, reviewed question pool and Wikidata snapshot into output rows."""
    check_country_features(default_countries())
    entries = load_all_entries(roster_path, auto_roster_path)
    entities = load_snapshot(snapshot_path)
    pool = load_pool(pool_path, [entry.name for entry in entries])
    required = required_properties(pool)
    claims_by_name = {entry.name: claim_set(_entity(entities, entry.wikidata_id), required) for entry in entries}
    check_pool(pool, claims_by_name)
    return [format_row(entry, sitelinks_for(entry, entities), pool, claims_by_name[entry.name]) for entry in entries]


def question_rows() -> List[Dict[str, str]]:
    """One row per attribute: column name, player-facing text, core or pool, and its broader parent question."""
    return [
        {"attribute": attribute, "question": text, "group": "core" if attribute in CORE_QUESTIONS else "pool",
         "parent": PARENTS.get(attribute, "")}
        for attribute, text in QUESTIONS.items()
    ]


def write_questions(path=QUESTIONS_OUTPUT_PATH):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["attribute", "question", "group", "parent"])
        writer.writeheader()
        writer.writerows(question_rows())


def write_dataset(rows: Sequence[Dict[str, str]], path=OUTPUT_PATH):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    try:
        rows = build_dataset()
        DATASET_DIR.mkdir(exist_ok=True)
        write_dataset(rows)
        write_questions()
    except (OSError, ValueError, csv.Error) as error:  # ValueError covers RosterError, PoolError, UnicodeDecodeError
        print("Could not build dataset: %s" % error, file=sys.stderr)
        return 1
    fictional_count = sum(row["is_fictional"] == "true" for row in rows)
    print("Wrote %d rows (%d real, %d fictional) x %d attributes (%d core + %d pool) to %s and %s" % (
        len(rows), len(rows) - fictional_count, fictional_count, len(QUESTIONS), len(CORE_QUESTIONS),
        len(QUESTIONS) - len(CORE_QUESTIONS), OUTPUT_PATH.relative_to(ROOT.parent), QUESTIONS_OUTPUT_PATH.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
