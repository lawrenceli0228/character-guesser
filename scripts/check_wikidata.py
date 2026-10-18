"""Cross-check hand-entered roster facts against the local Wikidata snapshot.

Usage:
    python scripts/fetch_wikidata.py   # download/refresh the snapshot first
    python scripts/check_wikidata.py

Compares name/label, gender, birth year, living status, age at death and
Nobel Prize in data/raw/roster.csv with data/raw/wikidata_snapshot.json and
prints every disagreement for manual review. Nothing is changed
automatically. Works offline.
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROSTER_PATH = ROOT / "data" / "raw" / "roster.csv"
SNAPSHOT_PATH = ROOT / "data" / "raw" / "wikidata_snapshot.json"

BIRTH_YEAR_TOLERANCE = 2  # BCE dates and uncertain dates differ by a year or two

ENTITY_PREFIX = "http://www.wikidata.org/entity/"
# Non-human characters use "male/female organism" (Q44148/Q43445).
GENDER_IDS = {
    "male": {ENTITY_PREFIX + "Q6581097", ENTITY_PREFIX + "Q44148"},
    "female": {ENTITY_PREFIX + "Q6581072", ENTITY_PREFIX + "Q43445"},
}


def read_roster(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_snapshot():
    if not SNAPSHOT_PATH.exists():
        raise SystemExit("No snapshot found; run `python scripts/fetch_wikidata.py` first.")
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def year_of(timestamp):
    """Historical year (no year 0; negative = BCE) from an xsd:dateTime string.

    The query service returns XSD years, where 0 is 1 BCE and -99 is 100 BCE.
    """
    sign = -1 if timestamp.startswith("-") else 1
    xsd_year = sign * int(timestamp.lstrip("-+").split("-", 1)[0])
    return xsd_year if xsd_year > 0 else xsd_year - 1


def exact_age(birth, death):
    """Age in whole years between two xsd:dateTime strings (CE dates only)."""
    born = [int(part) for part in birth[:10].split("-")]
    died = [int(part) for part in death[:10].split("-")]
    return died[0] - born[0] - ((died[1], died[2]) < (born[1], born[2]))


def check_age_at_death(row, entity):
    if not row["age_at_death"] or not entity["births"] or not entity["deaths"]:
        return []
    roster_age = int(row["age_at_death"])
    pairs = [(b, d) for b in entity["births"] for d in entity["deaths"]]
    if any(b.startswith("-") or d.startswith("-") for b, d in pairs):
        ages = sorted({year_of(d) - year_of(b) for b, d in pairs})  # BCE: year precision only
    else:
        ages = sorted({exact_age(b, d) for b, d in pairs})
    if roster_age not in ages and all(abs(age - roster_age) > 1 for age in ages):
        return ["age at death: roster=%d, Wikidata=%s" % (roster_age, ages)]
    if roster_age not in ages:
        return ["age at death (within 1 year, check calendar/precision): roster=%d, Wikidata=%s" % (roster_age, ages)]
    return []


def check_gender(row, entity):
    # Blank nodes (".well-known/genid/") are Wikidata's "unknown value".
    known = [g for g in entity["genders"] if g.startswith(ENTITY_PREFIX)]
    expected = GENDER_IDS.get(row["gender"])
    if expected is None:
        return ["gender is 'unknown' in roster; Wikidata has %s" % known] if known else []
    if not expected & set(known):
        return ["gender: roster=%s, Wikidata=%s" % (row["gender"], entity["genders"] or "missing")]
    return []


def check_real_person(row, entity):
    problems = []
    roster_year = int(row["origin_year"])
    years = [year_of(b) for b in entity["births"]]
    if not years:
        problems.append("birth year: Wikidata has none")
    elif all(abs(y - roster_year) > BIRTH_YEAR_TOLERANCE for y in years):
        problems.append("birth year: roster=%d, Wikidata=%s" % (roster_year, years))
    is_dead_in_wikidata = bool(entity["deaths"])
    if (row["alive"] == "yes") == is_dead_in_wikidata:
        problems.append("alive: roster=%s, Wikidata deaths=%s" % (row["alive"], entity["deaths"] or "none"))
    has_nobel_tag = "nobel" in row["tags"].split(";")
    if has_nobel_tag != bool(entity["nobel_awards"]):
        problems.append("nobel: roster tag=%s, Wikidata=%s" % (has_nobel_tag, entity["nobel_awards"] or "none"))
    return problems + check_age_at_death(row, entity)


def check_label(row, entity):
    """A wrong ID can still match gender and birth year, so compare names too."""
    label = entity["label"]
    if not label:
        return ["Wikidata has no English label; confirm from description: %r" % entity["description"]]
    if label.casefold() != row["name"].casefold():
        return ["name differs from Wikidata label %r (fine if it is an alias)" % label]
    return []


def check_row(row, entity):
    if entity is None:
        return ["Wikidata ID %s not found" % row["wikidata_id"]]
    problems = check_label(row, entity) + check_gender(row, entity)
    if row["kind"] == "real":
        problems += check_real_person(row, entity)
    return problems


def main():
    rows = read_roster(ROSTER_PATH)
    snapshot = load_snapshot()
    entities = snapshot["entities"]
    print("Wikidata snapshot retrieved %s; %d roster rows\n" % (snapshot["retrieved"], len(rows)))
    mismatch_count = 0
    for row in rows:
        entity = entities.get(row["wikidata_id"])
        problems = check_row(row, entity)
        label = entity["label"] if entity else "?"
        if problems:
            mismatch_count += 1
            print("%s (%s, Wikidata label '%s')" % (row["name"], row["wikidata_id"], label))
            for problem in problems:
                print("    - " + problem)
    print("\n%d of %d rows need review." % (mismatch_count, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
