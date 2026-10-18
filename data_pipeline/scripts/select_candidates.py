"""Rank well-known people and fictional characters to extend the roster.

Usage:
    python scripts/select_candidates.py

1. QLever: the HUMAN_POOL humans and FICTIONAL_POOL fictional characters with
   the most Wikipedia/Wikimedia sitelinks (a broad, objective long list).
2. Drop entries already in raw/roster.csv and those in
   raw/exclusions.csv (religious figures, people known mainly for
   atrocities or terrorism).
3. WDQS: English Wikipedia article title, a "mul" label when there is no
   English one, and for fictional characters whether they belong to an
   identifiable work (P1441, P4584, P1080, P170 or P8345). Characters from
   mythology, religion or folklore usually have none and are dropped.
4. Wikipedia API: English Wikipedia pageviews over the last PAGEVIEW_DAYS days
   (50 articles per request; the per-article REST API was too heavily
   rate-limited from here).
   Sitelinks favour long-established and occasionally spam-inflated
   entries; 60-day pageviews favour whatever is in the news. The long list is
   ranked by score = pageviews x sitelinks, which balances current and
   long-term recognition.

Writes raw/candidates.csv (every long-list entry with its status and
rank) and caches pageviews in raw/pageviews_60d_direct.json.
"""

import csv
import json
import sys
import time
import urllib.parse
from pathlib import Path

from wikidata_http import chunks, entity_id, get_json, qlever, sparql, value

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
ROSTER_PATH = RAW / "roster.csv"
EXCLUSIONS_PATH = RAW / "exclusions.csv"
CANDIDATES_PATH = RAW / "candidates.csv"
PAGEVIEWS_CACHE_PATH = RAW / "pageviews_60d_direct.json"
DETAILS_CACHE_PATH = RAW / "candidate_details.json"

HUMAN_POOL = 1200
FICTIONAL_POOL = 700
BATCH_SIZE = 100
PAGEVIEW_DAYS = 60  # the batched Wikipedia API covers at most the last 60 days
PAGEVIEW_BATCH = 50  # titles per API call
WORK_PROPERTIES = ("P1441", "P4584", "P1080", "P170", "P8345")

TOP_QUERY = """
SELECT ?item ?n ?l ?d WHERE {
  { SELECT DISTINCT ?item ?n WHERE { %s ?item wikibase:sitelinks ?n . } ORDER BY DESC(?n) LIMIT %d }
  OPTIONAL { ?item rdfs:label ?l . FILTER(LANG(?l) = "en") }
  OPTIONAL { ?item schema:description ?d . FILTER(LANG(?d) = "en") }
}
"""
HUMAN_PATTERN = "?item wdt:P31 wd:Q5 ."
FICTIONAL_PATTERN = "?item wdt:P31/wdt:P279* wd:Q95074 ."

DETAIL_QUERY = """
SELECT ?item (SAMPLE(?title) AS ?enwiki) (SAMPLE(?mul) AS ?mulLabel) (COUNT(?work) AS ?works) WHERE {
  VALUES ?item { %s }
  OPTIONAL { ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?title }
  OPTIONAL { ?item rdfs:label ?mul FILTER(LANG(?mul) = "mul") }
  OPTIONAL { ?item %s ?work }
}
GROUP BY ?item
"""

FIELDS = ["wikidata_id", "kind", "label", "description", "sitelinks", "enwiki_title",
          "pageviews", "has_work", "status", "rank"]


def read_ids(path, column="wikidata_id"):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return {row[column].strip() for row in csv.DictReader(handle) if row[column].strip()}


def top_entities(pattern, limit, kind):
    print("QLever: top %d %s by sitelinks..." % (limit, kind))
    entities = {}
    for binding in qlever(TOP_QUERY % (pattern, limit)):
        qid = entity_id(value(binding, "item"))
        entities.setdefault(qid, {
            "wikidata_id": qid, "kind": kind, "label": value(binding, "l"),
            "description": value(binding, "d"), "sitelinks": int(value(binding, "n", "0")),
        })
    return entities


def add_details(entities):
    cache = json.loads(DETAILS_CACHE_PATH.read_text(encoding="utf-8")) if DETAILS_CACHE_PATH.exists() else {}
    for qid, details in cache.items():
        if qid in entities:
            entities[qid].update(details)
    todo = sorted(qid for qid in entities if qid not in cache)
    print("WDQS: Wikipedia titles and work links for %d entities (%d cached)..." % (len(todo), len(entities) - len(todo)))
    work_path = "|".join("wdt:%s" % p for p in WORK_PROPERTIES)
    for count, batch in enumerate(chunks(todo, BATCH_SIZE), start=1):
        values = " ".join("wd:%s" % qid for qid in batch)
        for binding in sparql(DETAIL_QUERY % (values, work_path)):
            entity = entities[entity_id(value(binding, "item"))]
            entity["enwiki_title"] = value(binding, "enwiki")
            entity["label"] = entity["label"] or value(binding, "mulLabel")
            entity["has_work"] = int(value(binding, "works", "0")) > 0
            cache[entity["wikidata_id"]] = {k: entity[k] for k in ("enwiki_title", "label", "has_work")}
        DETAILS_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")
        print("  batch %d done" % count, flush=True)
        time.sleep(1)


def fetch_pageview_batch(titles):
    """Total views over the last PAGEVIEW_DAYS days for up to 50 titles (one API call)."""
    # Redirects are NOT followed: a character without its own article (whose title redirects
    # to e.g. "List of Harry Potter characters") must not inherit the list's pageviews.
    params = {"action": "query", "prop": "pageviews", "pvipdays": PAGEVIEW_DAYS,
              "titles": "|".join(titles), "format": "json", "formatversion": 2}
    totals, extra = {}, {}
    while True:
        data = get_json("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({**params, **extra}))
        query = data.get("query", {})
        # Map normalised titles back to the titles we asked for.
        renamed = {item["to"]: item["from"] for item in query.get("normalized", [])}
        for page in query.get("pages", []):
            original = page["title"]
            while original in renamed:
                original = renamed[original]
            views = sum(count or 0 for count in (page.get("pageviews") or {}).values())
            totals[original] = totals.get(original, 0) + views
        if "continue" not in data:
            return totals
        extra = data["continue"]


def add_pageviews(entities):
    cache = json.loads(PAGEVIEWS_CACHE_PATH.read_text(encoding="utf-8")) if PAGEVIEWS_CACHE_PATH.exists() else {}
    titles = sorted({e["enwiki_title"] for e in entities.values() if e.get("enwiki_title")})
    missing = [title for title in titles if title not in cache]
    print("Wikipedia API: %d-day pageviews for %d articles (%d cached)..." % (
        PAGEVIEW_DAYS, len(titles), len(titles) - len(missing)))
    for count, batch in enumerate(chunks(missing, PAGEVIEW_BATCH), start=1):
        found = fetch_pageview_batch(batch)
        cache.update({title: found.get(title, 0) for title in batch})
        PAGEVIEWS_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")
        if count % 10 == 0:
            print("  batch %d" % count, flush=True)
        time.sleep(0.5)
    for entity in entities.values():
        if entity.get("enwiki_title"):
            entity["pageviews"] = cache[entity["enwiki_title"]]


def status_of(entity, roster_ids, excluded_ids):
    if entity["wikidata_id"] in roster_ids:
        return "in_roster"
    if entity["wikidata_id"] in excluded_ids:
        return "excluded"
    if not entity.get("enwiki_title") or not entity.get("pageviews"):
        return "no_enwiki_article"
    if entity["kind"] == "fictional" and not entity.get("has_work"):
        return "no_identifiable_work"
    return "eligible"


def rank_entities(entities, roster_ids, excluded_ids):
    for entity in entities.values():
        entity["status"] = status_of(entity, roster_ids, excluded_ids)
    for kind in ("real", "fictional"):
        eligible = sorted((e for e in entities.values() if e["kind"] == kind and e["status"] == "eligible"),
                          key=lambda e: -e["pageviews"] * e["sitelinks"])
        seen_labels = set()
        rank = 0
        for entity in eligible:
            if entity["label"].casefold() in seen_labels:
                entity["status"] = "duplicate_label"
                continue
            seen_labels.add(entity["label"].casefold())
            rank += 1
            entity["rank"] = rank


def main():
    roster_ids = read_ids(ROSTER_PATH)
    excluded_ids = read_ids(EXCLUSIONS_PATH)
    entities = top_entities(HUMAN_PATTERN, HUMAN_POOL, "real")
    fictional = top_entities(FICTIONAL_PATTERN, FICTIONAL_POOL, "fictional")
    entities.update({qid: e for qid, e in fictional.items() if qid not in entities})
    add_details(entities)
    add_pageviews(entities)
    rank_entities(entities, roster_ids, excluded_ids)
    missing_exclusions = sorted(excluded_ids - set(entities))
    if missing_exclusions:
        print("Note: exclusions not in the long list: %s" % missing_exclusions)
    rows = sorted(entities.values(), key=lambda e: (e["kind"], e.get("rank") or 10 ** 6, -e["sitelinks"]))
    with open(CANDIDATES_PATH, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    counts = {}
    for entity in entities.values():
        counts[(entity["kind"], entity["status"])] = counts.get((entity["kind"], entity["status"]), 0) + 1
    print("Wrote %d candidates to %s" % (len(rows), CANDIDATES_PATH.relative_to(ROOT)))
    for key in sorted(counts):
        print("  %-10s %-22s %d" % (key[0], key[1], counts[key]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
