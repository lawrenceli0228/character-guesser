"""ID3 decision tree: entropy, information gain and recursive tree building."""
import math
from collections import Counter
import json

from simulate import answer_model

class DecisionTree:
    @staticmethod
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
    @staticmethod
    def entropy_expect(probs):
        """Entropy of a list of probabilities that sum to 1 (the same formula, on weights instead of names)."""
        res = 0
        for pron in probs:
            if pron > 0:
                res -= pron * math.log2(pron)
        return res

    @staticmethod
    def expected_entropy(candidates, attributes, question):
        """Uncertainty left among the candidates after asking question, averaged over the answers."""
        model = answer_model(question)
        result = 0
        for answer in ("yes", "no", "unknown"):
            # 1. weights = 每个候选人的 概率 × model[真实值][answer]
            # 2. total = sum(weights)
            # 3. 如果 total > 0：算 weights 归一化后的熵
            # 4. result += total × 熵
            weights = []
            weights_nor = []
            for candidate,prob in candidates:
                data_an = attributes[candidate][question]
                real_answer = model[data_an][answer]
                weights.append(prob * real_answer)
            total = sum(weights)
            if total > 0:
                weights_nor = [w/total for w in weights]
            result += total * DecisionTree.entropy_expect(weights_nor)

        return result

    @staticmethod
    def split(sheets, attribute):
        """Group answer sheets by their answer to one question: {"yes": [...], "no": [...], "unknown": [...]}."""
        groups = {"yes": [], "no": [], "unknown": []}
        for sheet in sheets:
            ans = sheet[0]
            answer = ans[attribute]
            groups[answer].append(sheet)
        return groups


    # information_gain(sheets, "is_male")
    @staticmethod
    def information_gain(sheets, attribute):
        """Gain = T1 - T2 (lecture week 5a): entropy before the split minus the weighted entropy after it."""
        t2 = 0
        names = [name for answers, name in sheets]
        t1 = DecisionTree.entropy(names)

        groups = DecisionTree.split(sheets, attribute)
        for group_ans in groups.values():
            w = len(group_ans) / len(sheets)
            names = [name for answers, name in group_ans]
            t2 = t2 + w * DecisionTree.entropy(names)
        res = t1 - t2
        return res

    @staticmethod
    def best_question(sheets, attributes):
        """The attribute with the highest information gain, or None if no question helps."""
        max_info_gain = 0
        chosen_attribute = None
        for attribute in attributes:
            info_gain = DecisionTree.information_gain(sheets, attribute)
            if info_gain > max_info_gain:
                max_info_gain = info_gain
                chosen_attribute = attribute
        return chosen_attribute


    @staticmethod
    def get_names(sheets):
        res = []
        for answers, name in sheets:
            res.append(name)
        return res

    @staticmethod
    def delete_questions(attributes,question):
        results =[]
        for a in attributes:
            if a != question:
                results.append(a)
        return results

    @staticmethod
    def save_dst(model, path):
        """Write the tree to a JSON file."""
        with open(path, "w", encoding="utf-8") as file:
                json.dump(model, file)

    @staticmethod
    def load_dst(path):
        """Read a tree saved by save_tree."""
        with open(path, encoding="utf-8") as file:
                return json.load(file)

    @staticmethod
    def build_tree(sheets, attributes, max_depth, min_sheets, first_question=None):
        """Build an ID3 tree (nested dicts) from answer sheets."""
        counts = dict(Counter(DecisionTree.get_names(sheets)))  #  {"Einstein": 4, "Curie": 4}
        result = {"leaf": True, "counts": counts} # end of the decision tree
        # ending environment
        if len(counts) == 1 or max_depth == 0 or len(sheets) < min_sheets:
            return result

        if first_question:
            question = first_question
        else:
            question = DecisionTree.best_question(sheets, attributes)
        if question is None :
            return result

        remaining = DecisionTree.delete_questions(attributes, question)
        groups = DecisionTree.split(sheets, question)

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
                branches[key] = DecisionTree.build_tree(values, remaining, max_depth -1, min_sheets)

        return {"leaf": False, "counts": counts, "question": question, "branches": branches}
