"""Extra Yes/No questions generated from Wikidata and reviewed by hand.

Each row of raw/question_pool.csv defines one question:

- sources: Wikidata facts that make the answer Yes, e.g. "P106=Q170790"
  (occupation = mathematician). Empty for purely manual questions.
- add / remove: roster names whose answer is corrected to Yes / No because
  Wikidata is missing a fact or lists one players would not recognise.
- unknown: roster names whose answer is genuinely debatable.
- gate / keywords: for generated (not hand-reviewed) entries the one-line
  Wikidata description decides, because it says what someone is known for
  while Wikidata lists many secondary occupations (actors as "singer"):
  keyword in the description -> Yes; Wikidata fact without a keyword ->
  unknown; neither -> No. gate is "real" (people only), "all" or empty.

The answer for everyone else follows Wikidata: Yes if they hold any source
fact, otherwise No. Every question was reviewed against the whole roster, so
treating a missing fact as No is a reviewed decision, not a default.
"""

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, Iterable, Mapping, Optional, Sequence, Tuple

POOL_PATH = Path(__file__).resolve().parent.parent / "raw" / "question_pool.csv"
POOL_COLUMNS = ("attribute", "question", "sources", "add", "remove", "unknown", "gate", "keywords", "notes")
GATES = ("", "real", "all")
SOURCE_PATTERN = re.compile(r"^(P[1-9][0-9]*)=(Q[1-9][0-9]*)$")
NAME_LISTS = ("add", "remove", "unknown")
# Non-attribute columns of dataset/characters.csv.
RESERVED_ATTRIBUTES = frozenset({"name", "source", "sitelinks"})


class PoolError(ValueError):
    """Raised when the question pool is malformed or inconsistent with the data."""


@dataclass(frozen=True)
class PoolQuestion:
    attribute: str
    sources: FrozenSet[Tuple[str, str]]
    add: FrozenSet[str]
    remove: FrozenSet[str]
    unknown: FrozenSet[str]
    gate: str = ""
    keywords: FrozenSet[str] = frozenset()


def _fail(line_number, message):
    raise PoolError("question_pool line %d: %s" % (line_number, message))


def _split(text):
    return [part.strip() for part in (text or "").split(";") if part.strip()]


def _parse_sources(text, line_number):
    sources = []
    for item in _split(text):
        match = SOURCE_PATTERN.match(item)
        if not match:
            _fail(line_number, "sources entry %r must look like P106=Q170790" % item)
        sources.append((match.group(1), match.group(2)))
    return frozenset(sources)


def _parse_names(row, field, known_names, line_number):
    names = frozenset(_split(row.get(field)))
    strangers = sorted(names - set(known_names))
    if strangers:
        _fail(line_number, "%s lists names that are not in the roster: %s" % (field, strangers))
    return names


def _check_no_overlap(lists, line_number):
    for first, second in (("add", "remove"), ("add", "unknown"), ("remove", "unknown")):
        overlap = sorted(lists[first] & lists[second])
        if overlap:
            _fail(line_number, "%s and %s both list %s" % (first, second, overlap))


def parse_pool_row(row, line_number, known_names) -> PoolQuestion:
    # DictReader stores extra cells under None and fills missing cells with None.
    if None in row or any(row.get(column) is None for column in POOL_COLUMNS):
        _fail(line_number, "row has missing or extra cells; expected columns %s" % list(POOL_COLUMNS))
    attribute = row["attribute"].strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", attribute):
        _fail(line_number, "attribute %r must be lower_snake_case" % attribute)
    if attribute in RESERVED_ATTRIBUTES:
        _fail(line_number, "attribute %r is reserved for a non-attribute column" % attribute)
    sources = _parse_sources(row.get("sources"), line_number)
    lists = {field: _parse_names(row, field, known_names, line_number) for field in NAME_LISTS}
    _check_no_overlap(lists, line_number)
    if not sources and not lists["add"]:
        _fail(line_number, "manual questions (no sources) need at least one name in add")
    gate = row["gate"].strip()
    keywords = frozenset(word.lower() for word in _split(row["keywords"]))
    if gate not in GATES:
        _fail(line_number, "gate must be one of %s, got %r" % (list(GATES), gate))
    if bool(gate) != bool(keywords):
        _fail(line_number, "gate and keywords must be given together")
    return PoolQuestion(attribute, sources, lists["add"], lists["remove"], lists["unknown"], gate, keywords)


def load_pool(path=POOL_PATH, known_names: Iterable[str] = ()) -> Tuple[PoolQuestion, ...]:
    names = frozenset(known_names)
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in POOL_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise PoolError("%s is missing column(s): %s" % (path, missing))
        pool = tuple(parse_pool_row(row, line, names) for line, row in enumerate(reader, start=2))
    attributes = [question.attribute for question in pool]
    duplicated = sorted({a for a in attributes if attributes.count(a) > 1})
    if duplicated:
        raise PoolError("question_pool attribute(s) appear more than once: %s" % duplicated)
    return pool


def required_properties(pool: Sequence[PoolQuestion]) -> FrozenSet[str]:
    """Wikidata properties that the pool's sources rely on."""
    return frozenset(property_id for question in pool for property_id, _ in question.sources)


def claim_set(entity: Mapping, required: Iterable[str] = ()) -> FrozenSet[Tuple[str, str]]:
    """All (property, value) facts of one snapshot entity.

    A property missing from the snapshot would silently turn every answer
    into No, so the properties the pool relies on must all be present.
    """
    if "claims" not in entity:
        raise PoolError("snapshot entity %r has no claims; run `python scripts/fetch_wikidata.py`"
                        % entity.get("label", "?"))
    missing = sorted(set(required) - set(entity["claims"]))
    if missing:
        raise PoolError("snapshot entity %r lacks properties %s; run `python scripts/fetch_wikidata.py`"
                        % (entity.get("label", "?"), missing))
    return frozenset(
        (property_id, value["id"])
        for property_id, values in entity["claims"].items()
        for value in values
    )


def pool_value(
    question: PoolQuestion,
    name: str,
    claims: FrozenSet[Tuple[str, str]],
    description: Optional[str] = None,
    is_fictional: bool = False,
) -> Optional[bool]:
    """description is given only for generated entries; it gates Wikidata-only Yes answers."""
    if name in question.unknown:
        return None
    if name in question.remove:
        return False
    if name in question.add:
        return True
    holds = bool(question.sources & claims)
    gated = description is not None and (question.gate == "all" or (question.gate == "real" and not is_fictional))
    if not gated:
        return holds
    if mentions(description, question.keywords):
        return True   # "Roman emperor" makes Augustus an emperor even without the Wikidata statement
    return None if holds else False


def mentions(text, keywords):
    """Whole-word, case-insensitive match. "singer-songwriter" mentions "singer", but
    "secretary-general" does not mention "general"."""
    lowered = text.lower()
    return any(re.search(r"(?<![\w-])%s(?!\w)" % re.escape(word), lowered) for word in keywords)


def check_pool(pool: Sequence[PoolQuestion], claims_by_name: Mapping[str, FrozenSet[Tuple[str, str]]]):
    """Reject sources nobody holds and corrections that would not change anything."""
    for question in pool:
        holders = {name for name, claims in claims_by_name.items() if question.sources & claims}
        if question.sources and not holders:
            raise PoolError("%s: no roster entry holds any source fact; check the Wikidata IDs" % question.attribute)
        redundant = sorted(question.add & holders)
        if redundant:
            raise PoolError("%s: add lists %s, who are already Wikidata holders" % (question.attribute, redundant))
        not_holders = sorted(question.remove - holders)
        if not_holders:
            raise PoolError("%s: remove lists %s, who are not a Wikidata holder" % (question.attribute, not_holders))
