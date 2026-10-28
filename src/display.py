"""Everything the player sees: title screen, questions, the guess and the result.

Every method returns a string (or a list of frames); Game decides when to print it.
FANCY = False gives one plain line per question, which is easier to read while testing.
FANCY = True is the arcade screen: player 1 against ALGO (the game itself), in colour.
"""
import re
import shutil
import sys
import textwrap


class Display:
    FANCY = False
    WIDTH = 60
    SUSPECT_MIN = 0.001                       # a character still counts as a suspect above 0.1%
    RANKS = ((6, "S", 3), (9, "A", 2), (12, "B", 1))   # (most questions used, rank, stars)
    GITHUB = "github.com/lawrenceli0228/character-guesser"
    RIVAL = "ALGO"                            # the name the game plays under on the arcade screen

    # ANSI colour codes: the terminal shows the text between a code and RESET in that colour
    PURPLE = "\033[95m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    CLEAR = "\033[2J\033[H"                   # wipe the screen and go back to the top left

    KO = [                                    # "K.O." in block letters for the rival's win
        "█   █    ███  ",
        "█  █    █   █ ",
        "███     █   █ ",
        "█  █    █   █ ",
        "█   █ ▪  ███ ▪",
    ]

    # --- helpers for the arcade screen ---------------------------------------------

    @staticmethod
    def paint(text, colour):
        return f"{colour}{text}{Display.RESET}"

    @staticmethod
    def visible(text):
        """The text without colour codes: what the player actually sees."""
        return re.sub(r"\033\[[0-9;]*[A-Za-z]", "", text)

    @staticmethod
    def centre(text):
        """Centre a line by its visible length (colour codes take no space on screen)."""
        gap = max(0, Display.WIDTH - len(Display.visible(text)))
        return " " * (gap // 2) + text

    @staticmethod
    def margin():
        """Spaces that move the 60-column screen to the middle of the terminal window."""
        if not sys.stdout.isatty():
            return ""                         # tests and pipes: nothing to centre in
        columns = shutil.get_terminal_size().columns
        return " " * max(0, (columns - Display.WIDTH) // 2)

    @staticmethod
    def place(text):
        """Indent every line by the margin, so the whole screen sits in the middle of the window."""
        pad = Display.margin()
        lines = []
        for line in text.split("\n"):
            if line.startswith(Display.CLEAR):          # the margin goes after the clear-screen code
                lines.append(Display.CLEAR + pad + line[len(Display.CLEAR):])
            else:
                lines.append(pad + line)
        return "\n".join(lines)

    @staticmethod
    def box(lines, colour):
        """Lines centred inside a frame of ▓ blocks."""
        inner = Display.WIDTH - 4
        edge = Display.paint("▓" * Display.WIDTH, colour)
        side = Display.paint("▓", colour)
        rows = [edge]
        for line in lines:
            gap = max(0, inner - len(Display.visible(line)))
            rows.append(f"{side} {' ' * (gap // 2)}{line}{' ' * (gap - gap // 2)} {side}")
        rows.append(edge)
        return "\n".join(rows)

    @staticmethod
    def spaced(name):
        """HULK -> H U L K, unless that is too wide for the answer box."""
        wide = " ".join(name.upper())
        return wide if len(wide) <= Display.WIDTH - 14 else name.upper()

    @staticmethod
    def meter(prob):
        """The rival's mind-read meter: one cell per 10% that the top guess is right."""
        filled = min(10, round(prob * 10))
        return Display.paint("▮" * filled, Display.YELLOW) + Display.paint("▯" * (10 - filled), Display.DIM)

    @staticmethod
    def suspects(guesses):
        return sum(1 for _, prob in guesses if prob >= Display.SUSPECT_MIN)

    @staticmethod
    def label(question):
        """A short clue name from a question key: look_green_skin -> GREEN SKIN."""
        for prefix in ("known_for_", "first_appeared_in_", "occupation_", "universe_", "franchise_",
                       "instrument_", "position_", "is_", "has_", "from_", "real_", "work_", "look_",
                       "role_", "award_", "sport_", "age_"):
            if question.startswith(prefix):
                question = question[len(prefix):]
                break
        return question.replace("_", " ").upper()

    @staticmethod
    def score(score):
        return f"{Display.paint(Display.RIVAL + ' ' + str(score['algo']), Display.RED)} : " \
               f"{Display.paint(str(score['player']) + ' P1', Display.GREEN)}"

    @staticmethod
    def rank(questions_used):
        for most, rank, stars in Display.RANKS:
            if questions_used <= most:
                return "★" * stars + " " + rank
        return "C"

    # --- what Game prints ------------------------------------------------------------

    @staticmethod
    def wrap(text):
        """Indent text by two spaces and wrap it to the screen width."""
        return textwrap.fill(text, width=Display.WIDTH, initial_indent="  ", subsequent_indent="  ")

    @staticmethod
    def prompt(text):
        """What input() shows: the question text, then where to type y / n / ?."""
        if not Display.FANCY:
            return f"{text} (y/n/?) "
        keys = (f"{Display.paint('[Y] YES', Display.GREEN)}    {Display.paint('[N] NO', Display.RED)}    "
                f"{Display.paint('[?] NOT SURE', Display.YELLOW)}")
        return Display.place(f"{text}\n\n{Display.centre(keys)}\n\n  {Display.paint('PLAYER 1 >', Display.CYAN)} ")

    @staticmethod
    def retry(text):
        """The prompt after an invalid answer: the whole question again, or only PLAYER 1 > on the arcade screen."""
        if not Display.FANCY:
            return Display.prompt(text)
        return Display.place(f"  {Display.paint('PLAYER 1 >', Display.CYAN)} ")

    @staticmethod
    def prompt_yes_no(text):
        """Like prompt, for questions where only yes or no makes sense ("Is it X?", "Play again?")."""
        if not Display.FANCY:
            return f"{text} (y/n) "
        keys = f"{Display.paint('[Y] YES', Display.GREEN)}    {Display.paint('[N] NO', Display.RED)}"
        return Display.place(f"{text}\n\n{Display.centre(keys)}\n\n  {Display.paint('PLAYER 1 >', Display.CYAN)} ")

    @staticmethod
    def yes_or_no():
        if not Display.FANCY:
            return "Please answer y or n (or type who it was)"
        return Display.place(f"  {Display.paint('✖ ONLY Y OR N', Display.RED)} {Display.paint('(or type who it was)', Display.DIM)}")

    @staticmethod
    def title(max_questions, character_count):
        """The opening screen: game name, what to do and how to answer."""
        if not Display.FANCY:
            return f"Guessorithm: think of someone, I will guess in {max_questions} questions."
        logo = Display.box(["", Display.paint("G U E S S O R I T H M", Display.BOLD + Display.YELLOW),
                            Display.paint("·  R E A D S   Y O U R   M I N D  ·", Display.PURPLE), ""], Display.PURPLE)
        lines = [
            Display.CLEAR + logo,
            "",
            Display.centre(f"{Display.paint('PLAYER 1', Display.GREEN)}   vs   {Display.paint(Display.RIVAL, Display.RED)}"),
            Display.centre(Display.paint(f"{character_count} characters loaded · {max_questions} stages", Display.DIM)),
            "",
            Display.wrap(f"Think of a famous real person or fictional character. I know {character_count} "
                         f"of them, and I will guess who it is in {max_questions} questions."),
            "",
            "  Answer with:   " + Display.paint("y = yes", Display.GREEN) + "    "
            + Display.paint("n = no", Display.RED) + "    " + Display.paint("? = not sure", Display.YELLOW),
            "",
            Display.paint(Display.wrap("How I think: a decision tree trained with ID3 picks the first questions, "
                                       "then the last ones focus on the people I currently think are most likely."),
                          Display.DIM),
        ]
        return Display.place("\n".join(lines))

    @staticmethod
    def press_start():
        """The prompt that waits on the title screen; the plain screen starts straight away."""
        if not Display.FANCY:
            return None
        return Display.place("\n" + Display.centre(Display.paint("▶  PRESS ENTER TO START  ◀", Display.CYAN)) + " ")

    @staticmethod
    def ready():
        """The countdown before each round, one frame per beat."""
        if not Display.FANCY:
            return []
        frames = [
            Display.CLEAR + "\n" + Display.centre(Display.paint("★ PLAYER 1 READY ★", Display.PURPLE)) + "\n\n"
            + Display.centre("Think of someone. Real or fictional.") + "\n"
            + Display.centre(Display.paint("Don't tell me.", Display.DIM)) + "\n",
            Display.centre(Display.paint("3", Display.BOLD + Display.YELLOW)),
            Display.centre(Display.paint("2", Display.BOLD + Display.YELLOW)),
            Display.centre(Display.paint("1", Display.BOLD + Display.YELLOW)),
            "\n" + Display.centre(Display.paint("▶  F I G H T !", Display.BOLD + Display.GREEN)),
        ]
        return [Display.place(frame) for frame in frames]

    @staticmethod
    def progress_bar(number, total):
        """One filled block per question asked so far."""
        return "▓" * number + "░" * (total - number)

    @staticmethod
    def question(number, total, text, guesses=None):
        """One question with its number; the arcade screen adds the stage bar and the mind-read meter."""
        if not Display.FANCY:
            return f"Q{number}: {text}"
        bar = Display.paint("▓" * number, Display.YELLOW) + Display.paint("░" * (total - number), Display.DIM)
        lines = [Display.CLEAR + "  " + Display.paint(f"STAGE {number:02d}/{total}", Display.PURPLE) + "   " + bar]
        if guesses:
            lines.append(f"  {Display.paint(Display.RIVAL + ' MIND-READ', Display.YELLOW)} {Display.meter(guesses[0][1])} "
                         f"{Display.paint(Display.chance(guesses[0][1]), Display.YELLOW)}   "
                         f"{Display.paint(str(Display.suspects(guesses)) + ' suspects left', Display.DIM)}")
        lines.append("  " + Display.paint("─" * (Display.WIDTH - 2), Display.PURPLE))
        lines.append("")
        wrapped = textwrap.fill(text, width=Display.WIDTH - 5, initial_indent="", subsequent_indent="     ")
        lines.append("  " + Display.paint(">>", Display.PURPLE) + " " + Display.paint(wrapped, Display.BOLD))
        return "\n".join(lines)

    @staticmethod
    def invalid():
        if not Display.FANCY:
            return "Please answer y, n or ?"
        return Display.place(f"  {Display.paint('✖ INVALID INPUT ✖', Display.RED)}  {Display.paint('only Y, N or ? accepted', Display.DIM)}")

    @staticmethod
    def feedback(answer, before, after):
        """What one answer changed: the top guess's chance and how many suspects are left."""
        if not Display.FANCY:
            return ""
        if answer == "unknown":
            return Display.place("\n" + Display.centre(Display.paint("?  NO CLUE  ?", Display.YELLOW)) + "\n"
                                 + Display.centre(Display.paint("skipped, no harm done", Display.DIM)))
        old, new = before[0][1], after[0][1]
        arrow = Display.paint("▲", Display.GREEN) if new >= old else Display.paint("▼", Display.RED)
        return Display.place("\n".join([
            "",
            Display.centre(Display.paint("+ CLUE ACQUIRED!", Display.BOLD + Display.GREEN)),
            Display.centre(Display.paint(f"MIND-READ {Display.chance(old)} ", Display.YELLOW) + arrow
                           + Display.paint(f" {Display.chance(new)}", Display.YELLOW)),
            Display.centre(Display.paint(f"{Display.suspects(before)} → {Display.suspects(after)} suspects left",
                                         Display.DIM)),
        ]))

    @staticmethod
    def final_round(questions_used, total):
        """Before the guess; a COMBO BREAKER when the rival is sure before the last stage."""
        if not Display.FANCY:
            return ""
        lines = [Display.CLEAR]
        if questions_used < total:
            lines += [Display.centre(Display.paint("!!  C O M B O   B R E A K E R  !!", Display.BOLD + Display.YELLOW)),
                      Display.centre(f"{Display.RIVAL} is sure after stage {questions_used}. Skipping ahead!"), ""]
        lines += [Display.centre(Display.paint("F I N A L   R O U N D", Display.PURPLE)), ""]
        return Display.place("\n".join(lines))

    @staticmethod
    def loading_frames():
        """A READING MIND bar that fills in 20 steps."""
        if not Display.FANCY:
            return []
        return [Display.place(f"  {Display.paint('READING MIND', Display.YELLOW)}  "
                              f"[{Display.paint('▓' * step, Display.YELLOW)}{'░' * (20 - step)}] {step * 5}%")
                for step in range(21)]

    @staticmethod
    def clues(asked):
        """The last few Yes answers, as if the rival were checking its notes."""
        if not Display.FANCY:
            return []
        yes = [question for question, answer in asked if answer == "yes"][-4:]
        return [Display.place(f"    {Display.paint('✓', Display.GREEN)} {Display.label(question)}") for question in yes]

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
        name = Display.paint(f">>  {Display.spaced(guesses[0][0])}  <<", Display.BOLD + Display.GREEN)
        lines = ["", Display.box([Display.paint(f"{Display.RIVAL}'S FINAL ANSWER", Display.YELLOW), "", name], Display.RED)]
        for rank, (other, prob) in enumerate(guesses[1:], start=2):
            lines.append(Display.paint(f"  {rank}P  {other:<30} {Display.chance(prob):>4}", Display.DIM))
        lines.append(Display.paint(f"  {questions_used} questions used", Display.DIM))
        return Display.place("\n".join(lines))

    @staticmethod
    def confirm(name):
        if not Display.FANCY:
            return f"Is it {name}?"
        return f"\n  {Display.paint(f'IS {Display.RIVAL} CORRECT?', Display.YELLOW)} {Display.paint('(or type who it was)', Display.DIM)}"

    @staticmethod
    def win(questions_used, prob=None):
        """The rival guessed right: K.O. screen with stages, mind-read and a rank."""
        if not Display.FANCY:
            return f"I got it in {questions_used} questions!"
        lines = [""] + [Display.centre(Display.paint(row, Display.RED)) for row in Display.KO]
        lines += ["", Display.centre(Display.paint(Display.spaced(Display.RIVAL + " WINS!"), Display.BOLD + Display.RED)), ""]
        lines.append(f"     Stages cleared  {Display.paint(f'{questions_used:02d}', Display.YELLOW)}")
        if prob is not None:
            lines.append(f"     Mind-read       {Display.paint(Display.chance(prob), Display.YELLOW)}")
        lines.append(f"     Rank            {Display.paint(Display.rank(questions_used), Display.BOLD + Display.YELLOW)}")
        lines += ["", Display.centre(Display.paint(f"Guessed in {questions_used} questions. "
                                                   "\"Get out of my head?\" Never.", Display.DIM))]
        return Display.place("\n".join(lines))

    @staticmethod
    def lose():
        if not Display.FANCY:
            return "You win! I couldn't guess who it was."
        return Display.place("\n" + Display.centre(Display.paint("★ ★   Y O U   W I N   ★ ★", Display.BOLD + Display.GREEN))
                             + "\n" + Display.centre(Display.paint(f"New challenger defeats {Display.RIVAL}!", Display.GREEN)))

    @staticmethod
    def ask_name():
        if not Display.FANCY:
            return "Who were you thinking of? (press Enter to skip) "
        return Display.place(f"\n  {Display.paint('ENTER YOUR CHARACTER', Display.YELLOW)} {Display.paint('(Enter to skip)', Display.DIM)}"
                             f"\n  {Display.paint('▸', Display.YELLOW)} ")

    @staticmethod
    def unknown_character(name, character_count):
        if not Display.FANCY:
            return f"I don't know {name} yet: they are not one of my {character_count} characters."
        return Display.place("\n".join([
            "",
            f"  {Display.paint('⚠ CHARACTER NOT FOUND', Display.YELLOW)}",
            f"  I don't know {name} yet: they are not one of my {character_count} characters.",
            f"  {Display.paint('Unlock in the next DLC.', Display.DIM)}",
        ]))

    @staticmethod
    def explanation(name, rank, rows):
        """Why the guess missed: where the player's answers and the data disagreed."""
        if not Display.FANCY:
            lines = [f"{name} was my number {rank} guess."]
            if not rows:
                lines.append(f"All your answers matched my data; {name} was just less likely than my guess.")
            else:
                lines.append("These answers did not match my data:")
                for question, said, data in rows:
                    lines.append(f"  - {question} (you said {said}, my data says {data})")
            return "\n".join(lines)
        misses = f"{len(rows)} critical miss" + ("" if len(rows) == 1 else "es")
        lines = ["", Display.centre(Display.paint("═══  B A T T L E   R E P L A Y  ═══", Display.PURPLE)), "",
                 f"  Found: {Display.paint(name, Display.GREEN)} · my number {rank} guess",
                 f"  {Display.paint(misses, Display.RED)}"]
        if not rows:
            lines.append(Display.wrap(f"All your answers matched my data; {name} was just less likely than my guess."))
        for question, said, data in rows:
            lines.append("")
            lines.append(textwrap.fill(question, width=Display.WIDTH, initial_indent="  ✖ ", subsequent_indent="    "))
            lines.append(f"    {Display.paint('P1', Display.DIM)} {Display.paint(said.upper(), Display.RED)}"
                         f"    {Display.paint(Display.RIVAL + ' DATA', Display.DIM)} {Display.paint(data.upper(), Display.GREEN)}")
        lines += ["", f"  {Display.paint(f'{Display.RIVAL} will remember this.', Display.DIM)}"]
        return Display.place("\n".join(lines))

    @staticmethod
    def play_again(score=None):
        if not Display.FANCY:
            return "Play again?"
        lines = ["", Display.centre(Display.paint("C O N T I N U E ?", Display.BOLD + Display.YELLOW))]
        if score:
            lines.append(Display.centre("Score  " + Display.score(score)))
        return "\n".join(lines)

    @staticmethod
    def goodbye(score=None):
        if not Display.FANCY:
            return "Thanks for playing!"
        lines = ["", Display.box(["", Display.paint("G A M E   O V E R", Display.BOLD + Display.RED), ""], Display.PURPLE), ""]
        if score:
            lines.append(Display.centre("Final score  " + Display.score(score)))
        lines += [Display.centre("Thanks for playing!"), Display.centre(Display.paint(Display.GITHUB, Display.CYAN))]
        return Display.place("\n".join(lines))
