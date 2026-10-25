"""ID3 decision tree: entropy, information gain and recursive tree building."""
import math
from collections import Counter
import json

def entropy(names):
    """Entropy H(S) of a list of names (lecture week 5a): 0 if all the same, higher if mixed."""
    res = 0
    total = len(names)
    if total == 0:
        return 0

    counts = Counter(names)
    for value in counts.values():
        p = value / total
        res -= p * math.log2(p)
    return res

def split(sheets, attribute):
    """Group answer sheets by their answer to one question: {"yes": [...], "no": [...], "unknown": [...]}."""
    groups = {"yes": [], "no": [], "unknown": []}
    for sheet in sheets:
        ans = sheet[0]
        answer = ans[attribute]
        groups[answer].append(sheet)
    return groups


# information_gain(sheets, "is_male")
def information_gain(sheets, attribute):
    """Gain = T1 - T2 (lecture week 5a): entropy before the split minus the weighted entropy after it."""
    t2 = 0
    names = [name for answers, name in sheets]
    t1 = entropy(names)

    groups = split(sheets, attribute)
    for group_ans in groups.values():
        w = len(group_ans) / len(sheets)
        names = [name for answers, name in group_ans]
        t2 = t2 + w * entropy(names)
    res = t1 - t2
    return res

def best_question(sheets, attributes):
    """The attribute with the highest information gain, or None if no question helps."""
    max_info_gain = 0
    chosen_attribute = None
    for attribute in attributes:
        info_gain = information_gain(sheets, attribute)
        if info_gain > max_info_gain:
            max_info_gain = info_gain
            chosen_attribute = attribute
    return chosen_attribute


def get_names(sheets):
    res = []
    for answers, name in sheets:
        res.append(name)
    return res

def delete_questions(attributes,question):
    results =[]
    for a in attributes:
        if a != question:
            results.append(a)
    return results

def save_dst(model, path):
    """Write the tree to a JSON file."""
    with open(path, "w", encoding="utf-8") as file:
            json.dump(model, file)

def load_dst(path):
    """Read a tree saved by save_tree."""
    with open(path, encoding="utf-8") as file:
            return json.load(file)

def build_tree(sheets, attributes, max_depth, min_sheets, first_question=None):
    """Build an ID3 tree (nested dicts) from answer sheets."""
    counts = dict(Counter(get_names(sheets)))  #  {"Einstein": 4, "Curie": 4}
    result = {"leaf": True, "counts": counts} # end of the decision tree
    # ending environment
    if len(counts) == 1 or max_depth == 0 or len(sheets) < min_sheets:
        return result

    if first_question:
        question = first_question
    else:
        question = best_question(sheets, attributes)
    if question is None :
        return result

    remaining = delete_questions(attributes, question)
    groups = split(sheets, question)

    branches = {}
    '''
    groups = {
        "yes": [
            ({"is_male": "yes", "is_fictional": "no"}, "Einstein"),
            ({"is_male": "yes", "is_fictional": "no"}, "Einstein"),
            ({"is_male": "yes", "is_fictional": "no"}, "Obama"),
        ],
        "no": [
            ({"is_male": "no", "is_fictional": "no"}, "Curie"),
        ],
        "unknown": [
            ({"is_male": "unknown", "is_fictional": "no"}, "Einstein"),
        ],
    }
    '''
    for key, values in groups.items():
        if not values:
            branches[key] = result
        else:
            branches[key] = build_tree(values, remaining, max_depth -1, min_sheets)

    return {"leaf": False, "counts": counts, "question": question, "branches": branches}
