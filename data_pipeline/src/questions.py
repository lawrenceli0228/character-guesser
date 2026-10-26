"""Player-facing Yes/No question for every attribute column in characters.csv.

- CORE_QUESTIONS: the 56 hand-designed questions below.
- POOL_QUESTIONS: extra questions generated from Wikidata and reviewed by
  hand, loaded from raw/question_pool.csv.
- QUESTIONS: both together, in the column order of the generated dataset.

Column names are the stable data format; the wording can be revised without
touching the data.

Conventions used when the data was encoded (see docs/DATA.md):
- "Origin" means birth year for real people and year of first appearance
  for fictional characters.
- Places for fictional characters refer to the country where the original
  work was created.
"""

import csv

from question_pool import POOL_COLUMNS, POOL_PATH

# Always asked first, before information gain takes over. It splits the
# roster into real people and fictional characters (350 / 150), is known for
# every entry, and is the most natural opening for players.
FIRST_QUESTION = "is_fictional"


def _place(place):
    """A "where from" question that says what it means for fictional characters."""
    return "Is this person from %s? (For a fictional character: was the original story created there?)" % place


CORE_QUESTIONS = {
    # What kind of entity
    "is_fictional": "Is this a fictional character (not a real person)?",
    "is_male": "Is this person or character male?",
    "is_human": "Is this a human being?",
    "is_animal": "Is this an animal, or an animal-like character (such as a talking mouse or bear)?",
    "is_alive": "Is this person still alive today?",
    "died_before_age_40": "Did this person die before the age of 40?",
    # When
    "origin_bce": "Was this person born (or this character created) before the Common Era (BCE)?",
    "origin_before_1500": "Was this person born (or this character created) before the year 1500?",
    "origin_before_1800": "Was this person born (or this character created) before 1800?",
    "origin_before_1900": "Was this person born (or this character created) before 1900?",
    "origin_before_1950": "Was this person born (or this character created) before 1950?",
    "origin_1960_or_later": "Was this person born (or this character created) in 1960 or later?",
    "origin_1970_or_later": "Was this person born (or this character created) in 1970 or later?",
    "origin_1980_or_later": "Was this person born (or this character created) in 1980 or later?",
    "origin_1995_or_later": "Was this person born (or this character created) in 1995 or later?",
    # Where (spelled out because players otherwise answer for the story world, e.g. Darth Vader)
    "from_asia": _place("Asia"),
    "from_europe": _place("Europe"),
    "from_north_america": _place("North America, including Mexico, Central America and the Caribbean"),
    "from_south_america": _place("South America"),
    "from_africa": _place("Africa"),
    "from_oceania": _place("Australia or Oceania"),
    "from_chinese_speaking_world": _place("the Chinese-speaking world (mainland China, Hong Kong or Taiwan)"),
    "from_usa": _place("the United States"),
    "from_uk": _place("the United Kingdom"),
    "from_japan": _place("Japan"),
    "from_france": _place("France"),
    "from_germany": _place("Germany"),
    "from_italy": _place("Italy"),
    "from_spain": _place("Spain"),
    "from_russia": _place("Russia (including the Soviet Union)"),
    "from_india": _place("India"),
    "from_canada": _place("Canada"),
    "from_brazil": _place("Brazil"),
    # What they are known for
    "known_for_science_or_medicine": "Is this person or character known for science or medicine?",
    "known_for_technology": "Is this person or character known for technology, computing or inventions?",
    "known_for_politics_or_leadership": "Is this person or character known for politics or leading a nation?",
    "known_for_sport": "Is this person or character known for sport?",
    "known_for_football": "Is this person known for football (soccer)?",
    "known_for_music": "Is this person or character known for music?",
    "known_for_acting_or_tv": "Is this person known as an actor (in films or TV shows)?",
    "known_for_filmmaking": "Is this person known for directing or producing films?",
    "known_for_writing": "Is this person known for writing, poetry or philosophy?",
    "known_for_visual_art": "Is this person known for painting or other visual art?",
    "known_for_business": "Is this person known for business or founding a company?",
    "known_for_exploration": "Is this person known for exploration, such as voyages of discovery or space travel?",
    # Distinguishing traits
    "won_nobel_prize": "Has this person won a Nobel Prize?",
    "has_ruled_a_country": "Has this person or character ruled a country or kingdom (as a monarch, president, prime minister or dictator)?",
    "is_monarch_or_royal": "Is this person or character a monarch or a member of a royal family?",
    "has_superpowers_or_magic": "Does this character have superpowers or magical abilities?",
    "is_villain": "Is this a fictional villain?",
    "is_robot_or_machine": "Is this character a robot or machine?",
    # Original medium (false for real people)
    "first_appeared_in_book": "Is this a fictional character who first appeared in a book?",
    "first_appeared_in_comic": "Is this a fictional character who first appeared in a comic or manga?",
    "first_appeared_in_animation": "Is this a fictional character who first appeared in an animated film or cartoon?",
    "first_appeared_in_video_game": "Is this a fictional character who first appeared in a video game?",
    "first_appeared_in_live_action": "Is this a fictional character who first appeared in a live-action film or TV show?",
}


def load_pool_questions(path=POOL_PATH):
    """Read attribute -> question text from the reviewed question pool.

    Full validation of the pool (sources, name lists) happens in
    question_pool.load_pool when the dataset is built.
    """
    try:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            missing = [c for c in POOL_COLUMNS if c not in (reader.fieldnames or [])]
            if missing:
                raise ValueError("%s is missing column(s): %s" % (path, missing))
            pool = _read_pool_questions(reader)
    except FileNotFoundError as error:
        raise ValueError("question pool not found at %s; the game needs this file" % path) from error
    if not pool:
        raise ValueError("%s contains no questions" % path)
    return pool


def _read_pool_questions(reader):
    pool = {}
    for row in reader:
        attribute = (row.get("attribute") or "").strip()
        text = (row.get("question") or "").strip()
        if attribute in CORE_QUESTIONS:
            raise ValueError("pool attribute %r clashes with a core question" % attribute)
        if attribute in pool:
            raise ValueError("pool attribute %r appears more than once" % attribute)
        if not attribute or not text:
            raise ValueError("pool row %r needs both an attribute and question text" % attribute)
        pool[attribute] = text
    return pool


POOL_QUESTIONS = load_pool_questions()
QUESTIONS = {**CORE_QUESTIONS, **POOL_QUESTIONS}
