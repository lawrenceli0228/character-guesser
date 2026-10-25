"""Probabilities over characters: a dict name -> probability that sums to 1."""
import math
import statistics


def normalise(weights):
    """Return a NEW dict with the same keys, scaled so the values sum to 1."""
    result = {}
    sum_weights = sum(weights.values())
    if sum_weights <= 0:
        raise ValueError("sum_weights must be greater than 0")
    for name, weight in weights.items():
       result[name] = weight / sum_weights

    return result

def group_medians(characters):
    """Median sitelinks of real people (key False) and fictional characters (key True)."""
    real_char = []
    fictional_char = []
    for character in characters:
        if character["attributes"]["is_fictional"] is True:
            fictional_char.append(character["sitelinks"])
        else:
            real_char.append(character["sitelinks"])
    return {False: statistics.median(real_char), True: statistics.median(fictional_char)}


def popularity_prior(characters):
    """Starting probability of each character: sqrt(sitelinks / median of its group), normalised."""
    medians = group_medians(characters)
    weights = {}
    for character in characters:
        if character["attributes"]["is_fictional"] is True:
            weights[character["name"]] = math.sqrt(character["sitelinks"] / medians[True])
        else:
            weights[character["name"]] = math.sqrt(character["sitelinks"] / medians[False])
    return normalise(weights)