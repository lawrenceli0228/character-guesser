"""Generate raw/roster_auto.csv from Wikidata for the extended dataset.

Usage:
    python scripts/select_candidates.py   # ranked candidates (network)
    python scripts/fetch_wikidata.py      # facts for roster + candidates (network)
    python scripts/build_auto_roster.py   # this script (offline)
    python src/preprocess.py

Walks the eligible candidates in pageview order and derives one roster row
each, until dataset_config.TARGET_REAL / TARGET_FICTIONAL (including the
curated roster) are reached. The rules, all documented in docs/DATA.md:

- Real people: "known for" domains come from keywords in the one-line
  Wikidata description (raw/domain_keywords.csv), which states what
  someone is mainly known for. Country/region from citizenship (P27) via
  raw/countries.csv; several citizenships make the places debatable.
- Fictional characters: medium, year and country come from the work they
  first appeared in (P4584), else the works they appear in (P1441), using
  raw/work_types.csv. Species from their class (P31) via
  raw/character_classes.csv.
- Anything that cannot be determined is written as unknown, never guessed.
- Entries with too little usable data are skipped (listed in the report).

Writes raw/roster_auto.csv and raw/auto_roster_report.txt (skipped
entries and unmapped Wikidata values to review).
"""

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

from check_wikidata import exact_age, year_of
from dataset_config import TARGET_FICTIONAL, TARGET_REAL
from wikidata_http import entity_id

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
SNAPSHOT_PATH = RAW / "wikidata_snapshot.json"
CANDIDATES_PATH = RAW / "candidates.csv"
ROSTER_PATH = RAW / "roster.csv"
OUTPUT_PATH = RAW / "roster_auto.csv"
CORRECTIONS_PATH = RAW / "auto_corrections.csv"
TRAITS_PATH = RAW / "fictional_traits.csv"  # hand-reviewed powers/villain for generated characters
REPORT_PATH = RAW / "auto_roster_report.txt"

ROSTER_COLUMNS = (
    "name", "wikidata_id", "popularity_wikidata_id", "kind", "gender", "species", "origin_year", "alive",
    "age_at_death", "region", "country", "domains", "media", "tags", "overrides", "notes",
)
EARLIEST_LIVING_BIRTH_YEAR = 1900
GENDER_IDS = {
    "male": {"Q6581097", "Q44148", "Q2449503"},      # male, male organism, trans man
    "female": {"Q6581072", "Q43445", "Q1052281"},    # female, female organism, trans woman
}
# Description phrases that must not trigger a keyword (e.g. "vice president").
IGNORED_PHRASES = ("vice president", "vice-president", "president-elect")
# Ruling titles are matched as titles (see has_title), so "rock band Queen" or
# "Stephen King" do not count; office words are matched as plain words.
RULER_TITLES = {"king", "queen", "emperor", "empress", "tsar", "sultan", "pharaoh", "khan", "monarch", "shah"}
ROYAL_TITLES = RULER_TITLES | {"prince", "princess"}
RULER_OFFICES = ("president", "prime minister", "chancellor", "supreme leader", "dictator", "leader of the soviet union")
ROYAL_PHRASES = ("royal family", "heir apparent", "consort of", "queen consort", "princess consort")
RULER_POSITIONS = re.compile(r"^(president|prime minister|king|queen|emperor|empress|chancellor of germany|"
                             r"monarch|premier|supreme leader|chairman of the chinese communist party|"
                             r"general secretary)\b", re.IGNORECASE)
# Positions that start like a head of state but are not one ("President of the Jury at the Cannes Festival").
NON_STATE_WORDS = re.compile(r"\b(jury|festival|commission|council|academy|association|society|university|college|"
                             r"club|federation|committee|court|senate|assembly|league|foundation|board|bank|"
                             r"institute|guild|school|company|corporation|union of|society)\b", re.IGNORECASE)
NOBEL_PATTERN = re.compile(r"^Nobel (Prize|Peace Prize|Memorial Prize)")  # excludes the Ig Nobel Prize
TITLE_STOPWORDS = {"band", "group", "duo", "drag", "rock"}  # "rock band Queen", "drag queen"
IGNORED_COUNTRY_IDS = {"Q223050"}  # statelessness
OLDEST_PLAUSIBLE_AGE = 110
VALID_DATE = re.compile(r"^[+-]?\d+-\d\d-\d\d")  # excludes Wikidata "unknown value" blank nodes
POWER_WORDS = ("superhero", "supervillain", "wizard", "witch", "sorcerer", "sorceress", "jedi", "sith",
               "mutant", "vampire", "demigod", "magical", "god of", "goddess")
VILLAIN_WORDS = ("villain", "supervillain", "antagonist", "nemesis", "arch-enemy", "archenemy")
ROBOT_WORDS = ("robot", "android", "droid", "cyborg")
MAGIC_SOURCES = {("P106", "Q148401"), ("P69", "Q174097")}  # magician; Hogwarts (pool question occupation_wizard)


# --- tables -----------------------------------------------------------------------

def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_tables():
    countries = {}
    for row in read_csv(RAW / "countries.csv"):
        for qid in filter(None, (q.strip() for q in row["wikidata_ids"].split(";"))):
            countries[qid] = (row["country"], row["region"])
    work_types = read_csv(RAW / "work_types.csv")
    bad = [row["type_qid"] for row in work_types if row["generic"] not in ("", "yes")]
    if bad:
        raise SystemExit("work_types.csv: generic must be empty or 'yes' for %s" % bad)
    franchises = read_csv(RAW / "franchise_countries.csv")
    country_names = {name for name, _ in countries.values()}
    unknown = sorted({row["country"] for row in franchises if row["country"]} - country_names)
    if unknown:
        raise SystemExit("franchise_countries.csv names countries missing from countries.csv: %s" % unknown)
    return {
        "countries": countries,
        "keywords": [(row["keyword"].lower(), row["domain"]) for row in read_csv(RAW / "domain_keywords.csv")],
        "work_media": {row["type_qid"]: (row["media"], row["generic"] == "yes") for row in work_types},
        "classes": {row["class_qid"]: row for row in read_csv(RAW / "character_classes.csv")},
        "franchises": [(row["keyword"].lower(), row["country"], row["media"]) for row in franchises],
        "traits": load_traits(),
    }


TRAIT_COLUMNS = ("powers", "villain", "royal", "ruler")
TRAIT_VERDICTS = ("yes", "no", "unknown")


def load_traits():
    traits = {}
    for row in read_csv(TRAITS_PATH):
        bad = [c for c in TRAIT_COLUMNS if row.get(c) not in TRAIT_VERDICTS]
        if bad:
            raise SystemExit("fictional_traits.csv: %s must be yes/no/unknown in %s" % (bad, row.get("name")))
        if row["wikidata_id"] in traits:
            raise SystemExit("fictional_traits.csv: %s appears more than once" % row["wikidata_id"])
        traits[row["wikidata_id"]] = row
    return traits


# --- text helpers ------------------------------------------------------------------

def clean_description(text):
    lowered = text.lower()
    for phrase in IGNORED_PHRASES:
        lowered = lowered.replace(phrase, " ")
    return lowered


def has_word(text, word):
    """Whole-word match; hyphens count as part of a word ("secretary-general" is not "general")."""
    return re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(word), text) is not None


def any_word(text, words):
    return any(has_word(text, word) for word in words)


def ids(entity, prop):
    return [value["id"] for value in entity.get("claims", {}).get(prop, [])]


def labels(entity, prop):
    return [value["label"] for value in entity.get("claims", {}).get(prop, [])]


# --- shared derivations ------------------------------------------------------------------

def gender_of(entity):
    found = {entity_id(uri) for uri in entity["genders"] if "/entity/" in uri}
    matches = [name for name, qids in GENDER_IDS.items() if found & qids]
    return matches[0] if len(matches) == 1 else "unknown"


def places(country_ids, tables, unmapped):
    """Mapped country names and regions; unknown ([], []) if any ID is not in countries.csv,
    because dropping it would make the remaining places look complete."""
    names, regions, missing = set(), set(), False
    for qid in country_ids:
        if qid in IGNORED_COUNTRY_IDS:
            continue
        if qid in tables["countries"]:
            name, region = tables["countries"][qid]
            names.add(name)
            regions.add(region)
        else:
            unmapped[qid] += 1
            missing = True
    return ([], []) if missing else (sorted(names), sorted(regions))


def place_columns(names, regions):
    return {"region": ";".join(regions) if regions else "unknown", "country": ";".join(names)}


# --- real people ---------------------------------------------------------------------------

def age_between(birth, death):
    if birth.startswith("-") or death.startswith("-"):  # BCE: year precision only, and there is no year 0
        years = year_of(death) - year_of(birth)
        return years - 1 if year_of(birth) < 0 < year_of(death) else years
    return exact_age(birth, death)


def life_columns(entity, today_year=2026):
    births = sorted((b for b in entity["births"] if VALID_DATE.match(b)), key=year_of)
    deaths = [d for d in entity["deaths"] if VALID_DATE.match(d)]
    birth_year = year_of(births[0]) if births else None
    if entity["deaths"]:  # any death statement, even an "unknown value" date
        alive = "no"
    elif birth_year is not None and EARLIEST_LIVING_BIRTH_YEAR <= birth_year > today_year - OLDEST_PLAUSIBLE_AGE:
        alive = "yes"
    else:
        alive = "unknown"
    age = str(age_between(births[0], deaths[0])) if alive == "no" and births and deaths else ""
    return {"origin_year": "" if birth_year is None else str(birth_year), "alive": alive, "age_at_death": age}


def real_domains(description, entity, tables):
    """Domains named by keywords in the description, longest keyword first; a matched
    phrase is removed so "martial artist" does not also count as "artist".

    Only the description counts: Wikidata also records hobbies and honorary roles
    under "sport" (P641), e.g. Stanley Kubrick (chess) or Prince William (football)."""
    consumed = description.lower()
    domains = set()
    for keyword in sorted({k for k, _ in tables["keywords"]}, key=len, reverse=True):
        if has_word(consumed, keyword):
            domains.update(d for k, d in tables["keywords"] if k == keyword)
            consumed = re.sub(r"(?<![\w-])%s(?![\w-])" % re.escape(keyword), " ", consumed)
    return domains


def is_state_position(label):
    """A head-of-state or government office that names what it governs ("President of
    France", "King of Norway"); a bare "president" may be of any organisation."""
    # State offices are capitalised on Wikidata ("Prime Minister of India"); lower-case
    # ones are usually posts in organisations ("president of the Société des gens de lettres").
    return (bool(RULER_POSITIONS.match(label)) and label[:1].isupper() and " of " in label.lower()
            and not re.search(r"\b(vice|consort)\b", label, re.IGNORECASE) and not NON_STATE_WORDS.search(label))


def real_tags(description, entity):
    """description is the cleaned (lower-case, no "vice president") text; titles are
    checked on the original description so capitalised names can be recognised."""
    tags = set()
    if any(NOBEL_PATTERN.match(award) for award in entity["nobel_awards"]):
        tags.add("nobel")
    original = entity["description"]
    positions = labels(entity, "P39")
    if any_word(description, RULER_OFFICES) or has_title(original, RULER_TITLES) or any(map(is_state_position, positions)):
        tags.add("ruler")
    if (has_title(original, ROYAL_TITLES) or any_word(original.lower(), ROYAL_PHRASES)
            or any(p.lower().startswith(("monarch of", "king of", "queen of", "emperor of")) for p in positions)):
        tags.add("royal")
    return tags


def derive_real(candidate, entity, tables, unmapped):
    # Domains use the full description ("vice president" still means politics);
    # the ruler tag uses the cleaned one (a vice president has not ruled).
    domains = real_domains(entity["description"].lower(), entity, tables)
    description = clean_description(entity["description"])
    tags = real_tags(description, entity)
    if tags & {"ruler", "royal"}:
        domains.add("politics")  # rulers and royals count as known for leadership
    if not domains:
        return None, "no recognisable 'known for' keyword in description %r" % entity["description"]
    life = life_columns(entity)
    if life["alive"] == "yes" and life["origin_year"] and int(life["origin_year"]) < EARLIEST_LIVING_BIRTH_YEAR:
        return None, "implausible dates"
    names, regions = places(ids(entity, "P27"), tables, unmapped["countries"])
    row = {
        "kind": "real", "gender": gender_of(entity), "species": "human", **life,
        **place_columns(names, regions), "domains": ";".join(sorted(domains)), "media": "",
        "tags": ";".join(sorted(tags)), "overrides": "",
    }
    return row, None


# --- fictional characters ------------------------------------------------------------------

def works_of(entity, snapshot, prop):
    return [snapshot["works"][qid] for qid in ids(entity, prop) if qid in snapshot["works"]]


def with_series(works, snapshot):
    """Each work plus the series it belongs to (an episode inherits its show's type and country)."""
    found = list(works)
    for work in works:
        found += [snapshot["works"][sid] for sid in work.get("series", []) if sid in snapshot["works"]]
    return found


def work_media(works, tables, unmapped):
    """(specific media, generic media) named by the works' types."""
    specific, generic = set(), set()
    for work in works:
        for work_type in work["types"]:
            if work_type["id"] not in tables["work_media"]:
                unmapped["work_types"][(work_type["id"], work_type["label"])] += 1
                continue
            medium, is_generic = tables["work_media"][work_type["id"]]
            if medium != "ignore":
                (generic if is_generic else specific).add(medium)
    if "animation" in specific:
        specific.discard("live_action")  # an "animated film" is also listed as a "film"
    return specific, generic


def single(values):
    return next(iter(values)) if len(values) == 1 else None


def medium_of(works, tables, unmapped):
    """The single medium of these works, or None when unknown or conflicting.

    Generic types ("film", "literary work") only count when no specific type
    ("animated film", "comic book issue") is present, because Wikidata often
    gives a work both, e.g. an animated film is also a "film".
    """
    specific, generic = work_media(works, tables, unmapped)
    return single(specific or generic)


# Medium words in a character's one-line description ("fictional character in Marvel
# Comics", "main antagonist of Stephen King's novel It"). The earliest match wins.
DESCRIPTION_MEDIA = (
    ("comic", r"comics?|comic strip|manga|graphic novel"),
    ("book", r"novels?|books?|legendarium|short stor(y|ies)|literary|nursery rhyme|fairy tale"),
    ("video_game", r"video games?|videogames?"),
    ("animation", r"animated|cartoons?|anime|animation"),
    ("live_action", r"films?|movies?|television|tv series|sitcom|drama series"),
)


def medium_from_description(description):
    matches = []
    for medium, pattern in DESCRIPTION_MEDIA:
        found = re.search(r"(?<!\w)(%s)(?!\w)" % pattern, description.lower())
        if found:
            matches.append((found.start(), medium))
    return min(matches)[1] if matches else None


def first_year(works):
    """Earliest publication year (P577) of the works, else earliest inception (P571).
    Publication wins: the first Harry Potter novel was begun in 1990 but published in 1997."""
    for key in ("published", "inceptions"):
        years = [year_of(d) for work in works for d in work.get(key, []) if VALID_DATE.match(d)]
        if years:
            return min(years)
    return None


def medium_from_classes(entity, tables):
    """The medium named by the character's classes, only if they name exactly one
    ("comics character" and "film character" together say nothing about the origin)."""
    media = {tables["classes"][c]["media"] for c in ids(entity, "P31") if c in tables["classes"]} - {""}
    return single(media)


def fictional_medium(entity, works, tables, unmapped):
    """Evidence in order: a specific type of the first-appearance work (or its series);
    medium words in the description; a generic "literary work" (a first appearance in
    a book); a franchise or author named in the description; classes naming a single
    medium; a generic screen type ("television series")."""
    specific, generic = work_media(works, tables, unmapped)
    generic_book = "book" if generic == {"book"} else None
    return (single(specific) or medium_from_description(entity["description"]) or generic_book
            or franchise_medium(entity["description"], tables)
            or medium_from_classes(entity, tables) or single(generic - {"book"}))


def franchise_medium(description, tables):
    """Original medium of a franchise or author named in the description
    (franchise_countries.csv), e.g. "by Agatha Christie" -> book, "from One Piece" -> comic."""
    lowered = description.lower()
    return single({medium for keyword, _, medium in tables["franchises"] if medium and keyword in lowered})


def fictional_origin(entity, snapshot, tables, unmapped):
    """(medium, year, work country ids) from the first-appearance work (P4584) and its series.

    "Present in work" (P1441) is not used: for comic characters it lists later films
    and games, which gave wrong years and media. Fallbacks when P4584 is missing:
    the description and classes for the medium, the inception (P571) for the year.
    """
    own = works_of(entity, snapshot, "P4584")
    with_shows = with_series(own, snapshot)
    medium = fictional_medium(entity, with_shows, tables, unmapped)
    # An episode's own date beats its series' start date (a late character joins a long-running show).
    year = first_year(own) or first_year(with_shows) or first_year([{"inceptions": entity.get("inceptions", [])}])
    countries = [c["id"] for work in with_shows for c in work["countries"]]
    return medium, year, countries


def species_and_class_tags(entity, tables, unmapped):
    species, tags = set(), set()
    for class_id, label in zip(ids(entity, "P31"), labels(entity, "P31")):
        row = tables["classes"].get(class_id)
        if row is None:
            unmapped["classes"][(class_id, label)] += 1
            continue
        if row["species"]:
            species.add(row["species"])
        tags.update(filter(None, row["tags"].split(";")))
    # Conflicting classes (or a class marked "unknown", e.g. a hybrid) leave species unknown.
    return (species.pop() if len(species) == 1 else "unknown"), tags


def has_title(original, words):
    """A title word used as a title, not inside a name: "Queen of Naboo" counts,
    "Stephen King" and "Princess Leia" (capitalised next to another capitalised word) do not."""
    tokens = re.findall(r"[\w'’-]+", original)
    for index, token in enumerate(tokens):
        if token.lower().rstrip("'’s") not in words and token.lower() not in words:
            continue
        previous = tokens[index - 1] if index else ""
        neighbours = tokens[max(index - 1, 0):index] + tokens[index + 1:index + 2]
        in_name = token[0].isupper() and any(n[0].isupper() for n in neighbours)
        if not in_name and previous.lower() not in TITLE_STOPWORDS:
            return True
    return False


def fictional_tags(description, entity, class_tags):
    tags = set(class_tags)
    claims = {(p, q) for p in ("P106", "P69") for q in ids(entity, p)}
    if any_word(description, POWER_WORDS) or claims & MAGIC_SOURCES:
        tags.add("powers")
    if any_word(description, VILLAIN_WORDS):
        tags.add("villain")
    if any_word(description, ROBOT_WORDS):
        tags.add("robot")
    original = entity["description"]
    if has_title(original, {"prince", "princess", "king", "queen", "emperor", "empress"}):
        tags.add("royal")
    if has_title(original, {"king", "queen", "emperor", "empress"}):
        tags.add("ruler")
    return tags


def franchise_country(description, tables):
    """Fallback country from a well-known franchise or publisher named in the description
    (raw/franchise_countries.csv), e.g. "fictional character in Marvel Comics" -> USA."""
    lowered = description.lower()
    countries = sorted({country for keyword, country, _ in tables["franchises"] if country and keyword in lowered})
    if len(countries) != 1:
        return [], []
    region = {name: region for name, region in tables["countries"].values()}[countries[0]]
    return countries, [region]


def reviewed_traits(qid, tags, tables):
    """Apply the hand-reviewed powers/villain values; return (tags, overrides).

    Without a review, powers come from the description/classes (else unknown) and
    "villain" is unknown unless the description says so: descriptions such as
    "fictional character in Marvel Comics" do not mention it (Thanos, the Joker)."""
    review = tables["traits"].get(qid, {})
    tags = set(tags)
    overrides = []
    for column, attribute in (("powers", "has_superpowers_or_magic"), ("villain", "is_villain"),
                              ("royal", "is_monarch_or_royal"), ("ruler", "has_ruled_a_country")):
        tag = column
        verdict = review.get(column) or ("yes" if tag in tags else "unknown")
        tags.discard(tag)
        if verdict == "yes":
            tags.add(tag)
        elif verdict == "unknown":
            overrides.append("%s=unknown" % attribute)
    return tags, overrides


def derive_fictional(candidate, entity, snapshot, tables, unmapped):
    medium, year, work_countries = fictional_origin(entity, snapshot, tables, unmapped)
    if medium is None and year is None:
        return None, "neither medium nor year of first appearance can be determined"
    species, class_tags = species_and_class_tags(entity, tables, unmapped)
    description = clean_description(entity["description"])
    tags = fictional_tags(description, entity, class_tags)
    if "robot" in tags and species == "human":
        species = "unknown"
    names, regions = places(ids(entity, "P495") or work_countries, tables, unmapped["countries"])
    if not names:
        names, regions = franchise_country(entity["description"], tables)
    tags, overrides = reviewed_traits(candidate["wikidata_id"], tags, tables)
    row = {
        "kind": "fictional", "gender": gender_of(entity), "species": species,
        "origin_year": "" if year is None else str(year), "alive": "na", "age_at_death": "",
        **place_columns(names, regions), "domains": "", "media": medium or "unknown",
        "tags": ";".join(sorted(tags)),
        "overrides": ";".join(overrides),
    }
    return row, None


# --- main ------------------------------------------------------------------------------------

def load_corrections():
    """Wikidata ID -> {roster column: value} found by spot-checking generated rows.

    The "set" column holds column=value pairs separated by ";;" (a value such as
    tags=royal;ruler may itself contain ";")."""
    corrections = {}
    for row in read_csv(CORRECTIONS_PATH):
        changes = {}
        for item in filter(None, (part.strip() for part in row["set"].split(";;"))):
            column, _, new_value = item.partition("=")
            if column not in ROSTER_COLUMNS:
                raise SystemExit("auto_corrections.csv: unknown column %r for %s" % (column, row["name"]))
            changes[column] = new_value
        if row["wikidata_id"] in corrections:
            raise SystemExit("auto_corrections.csv: %s appears more than once" % row["wikidata_id"])
        corrections[row["wikidata_id"]] = (row["name"], changes)
    return corrections


def corrected(qid, name, corrections):
    if qid not in corrections:
        return {}
    expected, changes = corrections[qid]
    if expected != name:
        raise SystemExit("auto_corrections.csv: %s is named %r there but %r in Wikidata" % (qid, expected, name))
    return changes


def curated_counts_and_names():
    rows = read_csv(ROSTER_PATH)
    counts = Counter(row["kind"] for row in rows)
    return counts, {row["name"].casefold() for row in rows}


def build_rows(snapshot, tables):
    counts, taken = curated_counts_and_names()
    targets = {"real": TARGET_REAL - counts["real"], "fictional": TARGET_FICTIONAL - counts["fictional"]}
    unmapped = {"countries": Counter(), "work_types": Counter(), "classes": Counter()}
    rows, skipped = [], []
    corrections = load_corrections()
    for candidate in read_csv(CANDIDATES_PATH):
        kind = candidate["kind"]
        if candidate["status"] != "eligible" or targets[kind] <= 0:
            continue
        entity = snapshot["entities"].get(candidate["wikidata_id"])
        name = (entity or {}).get("label", "").strip()
        if entity is None or not name or name.casefold() in taken:
            skipped.append((candidate, "not fetched, unnamed or duplicate name"))
            continue
        if kind == "real":
            row, reason = derive_real(candidate, entity, tables, unmapped)
        else:
            row, reason = derive_fictional(candidate, entity, snapshot, tables, unmapped)
        if row is None:
            skipped.append((candidate, reason))
            continue
        taken.add(name.casefold())
        targets[kind] -= 1
        rows.append({"name": name, "wikidata_id": candidate["wikidata_id"], "popularity_wikidata_id": "",
                     **row, "notes": entity["description"], **corrected(candidate["wikidata_id"], name, corrections)})
    unused = sorted(set(corrections) - {row["wikidata_id"] for row in rows})
    if unused:
        raise SystemExit("auto_corrections.csv lists IDs that are not generated: %s" % unused)
    return rows, skipped, unmapped, targets


def write_report(skipped, unmapped, targets):
    lines = ["Targets still unfilled: %s" % targets, "", "Skipped (%d):" % len(skipped)]
    lines += ["  %s %s (%s): %s" % (c["kind"], c["label"], c["wikidata_id"], reason) for c, reason in skipped]
    for key, title in (("countries", "Unmapped country IDs"), ("work_types", "Unmapped work types"),
                       ("classes", "Unmapped character classes")):
        lines += ["", "%s (%d):" % (title, len(unmapped[key]))]
        lines += ["  %s x%d" % (item, count) for item, count in unmapped[key].most_common()]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    rows, skipped, unmapped, targets = build_rows(snapshot, load_tables())
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ROSTER_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    write_report(skipped, unmapped, targets)
    kinds = Counter(row["kind"] for row in rows)
    print("Wrote %d rows (%d real, %d fictional) to %s; skipped %d; unfilled %s" % (
        len(rows), kinds["real"], kinds["fictional"], OUTPUT_PATH.relative_to(ROOT), len(skipped), targets))
    print("Review %s for unmapped values." % REPORT_PATH.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
