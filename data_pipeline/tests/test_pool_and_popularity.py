import csv

import pytest

from preprocess import RosterError, build_dataset, derive_attributes, format_row, parse_roster_row, sitelinks_for
from question_pool import PoolError, PoolQuestion, check_pool, claim_set, load_pool, pool_value
from questions import CORE_QUESTIONS, POOL_QUESTIONS, QUESTIONS, load_pool_questions
from test_preprocess import make_fictional_row, make_row

NAMES = {"Ada Lovelace", "Alan Turing", "Pikachu", "Isaac Newton"}
POOL_HEADER = ["attribute", "question", "sources", "add", "remove", "unknown", "gate", "keywords", "notes"]


def write_pool(path, rows):
    """Rows may omit gate and keywords (7 cells); they are then left empty."""
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(POOL_HEADER)
        writer.writerows(row[:6] + ["", ""] + row[6:] if len(row) == 7 else row for row in rows)
    return path


def question(attribute="occupation_mathematician", sources=(("P106", "Q170790"),),
             add=(), remove=(), unknown=()):
    return PoolQuestion(attribute, frozenset(sources), frozenset(add), frozenset(remove), frozenset(unknown))


# --- questions.py ------------------------------------------------------------

def test_questions_are_core_plus_pool_without_overlap():
    assert QUESTIONS == {**CORE_QUESTIONS, **POOL_QUESTIONS}
    assert not set(CORE_QUESTIONS) & set(POOL_QUESTIONS)
    assert len(POOL_QUESTIONS) >= 30


def test_load_pool_questions_rejects_clash_with_core(tmp_path):
    path = write_pool(tmp_path / "pool.csv", [["is_male", "Male?", "", "Ada Lovelace", "", "", ""]])

    with pytest.raises(ValueError, match="is_male"):
        load_pool_questions(path)


def test_load_pool_questions_rejects_duplicates_and_empty_text(tmp_path):
    duplicate = write_pool(tmp_path / "dup.csv", [["a_b", "Q?", "", "", "", "", ""], ["a_b", "Q?", "", "", "", "", ""]])
    empty = write_pool(tmp_path / "empty.csv", [["a_b", "  ", "", "", "", "", ""]])

    with pytest.raises(ValueError, match="more than once"):
        load_pool_questions(duplicate)
    with pytest.raises(ValueError, match="question"):
        load_pool_questions(empty)


# --- parsing the pool --------------------------------------------------------

def test_load_pool_parses_sources_and_name_lists(tmp_path):
    path = write_pool(tmp_path / "pool.csv", [
        ["occupation_mathematician", "Mathematician?", "P106=Q170790", "Alan Turing", "", "Isaac Newton", "note"],
    ])

    pool = load_pool(path, NAMES)

    assert pool == (question(add={"Alan Turing"}, unknown={"Isaac Newton"}),)


@pytest.mark.parametrize("row, message", [
    (["x_y", "Q?", "P106:Q1", "", "", "", ""], "sources"),
    (["x_y", "Q?", "P106=Q1", "Nobody", "", "", ""], "Nobody"),
    (["x_y", "Q?", "P106=Q1", "Ada Lovelace", "Ada Lovelace", "", ""], "Ada Lovelace"),
    (["x_y", "Q?", "", "", "", "Ada Lovelace", ""], "add"),
])
def test_load_pool_rejects_invalid_rows(tmp_path, row, message):
    path = write_pool(tmp_path / "pool.csv", [row])

    with pytest.raises(PoolError, match=message):
        load_pool(path, NAMES)


# --- membership --------------------------------------------------------------

def test_pool_value_combines_wikidata_and_manual_corrections():
    q = question(add={"Alan Turing"}, remove={"Ada Lovelace"}, unknown={"Isaac Newton"})
    holder_claims = frozenset({("P106", "Q170790")})

    assert pool_value(q, "Galileo Galilei", holder_claims) is True
    assert pool_value(q, "Alan Turing", frozenset()) is True
    assert pool_value(q, "Ada Lovelace", holder_claims) is False
    assert pool_value(q, "Isaac Newton", holder_claims) is None
    assert pool_value(q, "Pikachu", frozenset()) is False


def test_check_pool_rejects_corrections_that_change_nothing():
    claims = {"Ada Lovelace": frozenset({("P106", "Q170790")}), "Alan Turing": frozenset()}

    with pytest.raises(PoolError, match="already"):
        check_pool([question(add={"Ada Lovelace"})], claims)
    with pytest.raises(PoolError, match="not a Wikidata holder"):
        check_pool([question(remove={"Alan Turing"})], claims)


def test_claim_set_reads_snapshot_claims():
    entity = {"claims": {"P106": [{"id": "Q170790", "label": "mathematician"}], "P69": []}}

    assert claim_set(entity) == frozenset({("P106", "Q170790")})


def test_derive_attributes_includes_pool_and_allows_overrides_on_pool_columns():
    q = question()
    entry = parse_roster_row(make_row(overrides="occupation_mathematician=unknown"), line_number=2)

    attributes = derive_attributes(entry, pool=[q], claims=frozenset({("P106", "Q170790")}))

    assert list(attributes) == list(CORE_QUESTIONS) + ["occupation_mathematician"]
    assert attributes["occupation_mathematician"] is None


# --- popularity --------------------------------------------------------------

def test_sitelinks_use_popularity_id_when_given():
    entities = {"Q9351": {"sitelinks": 8}, "Q1": {"sitelinks": 70}}
    plain = parse_roster_row(make_fictional_row(), line_number=2)
    redirected = parse_roster_row(make_fictional_row(popularity_wikidata_id="Q1"), line_number=2)

    assert sitelinks_for(plain, entities) == 8
    assert sitelinks_for(redirected, entities) == 70


def test_sitelinks_missing_from_snapshot_is_an_error():
    entry = parse_roster_row(make_fictional_row(), line_number=2)

    with pytest.raises(RosterError, match="fetch_wikidata"):
        sitelinks_for(entry, {})


def test_invalid_popularity_id_is_rejected():
    with pytest.raises(RosterError, match="popularity_wikidata_id"):
        parse_roster_row(make_row(popularity_wikidata_id="Totoro"), line_number=9)


def test_format_row_writes_sitelinks_before_source():
    entry = parse_roster_row(make_fictional_row(), line_number=2)

    row = format_row(entry, sitelinks=42)

    assert list(row)[-2:] == ["sitelinks", "source"]
    assert row["sitelinks"] == "42"


# --- the real project data ---------------------------------------------------

def test_project_pool_matches_question_text_and_snapshot():
    rows = build_dataset()

    assert len(rows) >= 91  # curated roster plus any generated entries
    assert list(rows[0]) == ["name"] + list(QUESTIONS) + ["sitelinks", "source"]
    assert all(int(row["sitelinks"]) > 0 for row in rows)


# --- review follow-ups ---------------------------------------------------------

def test_claim_set_requires_claims_and_sourced_properties():
    with pytest.raises(PoolError, match="claims"):
        claim_set({"label": "x"})
    with pytest.raises(PoolError, match="P69"):
        claim_set({"claims": {"P106": []}}, required={"P69"})


def test_check_pool_rejects_sourced_question_without_any_holder():
    claims = {"Ada Lovelace": frozenset(), "Alan Turing": frozenset()}

    with pytest.raises(PoolError, match="no roster entry"):
        check_pool([question()], claims)


@pytest.mark.parametrize("row", [
    {"attribute": "x_y", "question": "Q?", "sources": "P106=Q1", "add": None, "remove": None, "unknown": None},
    {"attribute": "x_y", "question": "Q?", "sources": "P106=Q1", "add": "", "remove": "", "unknown": "",
     "notes": "", None: ["extra"]},
])
def test_pool_rows_with_missing_or_extra_cells_are_rejected(row):
    from question_pool import parse_pool_row

    with pytest.raises(PoolError, match="cells"):
        parse_pool_row(row, 3, NAMES)


@pytest.mark.parametrize("attribute", ["name", "source", "sitelinks"])
def test_reserved_attribute_names_are_rejected(tmp_path, attribute):
    path = write_pool(tmp_path / "pool.csv", [[attribute, "Q?", "P106=Q1", "", "", "", ""]])

    with pytest.raises(PoolError, match="reserved"):
        load_pool(path, NAMES)


def test_load_pool_questions_rejects_missing_file_header_only_and_bad_header(tmp_path):
    header_only = write_pool(tmp_path / "empty.csv", [])
    bad_header = tmp_path / "bad.csv"
    bad_header.write_text("attribute,text\nx_y,Q?\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing.csv"):
        load_pool_questions(tmp_path / "missing.csv")
    with pytest.raises(ValueError, match="no questions"):
        load_pool_questions(header_only)
    with pytest.raises(ValueError, match="question"):
        load_pool_questions(bad_header)


def test_malformed_snapshot_and_missing_sitelinks_are_reported(tmp_path):
    from preprocess import load_snapshot

    broken = tmp_path / "snapshot.json"
    broken.write_text('{"retrieved": "2026-10-16"}', encoding="utf-8")
    entry = parse_roster_row(make_fictional_row(), line_number=2)

    with pytest.raises(RosterError, match="fetch_wikidata"):
        load_snapshot(broken)
    with pytest.raises(RosterError, match="sitelinks"):
        sitelinks_for(entry, {"Q9351": {"label": "Pikachu"}})


@pytest.mark.parametrize("attributes", [
    {"award_nobel_peace": True, "won_nobel_prize": False},
    {"sport_tennis": True, "known_for_sport": False},
    {"universe_dc": True, "is_fictional": False},
    {"position_us_president": True, "has_ruled_a_country": False},
])
def test_cross_layer_contradictions_are_detected(attributes):
    from data_loader import find_inconsistencies

    assert find_inconsistencies(attributes) != []



# --- description gate for generated entries -------------------------------------

def test_gate_turns_unmentioned_occupations_into_unknown_for_generated_entries():
    singer = PoolQuestion("occupation_singer", frozenset({("P106", "Q177220")}), frozenset(), frozenset(),
                          frozenset(), "real", frozenset({"singer"}))
    claims = frozenset({("P106", "Q177220")})

    assert pool_value(singer, "Scarlett Johansson", claims, "American actress") is None
    assert pool_value(singer, "Adele", claims, "English singer-songwriter") is True
    assert pool_value(singer, "Dolly Parton", frozenset(), "American singer-songwriter") is True   # description says so
    assert pool_value(singer, "Tom Hanks", frozenset(), "American actor") is False
    assert pool_value(singer, "Curated Person", claims) is True               # curated: no description gate
    assert pool_value(singer, "Some Character", claims, "fictional character", is_fictional=True) is True


def test_gate_and_keywords_must_be_given_together(tmp_path):
    path = write_pool(tmp_path / "pool.csv", [["x_y", "Q?", "P106=Q1", "", "", "", "real", "", ""]])

    with pytest.raises(PoolError, match="together"):
        load_pool(path, NAMES)


def test_pool_sport_questions_imply_sport():
    from data_loader import find_inconsistencies

    assert find_inconsistencies({"sport_tennis": True, "known_for_sport": False}) != []
    assert find_inconsistencies({"sport_tennis": True, "known_for_sport": True}) == []
