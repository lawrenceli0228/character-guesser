"""The game itself: choose each question, read the player's answers, score every
character and make the guess.

Flow of one round (play_round):
  1. the decision tree (model/tree.json) asks the first questions;
  2. once its branch has too few training sheets, focus mode asks the question that
     best splits the 20 most likely characters;
  3. after every answer all 500 characters are scored again with ALL answers;
  4. the game guesses when the leader is far ahead, or after 15 questions.
"""
import difflib

from animation import Animation
from decision_tree import DecisionTree
from display import Display
from probability import Probability
from simulate import answer_model
from dataset import Dataset


class Game:
    # every answer the player may type, mapped to the three answers the game uses
    accept_input = {
            "y": "yes", "yes": "yes",
            "n": "no", "no": "no",
            "u": "unknown",
            "unknown": "unknown",
            "?": "unknown", "？": "unknown",   # full-width ? from a Chinese keyboard
            "not sure": "unknown",
            "dont know": "unknown", "don't know": "unknown", "maybe": "unknown",
        }
    FOCUS_BELOW = 1000        # follow the tree only while its node has at least this many training sheets
    TOP_N = 20                # focus mode compares the 20 most likely characters
    MAX_QUESTIONS = 15        # at most 15 questions per round
    FOLLOW_UP_SLACK = 0.1     # a follow-up of a Yes may leave this many more bits of uncertainty than the best question
    LEAD_RATIO = 20           # guess early once the leader is this many times as likely as the runner-up
    MIN_QUESTIONS = 5         # never guess before this many questions
    # birth / first-appearance years are hard to know, especially for fictional characters
    MAX_YEAR_QUESTIONS = {"yes": 1, "no": 2}   # keyed by the answer to "is this a fictional character?"

    @staticmethod
    def play():
        """Load the data, show the title screen and play rounds until the player stops."""
        tree = DecisionTree.load_dst("../model/tree.json")
        questions = Dataset.load_questions("../dataset/questions.csv")
        parents = Dataset.load_parents("../dataset/questions.csv")
        characters = Dataset.load_characters("../dataset/characters.csv")
        prior = Probability.popularity_prior(characters)
        print(Display.title(Game.MAX_QUESTIONS, len(characters)))
        start = Display.press_start()
        if start:
            input(start)
        score = {"algo": 0, "player": 0}     # rounds won by the game (ALGO) and by the player
        while True:
            Animation.frames(Display.ready(), 0.7)
            if Game.play_round(tree, questions, characters, prior, parents):
                score["algo"] += 1
            else:
                score["player"] += 1
            if Game.ask_yes_no(Display.play_again(score)) != "yes":
                break
        print(Display.goodbye(score))

    @staticmethod
    def choose_question(node, characters, prior, asked, parents=None):
        """The tree's question while its node has plenty of sheets, otherwise the focus question."""
        parents = parents or {}
        if (node is not None and not node["leaf"] and sum(node["counts"].values()) >= Game.FOCUS_BELOW
                and not Game.ruled_out(node["question"], dict(asked), parents)
                and not Game.over_limit(node["question"], dict(asked))):
            return node["question"]
        else:
            return Game.focus_question(characters, prior, asked, Game.TOP_N, parents)

    @staticmethod
    def ruled_out(question, answers, parents):
        """True if the answer already follows from earlier answers, so asking would waste a question.

        A broader question above was answered No (Europe No -> UK is No), or a narrower
        question below was answered Yes (US President Yes -> has ruled a country is Yes).
        Countries are not treated as exclusive: a wrong country answer is the most common
        player mistake, and asking another country is how the game recovers from it.
        """
        parent = parents.get(question)
        while parent is not None:
            if answers.get(parent) == "no":
                return True
            parent = parents.get(parent)
        for other, answer in answers.items():
            if answer != "yes":
                continue
            ancestor = parents.get(other)
            while ancestor is not None:
                if ancestor == question:
                    return True
                ancestor = parents.get(ancestor)
        return False

    @staticmethod
    def over_limit(question, answers):
        """True for a year question once this game has had its share of them (1 for fictional, 2 for real)."""
        if not question.startswith("origin_"):
            return False
        limit = Game.MAX_YEAR_QUESTIONS.get(answers.get("is_fictional"), 2)
        year_asked = 0
        for ans_question in answers:
            if ans_question.startswith("origin_"):
                year_asked += 1
        return year_asked >= limit

    @staticmethod
    def confident(guesses):
        """True once the leader is far ahead of the runner-up, so more questions would not change the guess."""
        if len(guesses) < 2:
            return True
        leader_prob = guesses[0][1]
        second_prob = guesses[1][1]
        return leader_prob >= Game.LEAD_RATIO * second_prob

    @staticmethod
    def find_character(characters, name):
        """The character the player named, or None if it is not in the dataset.

        Forgiving like a person would be: case and spaces are ignored, a middle name or a
        surname alone is enough (the better-known one wins, so "trump" is Donald), and a
        small typo is accepted ("albert einstien").
        """
        wanted = " ".join(name.split()).lower()
        if not wanted:
            return None
        by_name = {character["name"].lower(): character for character in characters}
        if wanted in by_name:
            return by_name[wanted]
        words = set(wanted.split())
        partial = [character for character in characters
                   if set(character["name"].lower().split()) <= words or words <= set(character["name"].lower().split())]
        if partial:
            return max(partial, key=lambda character: character["sitelinks"])
        close = difflib.get_close_matches(wanted, list(by_name), n=1, cutoff=0.8)
        return by_name[close[0]] if close else None

    @staticmethod
    def read_confirm(reply):
        """The answer to "Is it X?": ("yes" / "no" / "again", name the player typed or None)."""
        answer = Game.parse_user_input(reply)
        if answer in ("yes", "no"):
            return answer, None
        if answer == "unknown" or not reply.strip():
            return "again", None
        return "no", reply.strip()      # a name: "no, it was this person"

    @staticmethod
    def ask_yes_no(text):
        """Ask until the player answers yes or no (used where "not sure" makes no sense)."""
        while True:
            verdict, _ = Game.read_confirm(input(Display.prompt_yes_no(text)))
            if verdict != "again":
                return verdict
            print(Display.yes_or_no())

    @staticmethod
    def disagreements(character, asked):
        """(question, player's answer, data's answer) where a definite answer contradicts the data."""
        data_answer = {True: "yes", False: "no", None: "unknown"}
        rows = []
        for question, answer in asked:
            expected = data_answer[character["attributes"][question]]
            if answer != "unknown" and expected != "unknown" and answer != expected:
                rows.append((question, answer, expected))
        return rows

    @staticmethod
    def explain_miss(characters, prior, questions, asked, name=None):
        """After a wrong guess: ask who it was (unless already typed) and show which answers disagreed with the data."""
        if name is None:
            name = input(Display.ask_name()).strip()
        if not name:
            return
        character = Game.find_character(characters, name)
        if character is None:
            print(Display.unknown_character(name, len(characters)))
            return
        ranked = [n for n, _ in Game.score_guesses(characters, prior, asked, len(characters))]
        rows = [(questions[q], said, data) for q, said, data in Game.disagreements(character, asked)]
        print(Display.explanation(character["name"], ranked.index(character["name"]) + 1, rows))

    @staticmethod
    def sibling_said_yes(question, answers, parents):
        """True if another question under the same parent was answered Yes (basketball Yes -> skip football)."""
        parent = parents.get(question)
        if parent is None:
            return False
        for other, answer in answers.items():
            if other != question and answer == "yes" and parents.get(other) == parent:
                return True
        return False

    @staticmethod
    def parse_user_input(user_in):
        """The player's reply as "yes" / "no" / "unknown", or None if it is not an answer."""
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
        """Ask one question until the player gives a valid answer; returns "yes", "no" or "unknown"."""
        prompt = Display.prompt(text)
        while True:
            user_in = input(prompt)
            answer = Game.parse_user_input(user_in)
            if answer is not None:
                return answer
            print(Display.invalid())
            prompt = Display.retry(text)     # the arcade screen keeps the error visible instead of redrawing

    @staticmethod
    def play_round(tree, questions, characters, prior, parents=None):
        """One game: the tree picks the questions, then all answers pick the top 3 guesses.

        Returns True when the game guessed right (for the score).
        """
        node = tree            # where we are in the decision tree (None once focus mode has taken over)
        asked = []             # (question, answer) pairs in the order they were asked
        # every character's chance so far: the arcade screen shows the leader's and how many are left
        guesses = Game.score_guesses(characters, prior, asked, len(characters))
        for count in range(1, Game.MAX_QUESTIONS + 1):     # count = 1, 2, ..., 15
            # 1. pick the next question (tree first, then focus mode) and ask it
            question = Game.choose_question(node, characters, prior, asked, parents)
            question_ = questions.get(question)          # the text the player reads
            answer = Game.ask(Display.question(count, Game.MAX_QUESTIONS, question_, guesses))
            asked.append((question, answer))
            # 2. follow the tree's branch for this answer; leave the tree if focus mode asked
            if node is not None and not node["leaf"] and question == node["question"]:
                node = Game.next_quest(node, answer)
            else:
                node = None
            # 3. score everyone again with all answers and show what changed
            new_guesses = Game.score_guesses(characters, prior, asked, len(characters))
            Animation.show(Display.feedback(answer, guesses, new_guesses))
            Animation.pause(1.0)
            guesses = new_guesses
            # stop early when one character is already far ahead (like akinator.dev)
            if count >= Game.MIN_QUESTIONS and Game.confident(guesses):
                break
        # 4. the guess: the best character, with the next two shown as other possibilities
        ge_names = Game.score_guesses(characters, prior, asked, 3)
        Animation.show(Display.final_round(len(asked), Game.MAX_QUESTIONS))
        Animation.progress(Display.loading_frames(), 0.06)
        Animation.frames(Display.clues(asked), 0.3)
        Animation.show(Display.result(ge_names, len(asked)), 0.002)
        # one guess only: the runners-up are already on screen
        guess = ge_names[0][0]
        while True:
            verdict, name = Game.read_confirm(input(Display.prompt_yes_no(Display.confirm(guess))))
            if verdict != "again":
                break
            print(Display.yes_or_no())
        # typing the guessed character's name instead of y also counts as right
        named = Game.find_character(characters, name) if name else None
        if verdict == "yes" or (named is not None and named["name"] == guess):
            Animation.show(Display.win(len(asked), ge_names[0][1]), 0.002)
            return True
        print(Display.lose())
        Game.explain_miss(characters, prior, questions, asked, name)
        return False

    @staticmethod
    def focus_question(characters, prior, asked, top_n, parents=None):
        """The unasked question that best tells the current top candidates apart.

        Linked questions: children of a No are skipped, and a child of a Yes is preferred
        when it is nearly as good as the best question, so the questions follow on.
        """
        if not parents:
            parents = {}
        # [{name: prob} ..]
        candidates = Game.score_guesses(characters, prior, asked, top_n)
        attributes = {}
        #characters = [{"name": "Hulk", "attributes": {"is_male": True,...},]
        #  attributes = {"Hulk" : {"is_male": True,...}}
        for character in characters:
            attributes[character["name"]] = character["attributes"]

        # asked   = [("is_fictional", "yes"),...] to answer = {"is_fictional": "yes",...}
        answers = dict(asked)
        entropies = {}
        for question in characters[0]["attributes"]:
            if question in answers or Game.ruled_out(question, answers, parents) or Game.over_limit(question, answers):
                continue
            entropies[question] = DecisionTree.expected_entropy(candidates, attributes, question)
        if not entropies:
            return None

        res_mini_name = Game.mini_name(entropies)
        follow_up_question = {}
        for question in entropies:
            if (answers.get(parents.get(question)) == "yes" and not Game.sibling_said_yes(question, answers, parents)
                    and entropies[question] <= (entropies[res_mini_name] + Game.FOLLOW_UP_SLACK)):
                follow_up_question[question] = entropies[question]

        best_follow_up = Game.mini_name(follow_up_question)
        if best_follow_up:
            return best_follow_up
        return res_mini_name

    @staticmethod
    def mini_name(entropies):
        res_mini = float("inf")
        res_mini_name = None
        for question in entropies:
            if entropies[question] < res_mini:
                res_mini = entropies[question]
                res_mini_name = question
        return res_mini_name





