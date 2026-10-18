"""List Wikidata property values that could become extra Yes/No questions.

Usage:
    python scripts/propose_questions.py

Reads data/raw/wikidata_snapshot.json and writes
data/raw/question_candidates.csv: every (property, value) shared by at least
MIN_SHARED roster entries, with how many entries and which ones have it.

The candidate list is only input for manual review. Questions that are kept
are written by hand into data/raw/question_pool.csv, with player-friendly
wording and, where useful, several Wikidata values merged into one question
(e.g. actor + film actor + television actor).
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROSTER_PATH = ROOT / "data" / "raw" / "roster.csv"
AUTO_ROSTER_PATH = ROOT / "data" / "raw" / "roster_auto.csv"
SNAPSHOT_PATH = ROOT / "data" / "raw" / "wikidata_snapshot.json"
OUTPUT_PATH = ROOT / "data" / "raw" / "question_candidates.csv"
MIN_SHARED = 2
# Properties that can become player-facing questions. The snapshot also holds
# helper properties (citizenship, class, works) used only to build the roster.
QUESTION_PROPERTIES = ("P106", "P166", "P39", "P641", "P1303", "P69", "P1080", "P170", "P8345", "P54")


def roster_names():
    """Wikidata ID -> name for the curated and (if present) generated rosters."""
    names = {}
    for path in (ROSTER_PATH, AUTO_ROSTER_PATH):
        if path.exists():
            with open(path, newline="", encoding="utf-8-sig") as handle:
                names.update({row["wikidata_id"]: row["name"] for row in csv.DictReader(handle)})
    return names


def collect_candidates(snapshot, names):
    """Map (property, value id) -> (value label, sorted member names)."""
    members = defaultdict(set)
    labels = {}
    for qid, entity in snapshot["entities"].items():
        if qid not in names:
            continue
        for property_id, values in entity.get("claims", {}).items():
            if property_id not in QUESTION_PROPERTIES:
                continue
            for value in values:
                key = (property_id, value["id"])
                members[key].add(names[qid])
                labels[key] = value["label"]
    return {key: (labels[key], sorted(found)) for key, found in members.items() if len(found) >= MIN_SHARED}


def main():
    if not SNAPSHOT_PATH.exists():
        print("No snapshot found; run `python scripts/fetch_wikidata.py` first.", file=sys.stderr)
        return 1
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    candidates = collect_candidates(snapshot, roster_names())
    property_names = snapshot["claim_properties"]
    rows = sorted(candidates.items(), key=lambda item: (item[0][0], -len(item[1][1]), item[1][0]))
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["property", "property_name", "value_id", "value_label", "count", "members"])
        for (property_id, value_id), (label, found) in rows:
            writer.writerow([property_id, property_names[property_id], value_id, label, len(found), "; ".join(found)])
    print("Wrote %d candidates to %s" % (len(rows), OUTPUT_PATH.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
