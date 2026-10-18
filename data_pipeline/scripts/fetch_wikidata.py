"""Download the Wikidata facts used by the project into a local snapshot.

Usage:
    python scripts/fetch_wikidata.py

Entities: every ID in raw/roster.csv (plus popularity_wikidata_id), and
the top-ranked eligible candidates in raw/candidates.csv (written by
scripts/select_candidates.py), enough to fill the targets in dataset_config.py.

For each entity raw/wikidata_snapshot.json stores:
- label, description, gender (P21), birth (P569) and death (P570) dates and
  Nobel Prize awards (P166), used by check_wikidata.py and build_auto_roster.py;
- the number of Wikipedia/Wikimedia sitelinks, used as a popularity score;
- the item values of the properties in CLAIM_PROPERTIES.
For works that fictional characters appear in (P4584, P1441) it also stores
their type (P31), publication date (P577), inception (P571), country of
origin (P495) and the series they belong to (P179, fetched too), so a
character's medium, year and country can be derived. Entities also get their
inception date (P571), the creation year of a fictional character.

Everything else in the project reads the snapshot, so results are
reproducible offline. Wikidata content is CC0 (public domain).
"""

import csv
import json
import math
import sys
import time
from datetime import date
from pathlib import Path

from dataset_config import FETCH_BUFFER, TARGET_FICTIONAL, TARGET_REAL
from wikidata_http import WDQS_ENDPOINT, chunks, entity_id, sparql, value

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
ROSTER_PATH = RAW / "roster.csv"
CANDIDATES_PATH = RAW / "candidates.csv"
SNAPSHOT_PATH = RAW / "wikidata_snapshot.json"
BATCH_SIZE = 100
PAUSE_SECONDS = 1

# Properties stored per entity. Sensitive properties (religion, ethnicity,
# sexual orientation, ...) are deliberately excluded.
CLAIM_PROPERTIES = {
    "P106": "occupation",
    "P166": "award received",
    "P39": "position held",
    "P641": "sport",
    "P1303": "instrument",
    "P69": "educated at",
    "P1080": "from narrative universe",
    "P170": "creator",
    "P8345": "media franchise",
    "P54": "member of sports team",
    "P27": "country of citizenship",
    "P31": "instance of",
    "P495": "country of origin",
    "P1441": "present in work",
    "P4584": "first appearance",
}
WORK_LINK_PROPERTIES = ("P4584", "P1441")

BASIC_QUERY = """
SELECT ?item (COALESCE(SAMPLE(?enLabel), SAMPLE(?mulLabel)) AS ?label) (SAMPLE(?anyDesc) AS ?desc)
  (SAMPLE(?links) AS ?sitelinks)
  (GROUP_CONCAT(DISTINCT STR(?gender); separator="|") AS ?genders)
  (GROUP_CONCAT(DISTINCT STR(?birth); separator="|") AS ?births)
  (GROUP_CONCAT(DISTINCT STR(?death); separator="|") AS ?deaths)
  (GROUP_CONCAT(DISTINCT STR(?inception); separator="|") AS ?inceptions)
  (GROUP_CONCAT(DISTINCT ?awardLabel; separator="|") AS ?nobels)
WHERE {
  VALUES ?item { %s }
  OPTIONAL { ?item wikibase:sitelinks ?links }
  OPTIONAL { ?item wdt:P571 ?inception }
  OPTIONAL { ?item rdfs:label ?enLabel FILTER(LANG(?enLabel) = "en") }
  # Wikidata increasingly stores shared names as "mul" (multiple languages).
  OPTIONAL { ?item rdfs:label ?mulLabel FILTER(LANG(?mulLabel) = "mul") }
  OPTIONAL { ?item schema:description ?anyDesc FILTER(LANG(?anyDesc) = "en") }
  OPTIONAL { ?item wdt:P21 ?gender }
  OPTIONAL { ?item wdt:P569 ?birth }
  OPTIONAL { ?item wdt:P570 ?death }
  OPTIONAL {
    ?item wdt:P166 ?award .
    ?award rdfs:label ?awardLabel
    FILTER(LANG(?awardLabel) = "en" && CONTAINS(?awardLabel, "Nobel"))
  }
}
GROUP BY ?item
"""

CLAIM_QUERY = """
SELECT ?item ?value ?valueLabel WHERE {
  VALUES ?item { %s }
  ?item wdt:%s ?value .
  FILTER(ISIRI(?value))
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul". }
}
"""

WORK_QUERY = """
SELECT ?work (SAMPLE(?workLabel) AS ?label)
  (GROUP_CONCAT(DISTINCT CONCAT(STRAFTER(STR(?type), "entity/"), "=", ?typeLabel); separator="|") AS ?types)
  (GROUP_CONCAT(DISTINCT STR(?published); separator="|") AS ?dates)
  (GROUP_CONCAT(DISTINCT STR(?inception); separator="|") AS ?inceptions)
  (GROUP_CONCAT(DISTINCT CONCAT(STRAFTER(STR(?country), "entity/"), "=", ?countryLabel); separator="|") AS ?countries)
  (GROUP_CONCAT(DISTINCT STRAFTER(STR(?series), "entity/"); separator="|") AS ?series)
WHERE {
  VALUES ?work { %s }
  OPTIONAL { ?work wdt:P179 ?series }
  OPTIONAL { ?work rdfs:label ?workLabel FILTER(LANG(?workLabel) = "en") }
  OPTIONAL { ?work wdt:P31 ?type . ?type rdfs:label ?typeLabel FILTER(LANG(?typeLabel) = "en") }
  OPTIONAL { ?work wdt:P577 ?published }
  OPTIONAL { ?work wdt:P571 ?inception }
  OPTIONAL { ?work wdt:P495 ?country . ?country rdfs:label ?countryLabel FILTER(LANG(?countryLabel) = "en") }
}
GROUP BY ?work
"""


def read_roster_rows(path=ROSTER_PATH):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def roster_qids(rows):
    """Roster IDs plus any separate IDs used only for popularity (sitelinks)."""
    qids = [row["wikidata_id"].strip() for row in rows]
    extra = [(row.get("popularity_wikidata_id") or "").strip() for row in rows]
    return qids + sorted({qid for qid in extra if qid} - set(qids))


def candidate_qids(rows, path=CANDIDATES_PATH):
    """Top-ranked eligible candidates, with a buffer for entries skipped later."""
    if not path.exists():
        return []
    curated = {kind: sum(row["kind"] == kind for row in rows) for kind in ("real", "fictional")}
    limits = {
        "real": math.ceil((TARGET_REAL - curated["real"]) * FETCH_BUFFER),
        "fictional": math.ceil((TARGET_FICTIONAL - curated["fictional"]) * FETCH_BUFFER),
    }
    with open(path, newline="", encoding="utf-8") as handle:
        return [row["wikidata_id"] for row in csv.DictReader(handle)
                if row["status"] == "eligible" and int(row["rank"]) <= limits[row["kind"]]]


def split_field(binding, key):
    return [part for part in value(binding, key).split("|") if part]


def parse_basic(bindings):
    entities = {}
    for binding in bindings:
        entities[entity_id(value(binding, "item"))] = {
            "label": value(binding, "label"),
            "description": value(binding, "desc"),
            "sitelinks": int(value(binding, "sitelinks", "0")),
            "genders": split_field(binding, "genders"),
            "births": split_field(binding, "births"),
            "deaths": split_field(binding, "deaths"),
            "inceptions": split_field(binding, "inceptions"),
            "nobel_awards": split_field(binding, "nobels"),
        }
    return entities


def parse_claims(bindings):
    """Map entity ID -> sorted list of {"id", "label"} values for one property."""
    values = {}
    for binding in bindings:
        item = entity_id(value(binding, "item"))
        found = {"id": entity_id(value(binding, "value")), "label": value(binding, "valueLabel")}
        values.setdefault(item, []).append(found)
    return {item: sorted({v["id"]: v for v in found}.values(), key=lambda v: v["id"])
            for item, found in values.items()}


def parse_pairs(binding, key):
    """'Q1=label|Q2=label' -> [{"id": "Q1", "label": "label"}, ...]"""
    pairs = []
    for part in split_field(binding, key):
        qid, _, label = part.partition("=")
        pairs.append({"id": qid, "label": label})
    return pairs


def values_clause(qids):
    return " ".join("wd:%s" % qid for qid in qids)


def fetch_entities(qids):
    entities = {}
    for batch in chunks(qids, BATCH_SIZE):
        entities.update(parse_basic(sparql(BASIC_QUERY % values_clause(batch))))
        time.sleep(PAUSE_SECONDS)
    for property_id, description in CLAIM_PROPERTIES.items():
        print("  %s (%s)" % (property_id, description))
        claims = {}
        for batch in chunks(qids, BATCH_SIZE):
            claims.update(parse_claims(sparql(CLAIM_QUERY % (values_clause(batch), property_id))))
            time.sleep(PAUSE_SECONDS)
        for qid, entity in entities.items():
            entity.setdefault("claims", {})[property_id] = claims.get(qid, [])
    return entities


def fetch_work_details(work_ids):
    works = {}
    for batch in chunks(work_ids, BATCH_SIZE):
        for binding in sparql(WORK_QUERY % values_clause(batch)):
            works[entity_id(value(binding, "work"))] = {
                "label": value(binding, "label"),
                "types": parse_pairs(binding, "types"),
                # Publication dates are preferred over inception (e.g. when writing began).
                "published": split_field(binding, "dates"),
                "inceptions": split_field(binding, "inceptions"),
                "countries": parse_pairs(binding, "countries"),
                "series": split_field(binding, "series"),
            }
        time.sleep(PAUSE_SECONDS)
    return works


def fetch_works(entities):
    """Works characters appear in, plus the series an episode or issue belongs to (P179)."""
    work_ids = sorted({
        found["id"]
        for entity in entities.values()
        for prop in WORK_LINK_PROPERTIES
        for found in entity.get("claims", {}).get(prop, [])
    })
    print("Fetching %d works..." % len(work_ids))
    works = fetch_work_details(work_ids)
    series_ids = sorted({sid for work in works.values() for sid in work["series"]} - set(works))
    print("Fetching %d series..." % len(series_ids))
    works.update(fetch_work_details(series_ids))
    return works


def main():
    rows = read_roster_rows()
    curated_ids = roster_qids(rows)
    extra_ids = [qid for qid in candidate_qids(rows) if qid not in set(curated_ids)]
    qids = curated_ids + extra_ids
    print("Fetching %d entities (%d roster, %d candidates)..." % (len(qids), len(curated_ids), len(extra_ids)))
    entities = fetch_entities(qids)
    missing = sorted(set(qids) - set(entities))
    if missing:
        print("Wikidata returned nothing for: %s" % missing, file=sys.stderr)
        return 1
    snapshot = {
        "retrieved": date.today().isoformat(),
        "source": WDQS_ENDPOINT,
        "claim_properties": CLAIM_PROPERTIES,
        "entities": entities,
        "works": fetch_works(entities),
    }
    temporary = SNAPSHOT_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(snapshot, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(SNAPSHOT_PATH)  # atomic: an interrupted run never leaves a half-written snapshot
    print("Saved %d entities and %d works to %s" % (len(entities), len(snapshot["works"]),
                                                     SNAPSHOT_PATH.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
