import dataset
from probability import popularity_prior
from simulate import make_sheets
from decision_tree import build_tree, save_dst


class  Train:
    CHARACTERS_PATH = "../dataset/characters.csv"
    QUESTIONS_PATH = "../dataset/questions.csv"
    @staticmethod
    def train(characters, total, minimum, seed, max_depth, min_sheets):
        """Build the decision tree from the characters."""
        prior = popularity_prior(characters)
        sheet = make_sheets(characters, prior, total, minimum, seed)
        attributes = list(characters[-1]["attributes"].keys())
        dst_model = build_tree(sheet,attributes,max_depth, min_sheets,first_question="is_fictional")

        return dst_model

def main():
    characters = dataset.load_characters(Train.CHARACTERS_PATH)
    dst_model =Train.train(characters, total=50000, minimum=20, seed=1, max_depth=10, min_sheets=5)
    save_dst(dst_model,'../model/tree.json')
    print("model saved")

if __name__ == "__main__":
    main()