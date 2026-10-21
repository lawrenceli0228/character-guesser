"""Simulated answer sheets: how players with a character in mind answer each question."""
import random

# Probability of each answer for each true attribute value.
ANSWER_MODEL = {
    True: {"yes": 0.85, "no": 0.05, "unknown": 0.10},
    False: {"yes": 0.05, "no": 0.85, "unknown": 0.10},
    None: {"yes": 0.30, "no": 0.30, "unknown": 0.40},
}


def simulate_answer(value, rng):
    """Draw "yes", "no" or "unknown" for an attribute whose true value is value."""

    answer = ANSWER_MODEL[value]
    draw = rng.random()
    if draw < answer["yes"]:
        return "yes"
    elif draw < answer["yes"] + answer["no"]:
        return "no"
    else:
        return "unknown"

def make_sheet(character, rng):
    """One simulated answer sheet: (attribute -> answer, character name)."""
    answer_sheet = {}
    for key,value in character["attributes"].items():
        answer_sheet[key] = simulate_answer(value, rng)

    return answer_sheet, character["name"]

def sheet_counts(prior, total, minimum):
    """Number of answer sheets per character: total * probability, rounded, at least minimum."""
    counts = {}
    for key,value in prior.items():
        counts[key] = max(minimum,round(total * value))
    return counts

def make_sheets(characters, prior, total, minimum, seed):
    """All answer sheets: each character gets sheet_counts(...) sheets, drawn with one seeded rng."""
    rng = random.Random(seed)
    counts = sheet_counts(prior, total, minimum)
    sheets = []
    for character in characters:
        for _ in range(counts[character["name"]]):
            sheets.append(make_sheet(character, rng))
    return sheets

