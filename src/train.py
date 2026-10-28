"""Train the decision tree and save it to model/tree.json (run from src/: python3 train.py).

Steps: popularity prior -> simulated answer sheets -> ID3 tree -> JSON file.
It takes about a minute; the game only needs the saved tree.
"""
from dataset import Dataset
from probability import Probability
from simulate import make_sheets
from decision_tree import DecisionTree


class  Train:
    CHARACTERS_PATH = "../dataset/characters.csv"
    QUESTIONS_PATH = "../dataset/questions.csv"
    @staticmethod
    def train(characters, total, minimum, seed, max_depth, min_sheets):
        """Build the decision tree from the characters."""
        prior = Probability.popularity_prior(characters)
        sheet = make_sheets(characters, prior, total, minimum, seed)
        attributes = list(characters[-1]["attributes"].keys())
        dst_model = DecisionTree.build_tree(sheet,attributes,max_depth, min_sheets,first_question="is_fictional")

        return dst_model

def main():
    # 50,000 sheets in total, at least 20 per character; the tree may ask 10 questions deep
    characters = Dataset.load_characters(Train.CHARACTERS_PATH)
    dst_model =Train.train(characters, total=50000, minimum=20, seed=1, max_depth=10, min_sheets=5)
    DecisionTree.save_dst(dst_model,'../model/tree.json')
    print("model saved")

if __name__ == "__main__":
    main()