from decision_tree import DecisionTree
from display import Display
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
    FOCUS_BELOW = 1000
    TOP_N = 20
    MAX_QUESTIONS = 15

    @staticmethod
    def play():
        tree = DecisionTree.load_dst("../model/tree.json")
        questions = dataset.load_questions("../dataset/questions.csv")
        characters = dataset.load_characters("../dataset/characters.csv")
        prior = popularity_prior(characters)
        print(Display.title(Game.MAX_QUESTIONS, len(characters)))
        while True:
            Game.play_round(tree, questions, characters, prior)
            if Game.ask(Display.play_again()) != "yes":
                break
        print(Display.goodbye())

    @staticmethod
    def choose_question(node, characters, prior, asked):
        """The tree's question while its node has plenty of sheets, otherwise the focus question."""
        if node is not None and not node["leaf"] and sum(node["counts"].values()) >= Game.FOCUS_BELOW:
            return node["question"]
        else:
            return Game.focus_question(characters, prior, asked, Game.TOP_N)

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
            user_in = input(Display.prompt(text))
            answer = Game.parse_user_input(user_in)
            if answer is not None:
                return answer
            print(Display.invalid())

    @staticmethod
    def play_round(tree, questions, characters, prior):
        """One game: the tree picks the questions, then all answers pick the top 3 guesses."""


        node = tree
        asked = []
        for count in range(1, Game.MAX_QUESTIONS + 1):     # count = 1, 2, ..., 10
            # 1. question = 用 choose_question 决定这题问什么（返回的是问题名）
            question = Game.choose_question(node, characters, prior, asked)
            question_ = questions.get(question)
            answer = Game.ask(Display.question(count, Game.MAX_QUESTIONS, question_))
            asked.append((question, answer))
            if node is not None and not node["leaf"] and question == node["question"]:
                node = Game.next_quest(node, answer)
            else:
                node = None
        ge_names = Game.score_guesses(characters, prior, asked, 3)
        print(Display.result(ge_names, len(asked)))
        # one guess only: the runners-up are already on screen
        if Game.ask(Display.confirm(ge_names[0][0])) == "yes":
            print(Display.win(len(asked)))
        else:
            print(Display.lose())

    @staticmethod
    def focus_question(characters, prior, asked, top_n):
        """The unasked question that best tells the current top candidates apart."""
        candidates = Game.score_guesses(characters, prior, asked, top_n)
        attributes = {}
        res_mini = float("inf")
        res_mini_name = None
        for character in characters:
            attributes[character["name"]] = character["attributes"]
        ask_done = set(question for question, answer in asked)
        for question in characters[0]["attributes"]:
            if question in ask_done:
                continue
            res = DecisionTree.expected_entropy(candidates,attributes,question)
            if res < res_mini:
                res_mini = res
                res_mini_name = question
        return res_mini_name







