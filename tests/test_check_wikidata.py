import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_wikidata import check_age_at_death, exact_age, year_of  # noqa: E402


@pytest.mark.parametrize("timestamp, expected", [
    ("1879-03-14T00:00:00Z", 1879),
    ("+1879-03-14T00:00:00Z", 1879),
    ("-0099-07-12T00:00:00Z", -100),  # XSD year -99 is 100 BCE
    ("0000-01-01T00:00:00Z", -1),     # XSD year 0 is 1 BCE
])
def test_year_of_converts_xsd_years_to_bce_numbering(timestamp, expected):
    assert year_of(timestamp) == expected


def test_exact_age_counts_birthday_not_yet_reached():
    assert exact_age("1940-10-09T00:00:00Z", "1980-12-08T00:00:00Z") == 40
    assert exact_age("1912-06-23T00:00:00Z", "1954-06-07T00:00:00Z") == 41


def test_check_age_at_death_flags_disagreement():
    entity = {"births": ["1940-10-09T00:00:00Z"], "deaths": ["1980-12-08T00:00:00Z"]}

    assert check_age_at_death({"age_at_death": "40"}, entity) == []
    assert check_age_at_death({"age_at_death": "45"}, entity) != []


def test_check_age_at_death_skips_living_people():
    assert check_age_at_death({"age_at_death": ""}, {"births": ["1989-12-13T00:00:00Z"], "deaths": []}) == []
