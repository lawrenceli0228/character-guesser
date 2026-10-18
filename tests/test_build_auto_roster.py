import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_auto_roster import (  # noqa: E402
    age_between,
    clean_description,
    fictional_medium,
    first_year,
    reviewed_traits,
    has_title,
    medium_from_description,
    fictional_origin,
    derive_real,
    fictional_tags,
    gender_of,
    has_word,
    life_columns,
    medium_of,
    places,
    real_domains,
    real_tags,
)

TABLES = {
    "countries": {"Q30": ("USA", "north_america"), "Q183": ("Germany", "europe")},
    "keywords": [("physicist", "science"), ("president", "politics"), ("singer", "music"),
                 ("general", "politics"), ("co-founder", "business"), ("artist", "art"),
                 ("martial artist", "sport"), ("actor", "acting")],
    "work_media": {"Q8261": ("book", False), "Q202866": ("animation", False), "Q11424": ("live_action", True),
                   "Q7725634": ("book", True), "Q1": ("ignore", False)},
    "classes": {},
    "franchises": [],
}


def entity(description="", births=(), deaths=(), genders=(), claims=None, nobel=()):
    return {"description": description, "births": list(births), "deaths": list(deaths),
            "genders": list(genders), "nobel_awards": list(nobel), "claims": claims or {}}


def claim(*qids, label=""):
    return [{"id": qid, "label": label} for qid in qids]


def unmapped():
    return {"countries": Counter(), "work_types": Counter(), "classes": Counter()}


# --- text matching ------------------------------------------------------------------

def test_has_word_matches_whole_words_only():
    assert has_word("american singer-songwriter", "singer") is False   # hyphenated compound
    assert has_word("american singer and actor", "singer")
    assert has_word("british husband", "band") is False
    assert has_word("secretary-general of the un", "general") is False


def test_vice_president_does_not_count_as_president():
    assert has_word(clean_description("Vice President of the United States"), "president") is False
    assert has_word(clean_description("44th President of the United States"), "president")


# --- real people ----------------------------------------------------------------------

def test_real_domains_come_from_description_only():
    hobby = entity(claims={"P641": claim("Q2736")})   # a recorded sport is not what someone is known for

    assert real_domains("german theoretical physicist", entity(), TABLES) == {"science"}
    assert real_domains("prince of wales", hobby, TABLES) == set()


def test_derive_real_skips_people_without_a_recognisable_domain():
    row, reason = derive_real({}, entity("Swedish nobleman"), TABLES, unmapped())

    assert row is None
    assert "known for" in reason


def test_real_tags_ruler_royal_and_nobel():
    president = entity(claims={"P39": claim("Q11696", label="President of the United States")}, nobel=["Nobel Peace Prize"])
    vice = entity(claims={"P39": claim("Q11699", label="Vice President of the United States")})

    assert real_tags("american lawyer", president) == {"ruler", "nobel"}
    assert real_tags("american lawyer", vice) == set()
    queen = entity("Queen of the United Kingdom")
    assert real_tags(clean_description(queen["description"]), queen) == {"ruler", "royal"}


def test_gender_of_maps_known_ids_and_leaves_others_unknown():
    assert gender_of(entity(genders=["http://www.wikidata.org/entity/Q6581097"])) == "male"
    assert gender_of(entity(genders=["http://www.wikidata.org/entity/Q1052281"])) == "female"
    assert gender_of(entity(genders=["http://www.wikidata.org/entity/Q48270"])) == "unknown"
    assert gender_of(entity(genders=["http://www.wikidata.org/.well-known/genid/abc"])) == "unknown"


@pytest.mark.parametrize("births, deaths, expected", [
    (["1940-10-09T00:00:00Z"], ["1980-12-08T00:00:00Z"], {"origin_year": "1940", "alive": "no", "age_at_death": "40"}),
    (["1989-12-13T00:00:00Z"], [], {"origin_year": "1989", "alive": "yes", "age_at_death": ""}),
    (["1500-01-01T00:00:00Z"], [], {"origin_year": "1500", "alive": "unknown", "age_at_death": ""}),
    ([], [], {"origin_year": "", "alive": "unknown", "age_at_death": ""}),
])
def test_life_columns(births, deaths, expected):
    assert life_columns(entity(births=births, deaths=deaths)) == expected


def test_places_maps_countries_and_counts_unmapped():
    counter = Counter()

    assert places(["Q183", "Q30"], TABLES, counter) == (["Germany", "USA"], ["europe", "north_america"])
    places(["Q999"], TABLES, counter)
    assert counter == Counter({"Q999": 1})


# --- fictional characters ---------------------------------------------------------------

def work(*type_ids):
    return {"types": [{"id": qid, "label": qid} for qid in type_ids]}


def test_medium_of_uses_a_single_mapped_medium():
    found = unmapped()

    assert medium_of([work("Q8261")], TABLES, found) == "book"
    assert medium_of([work("Q11424")], TABLES, found) == "live_action"
    assert medium_of([work("Q777")], TABLES, found) is None
    assert found["work_types"][("Q777", "Q777")] == 1


def test_specific_types_win_over_generic_ones():
    animated_film = work("Q202866", "Q11424")      # "animated film" and "film"

    assert medium_of([animated_film], TABLES, unmapped()) == "animation"


def test_conflicting_specific_media_are_unknown():
    assert medium_of([work("Q8261"), work("Q202866")], TABLES, unmapped()) is None
    assert medium_of([work("Q11424"), work("Q7725634")], TABLES, unmapped()) is None


def test_fictional_tags_from_description_and_claims():
    hogwarts = entity(claims={"P69": claim("Q174097")}, description="student")

    assert fictional_tags("fictional supervillain", entity("fictional supervillain"), set()) == {"powers", "villain"}
    assert fictional_tags("student", hogwarts, set()) == {"powers"}
    assert fictional_tags("robot character", entity("robot character"), set()) == {"robot"}


@pytest.mark.parametrize("description, expected", [
    ("fictional character in the Star Wars universe and Queen of Naboo", True),
    ("main antagonist of Stephen King's novel It", False),
    ("son of Han Solo and Princess Leia", False),
    ("the king of the jungle", True),
])
def test_has_title_ignores_title_words_inside_names(description, expected):
    assert has_title(description, {"king", "queen", "princess"}) is expected


@pytest.mark.parametrize("description, expected", [
    ("fictional character in Marvel Comics", "comic"),
    ("main antagonist of Stephen King's novel It", "book"),
    ("fictional novel and movie character created by Robert Ludlum", "book"),
    ("Warner Bros. cartoon character", "animation"),
    ("fictional character in the television drama series Breaking Bad", "live_action"),
    ("fictional character by Sanrio", None),
])
def test_medium_from_description_uses_the_earliest_medium_word(description, expected):
    assert medium_from_description(description) == expected


def test_fictional_origin_uses_first_appearance_and_its_series():
    snapshot = {"works": {
        "W1": {"types": [{"id": "Q21191270", "label": "episode"}], "published": ["1992-09-11T00:00:00Z"],
               "countries": [], "series": ["S1"]},
        "S1": {"types": [{"id": "Q117467246", "label": "animated television series"}], "published": ["1992-09-05T00:00:00Z"],
               "countries": [{"id": "Q30", "label": "USA"}], "series": []},
    }}
    tables = {**TABLES, "franchises": [], "work_media": {"Q21191270": ("live_action", True), "Q117467246": ("animation", False)}}
    character = entity(claims={"P4584": claim("W1")})

    assert fictional_origin(character, snapshot, tables, unmapped()) == ("animation", 1992, ["Q30"])


def test_fictional_origin_falls_back_to_classes_and_inception():
    tables = {**TABLES, "franchises": [], "classes": {"Q1114461": {"species": "", "tags": "", "media": "comic"},
                                    "Q15773347": {"species": "", "tags": "", "media": "live_action"}}}
    character = {**entity(claims={"P31": claim("Q1114461")}), "inceptions": ["1990-01-01T00:00:00Z"]}

    assert fictional_origin(character, {"works": {}}, tables, unmapped()) == ("comic", 1990, [])



# --- review round 3 ----------------------------------------------------------------

def test_ig_nobel_is_not_a_nobel_prize():
    assert real_tags("american businessman", entity(nobel=["Ig Nobel Prize"])) == set()
    assert real_tags("american physicist", entity(nobel=["Nobel Prize in Physics"])) == {"nobel"}


def test_non_state_presidencies_do_not_make_a_ruler():
    juror = entity("American actor", claims={"P39": claim("Q1", label="President of the Jury at the Cannes Festival")})

    assert "ruler" not in real_tags("american actor", juror)


def test_band_names_are_not_royal_titles():
    mercury = entity("British singer, frontman of the rock band Queen")
    queen = entity("Queen of the United Kingdom from 1952 to 2022")

    assert real_tags(clean_description(mercury["description"]), mercury) == set()
    assert real_tags(clean_description(queen["description"]), queen) == {"ruler", "royal"}


def test_longer_keywords_consume_shorter_ones():
    assert real_domains("american martial artist and actor", entity(), TABLES) == {"sport", "acting"}


def test_life_columns_ignore_unknown_value_dates_and_implausible_ages():
    genid = "http://www.wikidata.org/.well-known/genid/abc"
    assert life_columns(entity(births=[genid], deaths=[genid])) == {"origin_year": "", "alive": "no", "age_at_death": ""}
    assert life_columns(entity(births=["1905-01-01T00:00:00Z"]))["alive"] == "unknown"   # would be 121


def test_age_between_crosses_bce_and_ce_without_a_year_zero():
    # Augustus: 63 BCE (XSD year -62) to 14 CE; year precision gives 76 (true age 75)
    assert age_between("-0062-09-23T00:00:00Z", "0014-08-19T00:00:00Z") == 76
    assert age_between("1940-10-09T00:00:00Z", "1980-12-08T00:00:00Z") == 40


def test_first_year_prefers_publication_over_inception():
    novel = {"published": ["1997-06-26T00:00:00Z"], "inceptions": ["1990-01-01T00:00:00Z"]}

    assert first_year([novel]) == 1997
    assert first_year([{"inceptions": ["1990-01-01T00:00:00Z"]}]) == 1990


def test_generic_literary_work_beats_classes_and_class_conflicts_are_ignored():
    tables = {**TABLES, "franchises": [], "classes": {"Q15773347": {"species": "", "tags": "", "media": "live_action"},
                                    "Q3658341": {"species": "", "tags": "", "media": "book"}}}
    hobbit = work("Q7725634")                                        # "literary work" (generic book)
    film_character = entity("Middle-earth character", claims={"P31": claim("Q15773347")})
    mixed = entity("character", claims={"P31": claim("Q15773347", "Q3658341")})
    episode = work("Q11424")

    assert fictional_medium(film_character, [hobbit], tables, unmapped()) == "book"
    assert fictional_medium(mixed, [], tables, unmapped()) is None


def test_reviewed_traits_set_tags_and_unknown_overrides():
    tables = {"traits": {"Q1": {"powers": "yes", "villain": "unknown", "royal": "no", "ruler": "no"}}}

    tags, overrides = reviewed_traits("Q1", {"royal"}, tables)

    assert tags == {"powers"}
    assert overrides == ["is_villain=unknown"]


def test_unreviewed_characters_get_unknown_villain_and_powers():
    tags, overrides = reviewed_traits("Q2", set(), {"traits": {}})

    assert "is_villain=unknown" in overrides and "has_superpowers_or_magic=unknown" in overrides


def test_places_are_unknown_when_any_citizenship_is_unmapped():
    counter = Counter()

    assert places(["Q30", "Q999"], TABLES, counter) == ([], [])
    assert places(["Q30", "Q223050"], TABLES, counter) == (["USA"], ["north_america"])   # statelessness ignored


def test_bare_position_titles_are_not_heads_of_state():
    philip = entity("consort of Elizabeth II", claims={"P39": claim("Q1", label="president")})

    assert "ruler" not in real_tags(clean_description(philip["description"]), philip)
