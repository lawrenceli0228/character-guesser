"""Read and validate roster files (one human-readable row per person or character).

Two files share this format:
- raw/roster.csv: hand-curated and reviewed entry by entry;
- raw/roster_auto.csv: generated from Wikidata by
  scripts/build_auto_roster.py, using "unknown" wherever the data is unclear.

See docs/DATA.md for the column rules. Every check fails with the file line
number, so a bad row is easy to find.
"""

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, Optional, Sequence, Tuple

from questions import QUESTIONS

ROOT = Path(__file__).resolve().parent.parent
ROSTER_PATH = ROOT / "raw" / "roster.csv"
AUTO_ROSTER_PATH = ROOT / "raw" / "roster_auto.csv"
COUNTRIES_PATH = ROOT / "raw" / "countries.csv"

ROSTER_COLUMNS = (
    "name", "wikidata_id", "popularity_wikidata_id", "kind", "gender", "species", "origin_year", "alive",
    "age_at_death", "region", "country", "domains", "media", "tags", "overrides", "notes",
)

KINDS = {"real", "fictional"}
GENDERS = {"male", "female", "unknown"}
ALIVE_VALUES = {"yes", "no", "unknown", "na"}
UNKNOWN = "unknown"
SPECIES_TO_HUMAN_ANIMAL = {
    "human": (True, False),
    "animal": (False, True),
    "other": (False, False),
    "unknown": (None, None),
}
REGION_FEATURES = {
    "asia": "from_asia",
    "europe": "from_europe",
    "north_america": "from_north_america",
    "south_america": "from_south_america",
    "africa": "from_africa",
    "oceania": "from_oceania",
}
COUNTRY_FEATURES = {
    "from_chinese_speaking_world": {"China", "Hong Kong", "Taiwan"},
    "from_usa": {"USA"},
    "from_uk": {"UK"},
    "from_japan": {"Japan"},
    "from_france": {"France"},
    "from_germany": {"Germany"},
    "from_italy": {"Italy"},
    "from_spain": {"Spain"},
    "from_russia": {"Russia"},
    "from_india": {"India"},
    "from_canada": {"Canada"},
    "from_brazil": {"Brazil"},
}
DOMAIN_FEATURES = {
    "science": "known_for_science_or_medicine",
    "technology": "known_for_technology",
    "politics": "known_for_politics_or_leadership",
    "sport": "known_for_sport",
    "football": "known_for_football",
    "music": "known_for_music",
    "acting": "known_for_acting_or_tv",
    "film": "known_for_filmmaking",
    "writing": "known_for_writing",
    "art": "known_for_visual_art",
    "business": "known_for_business",
    "exploration": "known_for_exploration",
}
TAG_FEATURES = {
    "nobel": "won_nobel_prize",
    "ruler": "has_ruled_a_country",
    "royal": "is_monarch_or_royal",
    "powers": "has_superpowers_or_magic",
    "villain": "is_villain",
    "robot": "is_robot_or_machine",
}
MEDIA_FEATURES = {
    "book": "first_appeared_in_book",
    "comic": "first_appeared_in_comic",
    "animation": "first_appeared_in_animation",
    "video_game": "first_appeared_in_video_game",
    "live_action": "first_appeared_in_live_action",
}
REAL_ONLY_TAGS = frozenset({"nobel"})
FICTIONAL_ONLY_TAGS = frozenset({"powers", "villain"})
EARLIEST_LIVING_BIRTH_YEAR = 1900
OVERRIDE_VALUES = {"true": True, "false": False, "unknown": None}
WIKIDATA_ID_PATTERN = re.compile(r"^Q[1-9][0-9]*$")


class RosterError(ValueError):
    """Raised when a roster or the country table contains an invalid or inconsistent value."""


@dataclass(frozen=True)
class RosterEntry:
    name: str
    wikidata_id: str
    popularity_id: Optional[str]
    is_fictional: bool
    gender: str
    species: str
    origin_year: Optional[int]          # None: unknown
    alive: str                          # yes / no / unknown (real), na (fictional)
    age_at_death: Optional[int]         # None: alive, fictional or unknown
    regions: FrozenSet[str]             # empty: unknown; several: debatable
    countries: FrozenSet[str]           # empty: unknown; several: debatable
    domains: FrozenSet[str]
    media: Optional[str]                # None for real people; "unknown" allowed for fictional
    tags: FrozenSet[str]
    overrides: Tuple[Tuple[str, Optional[bool]], ...]
    is_generated: bool = False          # True for rows from roster_auto.csv
    notes: str = ""                     # for generated rows: the Wikidata one-line description


# --- country table ------------------------------------------------------------

def load_countries(path=COUNTRIES_PATH) -> Dict[str, str]:
    """Country name -> region, from raw/countries.csv."""
    countries = {}
    with open(path, newline="", encoding="utf-8-sig") as handle:
        for line_number, row in enumerate(csv.DictReader(handle), start=2):
            name = (row.get("country") or "").strip()
            region = (row.get("region") or "").strip()
            if not name or region not in REGION_FEATURES:
                raise RosterError("%s line %d: needs a country name and a region in %s"
                                  % (path, line_number, sorted(REGION_FEATURES)))
            if name in countries:
                raise RosterError("%s line %d: country %r appears more than once" % (path, line_number, name))
            countries[name] = region
    return countries


_DEFAULT_COUNTRIES = None


def default_countries() -> Dict[str, str]:
    global _DEFAULT_COUNTRIES
    if _DEFAULT_COUNTRIES is None:
        _DEFAULT_COUNTRIES = load_countries()
    return _DEFAULT_COUNTRIES


# --- cell parsing ---------------------------------------------------------------

def _fail(line_number, message):
    raise RosterError("line %d: %s" % (line_number, message))


def _text(row, field):
    """Cell text; DictReader gives None for cells missing from a short row."""
    return (row.get(field) or "").strip()


def _items(text):
    return [item.strip() for item in text.split(";") if item.strip()]


def _choice(row, field, allowed, line_number):
    value = _text(row, field)
    if value not in allowed:
        _fail(line_number, "%s must be one of %s, got %r" % (field, sorted(allowed), value))
    return value


def _vocab_list(row, field, allowed, line_number):
    items = _items(_text(row, field))
    unknown = [item for item in items if item not in allowed]
    if unknown:
        _fail(line_number, "%s contains unknown value(s) %s; allowed: %s" % (field, unknown, sorted(allowed)))
    return frozenset(items)


def _parse_overrides(text, line_number):
    overrides = []
    for item in _items(text):
        feature, separator, value = item.partition("=")
        if not separator:
            _fail(line_number, "override %r must look like feature=value" % item)
        if feature not in QUESTIONS:
            _fail(line_number, "override names unknown attribute %r" % feature)
        if value not in OVERRIDE_VALUES:
            _fail(line_number, "override value %r must be true, false or unknown" % value)
        if feature in dict(overrides):
            _fail(line_number, "override for %r appears more than once" % feature)
        overrides.append((feature, OVERRIDE_VALUES[value]))
    return tuple(overrides)


def _parse_year(row, line_number):
    text = _text(row, "origin_year")
    if not text:
        return None
    if not re.fullmatch(r"-?[0-9]+", text) or int(text) == 0:
        _fail(line_number, "origin_year must be empty or a non-zero whole year (negative for BCE), got %r" % text)
    return int(text)


def _parse_age_at_death(row, alive, line_number):
    text = _text(row, "age_at_death")
    if alive != "no":
        if text:
            _fail(line_number, "age_at_death must be empty unless alive is 'no', got %r" % text)
        return None
    if text and not re.fullmatch(r"[0-9]+", text):
        _fail(line_number, "age_at_death must be empty or a whole number, got %r" % text)
    return int(text) if text else None


def _parse_regions(row, line_number):
    text = _text(row, "region")
    if text == UNKNOWN:
        return frozenset()
    regions = _vocab_list(row, "region", set(REGION_FEATURES), line_number)
    if not regions:
        _fail(line_number, "region must list one or more regions or say 'unknown'")
    return regions


def _parse_countries(row, regions, countries_table, line_number):
    countries = frozenset(_items(_text(row, "country")))
    strangers = sorted(countries - set(countries_table))
    if strangers:
        _fail(line_number, "country %s not in raw/countries.csv; add it there with its region" % strangers)
    if countries and not regions:
        _fail(line_number, "region is 'unknown' but country is given; set region from the country")
    mismatched = sorted(c for c in countries if countries_table[c] not in regions)
    if mismatched:
        _fail(line_number, "region %s does not match country %s" % (sorted(regions), mismatched))
    return countries


def _parse_media(row, is_fictional, line_number):
    media = _text(row, "media")
    allowed = set(MEDIA_FEATURES) | {UNKNOWN}
    if is_fictional and media not in allowed:
        _fail(line_number, "fictional characters need media in %s, got %r" % (sorted(allowed), media))
    if not is_fictional and media:
        _fail(line_number, "real people must leave media empty, got %r" % media)
    return media or None


def _check_required_text(row, line_number):
    if None in row:
        _fail(line_number, "row has extra cells beyond the header: %s" % row[None])
    name = _text(row, "name")
    if not name:
        _fail(line_number, "name is empty")
    wikidata_id = _text(row, "wikidata_id")
    if not WIKIDATA_ID_PATTERN.match(wikidata_id):
        _fail(line_number, "wikidata_id must look like Q123, got %r" % wikidata_id)
    return name, wikidata_id


def _parse_popularity_id(row, line_number):
    text = _text(row, "popularity_wikidata_id")
    if text and not WIKIDATA_ID_PATTERN.match(text):
        _fail(line_number, "popularity_wikidata_id must be empty or look like Q123, got %r" % text)
    return text or None


def _parse_kind_and_alive(row, line_number):
    is_fictional = _choice(row, "kind", KINDS, line_number) == "fictional"
    alive = _choice(row, "alive", ALIVE_VALUES, line_number)
    if is_fictional != (alive == "na"):
        _fail(line_number, "alive must be 'na' for fictional characters and yes/no/unknown for real people")
    return is_fictional, alive


def _check_plausibility(entry, line_number):
    if not entry.is_fictional and not entry.domains:
        _fail(line_number, "domains must list at least one entry for real people (what they are known for)")
    wrong_tags = entry.tags & (REAL_ONLY_TAGS if entry.is_fictional else FICTIONAL_ONLY_TAGS)
    if wrong_tags:
        _fail(line_number, "tag(s) %s do not apply to %s" % (
            sorted(wrong_tags), "fictional characters" if entry.is_fictional else "real people"))
    if entry.alive == "yes" and entry.origin_year is not None and entry.origin_year < EARLIEST_LIVING_BIRTH_YEAR:
        _fail(line_number, "alive is 'yes' but origin_year is %d" % entry.origin_year)


def parse_roster_row(row, line_number, countries_table=None, is_generated=False) -> RosterEntry:
    """Validate one raw CSV row and return an immutable RosterEntry."""
    table = countries_table if countries_table is not None else default_countries()
    name, wikidata_id = _check_required_text(row, line_number)
    is_fictional, alive = _parse_kind_and_alive(row, line_number)
    regions = _parse_regions(row, line_number)
    entry = RosterEntry(
        name=name,
        wikidata_id=wikidata_id,
        popularity_id=_parse_popularity_id(row, line_number),
        is_fictional=is_fictional,
        gender=_choice(row, "gender", GENDERS, line_number),
        species=_choice(row, "species", set(SPECIES_TO_HUMAN_ANIMAL), line_number),
        origin_year=_parse_year(row, line_number),
        alive=alive,
        age_at_death=_parse_age_at_death(row, alive, line_number),
        regions=regions,
        countries=_parse_countries(row, regions, table, line_number),
        domains=_vocab_list(row, "domains", set(DOMAIN_FEATURES), line_number),
        media=_parse_media(row, is_fictional, line_number),
        tags=_vocab_list(row, "tags", set(TAG_FEATURES), line_number),
        overrides=_parse_overrides(_text(row, "overrides"), line_number),
        is_generated=is_generated,
        notes=_text(row, "notes"),
    )
    _check_plausibility(entry, line_number)
    return entry


# --- files ------------------------------------------------------------------------

def check_unique(entries: Sequence[RosterEntry]):
    """Reject duplicate names or Wikidata IDs (case-insensitive names)."""
    seen_names, seen_ids = set(), set()
    for entry in entries:
        key = entry.name.casefold()
        if key in seen_names:
            raise RosterError("Duplicate name: %s" % entry.name)
        if entry.wikidata_id in seen_ids:
            raise RosterError("Duplicate Wikidata ID: %s (%s)" % (entry.wikidata_id, entry.name))
        seen_names.add(key)
        seen_ids.add(entry.wikidata_id)


def load_roster(path=ROSTER_PATH, countries_table=None, is_generated=False) -> Tuple[RosterEntry, ...]:
    # utf-8-sig also accepts files saved by Excel with a byte-order mark.
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
        missing = [column for column in ROSTER_COLUMNS if column not in header]
        if missing:
            raise RosterError("%s is missing column(s): %s" % (path, missing))
        duplicated = sorted({c for c in header if header.count(c) > 1})
        if duplicated:
            raise RosterError("%s has column(s) appearing more than once: %s" % (path, duplicated))
        # Line 1 is the header, so data rows start at line 2.
        try:
            entries = tuple(
                parse_roster_row(row, line_number, countries_table, is_generated)
                for line_number, row in enumerate(reader, start=2)
            )
        except RosterError as error:
            raise RosterError("%s %s" % (Path(path).name, error)) from error
    if not entries:
        raise RosterError("%s contains no rows" % path)
    check_unique(entries)
    return entries
