from decision_tree import load_dst
from probability import popularity_prior
from simulate import answer_model
import dataset


class Game:
    accept_input = {
            "y": "yes", "yes": "yes",
            "n": "no", "no": "no",
            "u": "unknown",
            "unknown": "unknown",
            "?": "unknown",
            "not sure": "unknown",
            "dont know": "unknown",
        }
    @staticmethod
    def play():
        tree = load_dst("../model/tree.json")
        questions = dataset.load_questions("../dataset/questions.csv")
        characters = dataset.load_characters("../dataset/characters.csv")
        prior = popularity_prior(characters)
        while True:
            Game.play_round(tree, questions, characters, prior)
            if Game.ask("Play again?") != "yes":
                break
        print("Thanks for playing!")

    @staticmethod
    def parse_user_input(user_in):
        temp = user_in.strip().lower()
        key_check = Game.accept_input.get(temp)
        return key_check

    @staticmethod
    def next_quest(node, answer):
        """The child of node that the player's answer leads to."""
        return node["branches"][answer]

    @staticmethod
    def guess_who(node, k):
        """The k most likely names at this node, as (name, probability), most likely first."""
        counts = node["counts"]
        #  {"Einstein": 4, "Curie": 4}
        sum_count = sum(counts.values())
        sorted_dict = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        res = []
        for key, value in sorted_dict:
            prob = value / sum_count
            res.append((key,prob))
        return res[:k]

    @staticmethod
    def score_guesses(characters, prior, asked, k):
        """The k most likely characters given ALL answers so far, as (name, probability).

        score = prior x P(answer | true value) for every question asked, so one wrong
        answer lowers a character's score instead of ruling them out like a tree branch does.
        """
        scores = {}
        for character in characters:
            score = prior[character["name"]]
            for question, answer in asked:
                value = character["attributes"][question]
                score *= answer_model(question)[value][answer]
            scores[character["name"]] = score
        # guess_who already normalises, sorts and keeps the top k
        return Game.guess_who({"counts": scores}, k)

    @staticmethod
    def ask(text):
        while True:
            user_in = input(text + " (y/n/?) ")
            answer = Game.parse_user_input(user_in)
            if answer is not None:
                return answer
            print("Invalid input, please try again must yes,no,unknown")

    @staticmethod
    def play_round(tree, questions, characters, prior):
        """One game: the tree picks the questions, then all answers pick the top 3 guesses."""
        node = tree
        count = 0
        asked = []
        while not node["leaf"]:
            count += 1
            question = questions.get(node["question"])
            answer = Game.ask(f"Q{count}: {question}")
            asked.append((node["question"], answer))
            node = Game.next_quest(node, answer)
        ge_names = Game.score_guesses(characters, prior, asked, 3)

        for name, prob in ge_names:
            if Game.ask(f"Is it {name}?") == "yes":
                print(f"I got it in {count} questions!")
                return
        print("You win! I couldn't guess who it was.")




