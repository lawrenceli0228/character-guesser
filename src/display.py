"""Everything the player sees: title screen, questions, the guess and the result.

Every method returns a string; Game decides when to print it.
FANCY = False gives one plain line per question, which is easier to read while testing.
"""
import textwrap


class Display:
    FANCY = False
    WIDTH = 60

    @staticmethod
    def wrap(text):
        """Indent text by two spaces and wrap it to the screen width."""
        return textwrap.fill(text, width=Display.WIDTH, initial_indent="  ", subsequent_indent="  ")

    @staticmethod
    def prompt(text):
        """What input() shows: the question text, then where to type y / n / ?."""
        if not Display.FANCY:
            return f"{text} (y/n/?) "
        return f"{text}\n  (y / n / ?) > "

    @staticmethod
    def prompt_yes_no(text):
        """Like prompt, for questions where only yes or no makes sense ("Is it X?", "Play again?")."""
        if not Display.FANCY:
            return f"{text} (y/n) "
        return f"{text}\n  (y / n) > "

    @staticmethod
    def yes_or_no():
        return "Please answer y or n (or type who it was)" if not Display.FANCY else "  Please answer y or n (or type who it was)"

    @staticmethod
    def title(max_questions, character_count):
        """The opening screen: game name, what to do and how to answer."""
        if not Display.FANCY:
            return f"Character Guesser: think of someone, I will guess in {max_questions} questions."
        border = "═" * Display.WIDTH
        lines = [
            border,
            "CHARACTER GUESSER".center(Display.WIDTH),
            f"I will guess who you are thinking of in {max_questions} questions".center(Display.WIDTH),
            border,
            Display.wrap(f"Think of a famous real person or fictional character. I know {character_count} "
                         "of them: scientists, leaders, athletes, singers, actors, superheroes, "
                         "cartoon and game characters."),
            "",
            "  Answer with:   y = yes    n = no    ? = not sure",
            "",
            Display.wrap("How I think: a decision tree trained with ID3 picks the first questions, "
                         "then the last ones focus on the people I currently think are most likely."),
            border,
        ]
        return "\n".join(lines)

    @staticmethod
    def progress_bar(number, total):
        """One filled box per question asked so far."""
        return "■" * number + "□" * (total - number)

    @staticmethod
    def question(number, total, text):
        """One question with its number (and a progress bar on the fancy screen)."""
        if not Display.FANCY:
            return f"Q{number}: {text}"
        return "\n".join([
            "",
            "  " + "─" * (Display.WIDTH - 2),
            f"  Question {number} of {total}   {Display.progress_bar(number, total)}",
            Display.wrap(text),
        ])

    @staticmethod
    def invalid():
        return "Please answer y, n or ?" if not Display.FANCY else "  Please answer y, n or ?"

    @staticmethod
    def chance(prob):
        """A probability as a whole percentage; tiny ones show as <1% rather than 0%."""
        return f"{prob:.0%}" if prob >= 0.005 else "<1%"

    @staticmethod
    def result(guesses, questions_used):
        """The guess: the top answer first, then the runners-up with their chance."""
        answer = f"My answer: {guesses[0][0]}"
        others = [f"{rank}. {name} ({Display.chance(prob)})" for rank, (name, prob) in enumerate(guesses[1:], start=2)]
        if not Display.FANCY:
            lines = [f"{questions_used} questions used, time to guess!", answer]
            if others:
                lines += ["Other possibilities:"] + ["  " + other for other in others]
            return "\n".join(lines)
        border = "═" * Display.WIDTH
        lines = ["", border, f"  {questions_used} questions used, time to guess!", "", f"  >>>  {answer}  <<<"]
        if others:
            lines += ["", "  Other possibilities:"] + ["    " + other for other in others]
        lines.append(border)
        return "\n".join(lines)

    @staticmethod
    def confirm(name):
        return f"Is it {name}?" if not Display.FANCY else f"  Is it {name}?"

    @staticmethod
    def win(questions_used):
        if not Display.FANCY:
            return f"I got it in {questions_used} questions!"
        return f"\n  *** I got it in {questions_used} questions! ***"

    @staticmethod
    def lose():
        if not Display.FANCY:
            return "You win! I couldn't guess who it was."
        return "\n  You beat me! I couldn't guess who it was."

    @staticmethod
    def ask_name():
        return "Who were you thinking of? (press Enter to skip) " if not Display.FANCY else \
            "\n  Who were you thinking of? (press Enter to skip) > "

    @staticmethod
    def unknown_character(name, character_count):
        indent = "  " if Display.FANCY else ""
        return f"{indent}I don't know {name} yet: they are not one of my {character_count} characters."

    @staticmethod
    def explanation(name, rank, rows):
        """Why the guess missed: where the player's answers and the data disagreed."""
        indent = "  " if Display.FANCY else ""
        lines = [f"{indent}{name} was my number {rank} guess."]
        if not rows:
            lines.append(f"{indent}All your answers matched my data; {name} was just less likely than my guess.")
        else:
            lines.append(f"{indent}These answers did not match my data:")
            for question, said, data in rows:
                lines.append(f"{indent}  - {question} (you said {said}, my data says {data})")
        return "\n".join(lines)

    @staticmethod
    def play_again():
        return "Play again?" if not Display.FANCY else "\n  Play again?"

    @staticmethod
    def goodbye():
        return "Thanks for playing!" if not Display.FANCY else "\n  Thanks for playing!"
