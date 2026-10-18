import csv

import pytest

from preprocess import (
    RosterError,
    check_unique,
    derive_attributes,
    format_row,
    load_roster,
    parse_roster_row,
)
from questions import CORE_QUESTIONS


def make_row(**changes):
    row = {
        "name": "Ada Lovelace",
        "wikidata_id": "Q7259",
        "popularity_wikidata_id": "",
        "kind": "real",
        "gender": "female",
        "species": "human",
        "origin_year": "1815",
        "alive": "no",
        "age_at_death": "36",
        "region": "europe",
        "country": "UK",
        "domains": "science;technology",
        "media": "",
        "tags": "",
        "overrides": "",
        "notes": "",
    }
    return {**row, **changes}


def make_fictional_row(**changes):
    row = make_row(
        name="Pikachu", wikidata_id="Q9351", kind="fictional", gender="unknown",
        species="animal", origin_year="1996", alive="na", age_at_death="", region="asia",
        country="Japan", domains="", media="video_game", tags="powers",
    )
    return {**row, **changes}


def attributes_for(row):
    return derive_attributes(parse_roster_row(row, line_number=2))


# --- derivation -----------------------------------------------------------

def test_derived_attributes_without_pool_match_core_questions_exactly():
    assert set(attributes_for(make_row())) == set(CORE_QUESTIONS)
    assert set(attributes_for(make_fictional_row())) == set(CORE_QUESTIONS)


def test_real_person_identity_and_time_attributes():
    attributes = attributes_for(make_row())

    assert attributes["is_fictional"] is False
    assert attributes["is_male"] is False
    assert attributes["is_human"] is True
    assert attributes["is_animal"] is False
    assert attributes["is_alive"] is False
    assert attributes["origin_before_1500"] is False
    assert attributes["origin_before_1900"] is True
    assert attributes["origin_1970_or_later"] is False


def test_real_person_place_domain_and_media_attributes():
    attributes = attributes_for(make_row())

    assert attributes["from_europe"] is True
    assert attributes["from_asia"] is False
    assert attributes["from_uk"] is True
    assert attributes["from_usa"] is False
    assert attributes["known_for_science_or_medicine"] is True
    assert attributes["known_for_technology"] is True
    assert attributes["known_for_music"] is False
    assert attributes["first_appeared_in_book"] is False
    assert attributes["is_villain"] is False


def test_fictional_character_attributes():
    attributes = attributes_for(make_fictional_row())

    assert attributes["is_fictional"] is True
    assert attributes["is_alive"] is None
    assert attributes["is_male"] is None
    assert attributes["first_appeared_in_video_game"] is True
    assert attributes["first_appeared_in_book"] is False
    assert attributes["has_superpowers_or_magic"] is True
    assert attributes["from_japan"] is True
    assert attributes["origin_1995_or_later"] is True


@pytest.mark.parametrize("species, expected_human, expected_animal", [
    ("human", True, False),
    ("animal", False, True),
    ("other", False, False),
    ("unknown", None, None),
])
def test_species_maps_to_human_and_animal(species, expected_human, expected_animal):
    attributes = attributes_for(make_fictional_row(species=species))

    assert attributes["is_human"] is expected_human
    assert attributes["is_animal"] is expected_animal


@pytest.mark.parametrize("year, feature, expected", [
    ("1499", "origin_before_1500", True),
    ("1500", "origin_before_1500", False),
    ("1969", "origin_1970_or_later", False),
    ("1970", "origin_1970_or_later", True),
    ("-551", "origin_before_1500", True),
])
def test_year_thresholds_at_boundaries(year, feature, expected):
    assert attributes_for(make_row(origin_year=year))[feature] is expected


@pytest.mark.parametrize("year, expected", [("-1", True), ("1", False), ("-551", True)])
def test_origin_bce(year, expected):
    assert attributes_for(make_row(origin_year=year))["origin_bce"] is expected


@pytest.mark.parametrize("changes, expected", [
    ({"age_at_death": "39"}, True),
    ({"age_at_death": "40"}, False),
    ({"alive": "yes", "age_at_death": "", "origin_year": "1989"}, False),
])
def test_died_before_age_40_for_real_people(changes, expected):
    assert attributes_for(make_row(**changes))["died_before_age_40"] is expected


def test_died_before_age_40_is_unknown_for_fictional_characters():
    assert attributes_for(make_fictional_row())["died_before_age_40"] is None


def test_football_domain_sets_football_attribute():
    attributes = attributes_for(make_row(domains="sport;football"))

    assert attributes["known_for_football"] is True
    assert attributes["known_for_sport"] is True


@pytest.mark.parametrize("country", ["China", "Hong Kong", "Taiwan"])
def test_chinese_speaking_world_covers_listed_places(country):
    assert attributes_for(make_row(region="asia", country=country))["from_chinese_speaking_world"] is True


def test_overrides_replace_derived_values():
    row = make_row(overrides="from_uk=unknown;known_for_music=true")

    attributes = attributes_for(row)

    assert attributes["from_uk"] is None
    assert attributes["known_for_music"] is True


def test_derivation_is_repeatable_and_does_not_mutate_entry():
    entry = parse_roster_row(make_row(overrides="from_uk=unknown"), line_number=2)

    first = derive_attributes(entry)
    first["from_uk"] = True
    second = derive_attributes(entry)

    assert second["from_uk"] is None


# --- validation -----------------------------------------------------------

@pytest.mark.parametrize("changes, message", [
    ({"gender": "robot"}, "gender"),
    ({"species": "plant"}, "species"),
    ({"kind": "myth"}, "kind"),
    ({"region": "antarctica"}, "region"),
    ({"domains": "science;cooking"}, "cooking"),
    ({"tags": "famous"}, "famous"),
    ({"origin_year": "about 1800"}, "origin_year"),
    ({"wikidata_id": "7259"}, "wikidata_id"),
    ({"name": "  "}, "name"),
    ({"alive": "na"}, "alive"),
    ({"age_at_death": "-3"}, "age_at_death"),
    ({"alive": "yes"}, "age_at_death"),
    ({"media": "book"}, "media"),
    ({"overrides": "not_a_column=true"}, "not_a_column"),
    ({"overrides": "from_uk=maybe"}, "maybe"),
    ({"overrides": "from_uk"}, "from_uk"),
])
def test_invalid_real_rows_are_rejected_with_line_number(changes, message):
    with pytest.raises(RosterError) as error:
        parse_roster_row(make_row(**changes), line_number=7)

    assert "line 7" in str(error.value)
    assert message in str(error.value)


@pytest.mark.parametrize("changes, message", [
    ({"media": ""}, "media"),
    ({"media": "radio"}, "media"),
    ({"alive": "yes"}, "alive"),
    ({"age_at_death": "30"}, "age_at_death"),
])
def test_invalid_fictional_rows_are_rejected(changes, message):
    with pytest.raises(RosterError, match=message):
        parse_roster_row(make_fictional_row(**changes), line_number=3)


def test_duplicate_names_are_rejected():
    entries = [parse_roster_row(make_row(), 2), parse_roster_row(make_row(wikidata_id="Q1"), 3)]

    with pytest.raises(RosterError, match="Duplicate name"):
        check_unique(entries)


def test_duplicate_wikidata_ids_are_rejected():
    entries = [parse_roster_row(make_row(), 2), parse_roster_row(make_row(name="Other"), 3)]

    with pytest.raises(RosterError, match="Duplicate Wikidata ID"):
        check_unique(entries)


# --- output formatting ----------------------------------------------------

def test_format_row_writes_true_false_unknown_and_source():
    entry = parse_roster_row(make_fictional_row(), line_number=2)

    row = format_row(entry, sitelinks=8)

    assert list(row) == ["name"] + list(CORE_QUESTIONS) + ["sitelinks", "source"]
    assert row["name"] == "Pikachu"
    assert row["is_fictional"] == "true"
    assert row["is_human"] == "false"
    assert row["is_alive"] == "unknown"
    assert "Q9351" in row["source"]


# --- roster file ----------------------------------------------------------

def write_roster(path, rows, columns=None):
    columns = columns or list(make_row())
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_load_roster_reads_valid_file(tmp_path):
    path = write_roster(tmp_path / "roster.csv", [make_row(), make_fictional_row()])

    entries = load_roster(path)

    assert [entry.name for entry in entries] == ["Ada Lovelace", "Pikachu"]


def test_load_roster_rejects_missing_column(tmp_path):
    columns = [c for c in make_row() if c != "species"]
    path = write_roster(tmp_path / "roster.csv", [make_row()], columns=columns)

    with pytest.raises(RosterError, match="species"):
        load_roster(path)


def test_load_roster_rejects_empty_file(tmp_path):
    path = write_roster(tmp_path / "roster.csv", [])

    with pytest.raises(RosterError, match="no rows"):
        load_roster(path)


def test_load_roster_reports_line_number_of_bad_row(tmp_path):
    path = write_roster(tmp_path / "roster.csv", [make_row(), make_fictional_row(gender="robot")])

    with pytest.raises(RosterError, match="line 3"):
        load_roster(path)


# --- review follow-ups: unknown must never become false ---------------------

@pytest.mark.parametrize("changes, message", [
    ({"country": "United Kingdom"}, "United Kingdom"),
    ({"country": "Japan"}, "region"),
    ({"domains": ""}, "domains"),
    ({"tags": "villain"}, "villain"),
    ({"tags": "powers"}, "powers"),
    ({"alive": "yes", "age_at_death": "", "origin_year": "1500"}, "alive"),
    ({"origin_year": "0"}, "origin_year"),
    ({"age_at_death": "²"}, "age_at_death"),
])
def test_review_validation_rules_for_real_rows(changes, message):
    with pytest.raises(RosterError, match=message):
        parse_roster_row(make_row(**changes), line_number=4)


def test_short_row_reports_line_number_instead_of_crashing():
    row = {key: value for key, value in make_row().items() if key in ("name", "wikidata_id")}
    row.update({key: None for key in make_row() if key not in row})

    with pytest.raises(RosterError, match="line 5"):
        parse_roster_row(row, line_number=5)


def test_row_with_extra_cells_is_rejected():
    row = {**make_row(), None: ["unexpected"]}

    with pytest.raises(RosterError, match="extra"):
        parse_roster_row(row, line_number=6)


def test_nobel_tag_is_rejected_for_fictional_characters():
    with pytest.raises(RosterError, match="nobel"):
        parse_roster_row(make_fictional_row(tags="nobel"), line_number=2)


def test_duplicate_override_keys_are_rejected():
    with pytest.raises(RosterError, match="more than once"):
        parse_roster_row(make_row(overrides="from_uk=unknown;from_uk=true"), line_number=2)


def test_override_that_changes_nothing_is_rejected():
    entry = parse_roster_row(make_row(overrides="from_uk=true"), line_number=2)

    with pytest.raises(RosterError, match="no effect"):
        derive_attributes(entry)


def test_override_that_contradicts_other_attributes_is_rejected():
    entry = parse_roster_row(make_row(overrides="origin_before_1500=true"), line_number=2)

    with pytest.raises(RosterError, match="origin_before_1800"):
        derive_attributes(entry)


def test_robot_tag_sets_robot_attribute():
    assert attributes_for(make_fictional_row(tags="robot"))["is_robot_or_machine"] is True
    assert attributes_for(make_fictional_row())["is_robot_or_machine"] is False


def test_load_roster_accepts_utf8_bom(tmp_path):
    path = write_roster(tmp_path / "roster.csv", [make_row()])
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())

    assert load_roster(path)[0].name == "Ada Lovelace"



# --- unknown values allowed for generated rows ------------------------------

def test_empty_origin_year_makes_every_year_attribute_unknown():
    attributes = attributes_for(make_row(origin_year=""))

    assert all(attributes[f] is None for f in ("origin_bce", "origin_before_1900", "origin_1995_or_later"))


def test_unknown_age_at_death_makes_died_young_unknown():
    assert attributes_for(make_row(age_at_death=""))["died_before_age_40"] is None


def test_unknown_living_status():
    attributes = attributes_for(make_row(alive="unknown", age_at_death=""))

    assert attributes["is_alive"] is None
    assert attributes["died_before_age_40"] is None


def test_several_regions_and_countries_are_debatable():
    attributes = attributes_for(make_row(region="europe;north_america", country="UK;USA"))

    assert attributes["from_europe"] is None
    assert attributes["from_north_america"] is None
    assert attributes["from_asia"] is False
    assert attributes["from_uk"] is None
    assert attributes["from_usa"] is None
    assert attributes["from_japan"] is False


def test_unknown_country_is_unknown_only_for_countries_in_the_region():
    attributes = attributes_for(make_row(country=""))

    assert attributes["from_uk"] is None          # the UK is in Europe
    assert attributes["from_usa"] is False        # the USA is not
    assert attributes["from_japan"] is False


def test_unknown_region_makes_every_place_attribute_unknown():
    attributes = attributes_for(make_row(region="unknown", country=""))

    assert attributes["from_europe"] is None
    assert attributes["from_usa"] is None


def test_unknown_region_with_a_country_is_rejected():
    with pytest.raises(RosterError, match="region"):
        parse_roster_row(make_row(region="unknown", country="UK"), line_number=2)


def test_unknown_media_makes_every_media_attribute_unknown():
    attributes = attributes_for(make_fictional_row(media="unknown"))

    assert attributes["first_appeared_in_book"] is None
    assert attributes["first_appeared_in_video_game"] is None


def test_new_domains_film_and_exploration():
    attributes = attributes_for(make_row(domains="film;exploration"))

    assert attributes["known_for_filmmaking"] is True
    assert attributes["known_for_exploration"] is True


def test_generated_rows_are_labelled_in_source():
    entry = parse_roster_row(make_row(), line_number=2, is_generated=True)

    assert "generated automatically" in format_row(entry, sitelinks=5)["source"]


def test_load_countries_rejects_bad_rows(tmp_path):
    from roster import load_countries

    path = tmp_path / "countries.csv"
    path.write_text("country,region,wikidata_ids,notes\nAtlantis,ocean,Q1,\n", encoding="utf-8")

    with pytest.raises(RosterError, match="region"):
        load_countries(path)



def test_countries_wholly_inside_a_flag_group_count_as_yes():
    attributes = attributes_for(make_row(region="asia", country="China;Taiwan"))

    assert attributes["from_chinese_speaking_world"] is True
