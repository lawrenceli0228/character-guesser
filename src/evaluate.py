"""How often the game guesses right, played by simulated players (step 6).

    cd src
    python3 evaluate.py          # all 500 characters, seed 9001 (about 4 minutes)
    python3 evaluate.py 2027     # the same with another random seed

For every character there is one honest game (every answer taken from the data,
"not sure" where the data is unknown) and 3 noisy games (answers drawn from the same
model as the training sheets: 85% right, 5% wrong, 10% not sure; see simulate.py).
The real Game.play_round runs unchanged: only input() is replaced by the player.
These players make random mistakes, not the shared misconceptions real players have,
so real accuracy can be lower.
"""
import builtins
import contextlib
import io
import random
import re
import sys

from dataset import Dataset
from decision_tree import DecisionTree
from game import Game
from probability import Probability
from simulate import answer_model


class Evaluate:
    NOISY_GAMES = 3
    TRUTH = {True: "yes", False: "no", None: "unknown"}
    SHORT = {"yes": "y", "no": "n", "unknown": "?"}

    @staticmethod
    def answer(character, question, rng):
        """The honest answer when rng is None, otherwise one drawn from the answer model."""
        value = character["attributes"][question]
        if rng is None:
            return Evaluate.TRUTH[value]
        chances = answer_model(question)[value]
        return rng.choices(list(chances), weights=list(chances.values()))[0]

    @staticmethod
    def play(character, rng, tree, questions, characters, prior, parents):
        """One round of the real game for this character; returns the names shown, best guess first."""
        keys = {}
        for key, text in questions.items():
            keys[text] = key

        def player(prompt=""):
            if prompt.endswith(" (y/n/?) "):                      # "Q3: <question> (y/n/?) "
                text = prompt.split(": ", 1)[1][:-len(" (y/n/?) ")]
                return Evaluate.SHORT[Evaluate.answer(character, keys[text], rng)]
            if prompt.startswith("Is it "):
                return "n"                                        # say no, so every round ends the same way
            return ""                                             # "Who were you thinking of?" -> skip

        real_input = builtins.input
        builtins.input = player
        try:
            with contextlib.redirect_stdout(io.StringIO()) as screen:
                Game.play_round(tree, questions, characters, prior, parents)
        finally:
            builtins.input = real_input
        text = screen.getvalue()
        names = [re.search(r"My answer: (.+)", text).group(1)]
        names += re.findall(r"^  \d+\. (.+) \(", text, re.M)
        return names

    @staticmethod
    def run(players, seed, tree, questions, characters, prior, parents):
        """Counts over the given characters: honest first guesses, noisy first guesses and noisy top 3."""
        rng = random.Random(seed)
        res = {"honest_first": 0, "honest_games": 0, "noisy_first": 0, "noisy_top3": 0, "noisy_games": 0}
        for character in players:
            name = character["name"]
            shown = Evaluate.play(character, None, tree, questions, characters, prior, parents)
            res["honest_games"] += 1
            if shown[0] == name:
                res["honest_first"] += 1
            for _ in range(Evaluate.NOISY_GAMES):
                shown = Evaluate.play(character, rng, tree, questions, characters, prior, parents)
                res["noisy_games"] += 1
                if shown[0] == name:
                    res["noisy_first"] += 1
                if name in shown:
                    res["noisy_top3"] += 1
        return res


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 9001
    tree = DecisionTree.load_dst("../model/tree.json")
    questions = Dataset.load_questions("../dataset/questions.csv")
    parents = Dataset.load_parents("../dataset/questions.csv")
    characters = Dataset.load_characters("../dataset/characters.csv")
    prior = Probability.popularity_prior(characters)
    res = Evaluate.run(characters, seed, tree, questions, characters, prior, parents)
    print(f"seed {seed}, {len(characters)} characters")
    print(f"honest players: first guess right {res['honest_first']}/{res['honest_games']} "
          f"({res['honest_first'] / res['honest_games']:.1%})")
    print(f"noisy players:  first guess right {res['noisy_first']}/{res['noisy_games']} "
          f"({res['noisy_first'] / res['noisy_games']:.1%}), "
          f"in the top 3 {res['noisy_top3']}/{res['noisy_games']} ({res['noisy_top3'] / res['noisy_games']:.1%})")


if __name__ == "__main__":
    main()
