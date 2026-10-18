"""Data-quality report for data/characters.csv.

Usage:
    python scripts/analyse_data.py

Prints:
1. per-attribute true/false/unknown counts (how useful each question can be);
2. characters with many unknown values;
3. pairs of characters that no attribute can tell apart, and pairs separated
   by only one attribute (fragile if the player answers that one wrongly),
   for the core questions and for core + question pool;
4. a rough feasibility check: a greedy information-gain split over the whole
   roster, reporting how many questions each character needs in the worst
   case. This is a data diagnostic only, not the game's question strategy;
5. the popularity (sitelinks) distribution.
"""

import math
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from data_loader import load_characters  # noqa: E402
from questions import CORE_QUESTIONS, FIRST_QUESTION, QUESTIONS  # noqa: E402

QUESTION_LIMIT = 10
HIGH_UNKNOWN_COUNT = 5


def attribute_counts(characters, attribute):
    values = [c.attributes[attribute] for c in characters]
    return values.count(True), values.count(False), values.count(None)


def print_attribute_table(characters, attributes):
    print("1. Attribute distribution (n=%d)" % len(characters))
    print("   %-34s %5s %6s %8s" % ("attribute", "true", "false", "unknown"))
    for attribute in attributes:
        true_count, false_count, unknown_count = attribute_counts(characters, attribute)
        print("   %-34s %5d %6d %8d" % (attribute, true_count, false_count, unknown_count))


def print_unknown_heavy(characters):
    print("\n2. Characters with >= %d unknown values" % HIGH_UNKNOWN_COUNT)
    heavy = [(sum(v is None for v in c.attributes.values()), c.name) for c in characters]
    heavy = sorted((item for item in heavy if item[0] >= HIGH_UNKNOWN_COUNT), reverse=True)
    for count, name in heavy:
        print("   %-24s %d unknown" % (name, count))
    if not heavy:
        print("   none")


def separating_attributes(first, second, attributes):
    """Attributes where both values are known and differ."""
    return [
        a for a in attributes
        if first.attributes[a] is not None
        and second.attributes[a] is not None
        and first.attributes[a] != second.attributes[a]
    ]


def print_pair_report(characters, attributes, label, list_pairs=True):
    print("\n3. Pairs that are hard to tell apart (%s)" % label)
    inseparable, fragile = [], []
    for first, second in combinations(characters, 2):
        separators = separating_attributes(first, second, attributes)
        if not separators:
            inseparable.append((first.name, second.name))
        elif len(separators) == 1:
            fragile.append((first.name, second.name, separators[0]))
    print("   Inseparable pairs: %d" % len(inseparable))
    for pair in inseparable:
        print("     - %s / %s" % pair)
    print("   Pairs separated by exactly one attribute: %d" % len(fragile))
    if list_pairs:
        for first, second, attribute in fragile:
            print("     - %s / %s (only %s)" % (first, second, attribute))


def entropy(count):
    return math.log2(count) if count > 1 else 0.0


def split(candidates, attribute):
    """Unknown values follow both branches, as a cautious game would do."""
    yes = [c for c in candidates if c.attributes[attribute] is not False]
    no = [c for c in candidates if c.attributes[attribute] is not True]
    return yes, no


def best_attribute(candidates, attributes):
    best, best_gain = None, 0.0
    for attribute in attributes:
        yes, no = split(candidates, attribute)
        if not yes or not no or len(yes) == len(candidates) or len(no) == len(candidates):
            continue
        total = len(yes) + len(no)
        remaining = (len(yes) * entropy(len(yes)) + len(no) * entropy(len(no))) / total
        gain = entropy(len(candidates)) - remaining
        if gain > best_gain:
            best, best_gain = attribute, gain
    return best


def worst_case_depths(candidates, attributes, depth=0, first_question=None):
    """Map each name to the deepest point at which it is still not isolated."""
    if len(candidates) == 1 or depth == QUESTION_LIMIT:
        return {c.name: (depth, len(candidates)) for c in candidates}
    attribute = first_question or best_attribute(candidates, attributes)
    if attribute is None:
        return {c.name: (depth, len(candidates)) for c in candidates}
    remaining = [a for a in attributes if a != attribute]
    results = {}
    for branch in split(candidates, attribute):
        for name, outcome in worst_case_depths(branch, remaining, depth + 1).items():
            results[name] = max(results.get(name, outcome), outcome)
    return results


def print_feasibility(characters, attributes, label, first_question=None):
    opening = "first question fixed to %s" % first_question if first_question else "no fixed first question"
    print("\n4. Greedy information-gain feasibility check (%s; limit %d questions, %s)" % (
        label, QUESTION_LIMIT, opening))
    outcomes = worst_case_depths(list(characters), list(attributes), first_question=first_question)
    isolated = {n: d for n, (d, size) in outcomes.items() if size == 1}
    unresolved = {n: (d, size) for n, (d, size) in outcomes.items() if size > 1}
    depths = list(isolated.values())
    print("   Isolated within limit: %d / %d" % (len(isolated), len(outcomes)))
    if depths:
        print("   Questions needed (worst path): min %d, mean %.2f, max %d" % (
            min(depths), sum(depths) / len(depths), max(depths)))
    for name, (depth, size) in sorted(unresolved.items()):
        print("     - %s still shares a leaf with %d candidates after %d questions" % (name, size - 1, depth))


def print_popularity(characters):
    print("\n5. Popularity (Wikipedia/Wikimedia sitelinks)")
    if any(c.sitelinks is None for c in characters):
        print("   not available: the dataset has no sitelinks column")
        return
    ranked = sorted(characters, key=lambda c: c.sitelinks, reverse=True)
    links = [c.sitelinks for c in ranked]
    print("   min %d, median %d, max %d" % (links[-1], links[len(links) // 2], links[0]))
    print("   most popular:  " + ", ".join("%s (%d)" % (c.name, c.sitelinks) for c in ranked[:5]))
    print("   least popular: " + ", ".join("%s (%d)" % (c.name, c.sitelinks) for c in ranked[-5:]))
    weights = [math.sqrt(n) for n in links]
    print("   with weight sqrt(sitelinks): top-10 share %.0f%%, uniform share %.0f%%" % (
        100 * sum(weights[:10]) / sum(weights), 100 * 10 / len(weights)))


def main():
    characters = load_characters()
    core = list(CORE_QUESTIONS)
    everything = list(QUESTIONS)
    print_attribute_table(characters, everything)
    print_unknown_heavy(characters)
    print_pair_report(characters, core, "%d core questions" % len(core), list_pairs=False)
    print_pair_report(characters, everything, "%d core + pool questions" % len(everything))
    print_feasibility(characters, core, "core", first_question=FIRST_QUESTION)
    print_feasibility(characters, everything, "core + pool", first_question=FIRST_QUESTION)
    print_popularity(characters)
    return 0


if __name__ == "__main__":
    sys.exit(main())
