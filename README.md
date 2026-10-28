# Guessorithm

A terminal guessing game in the spirit of Akinator (repository: `character-guesser`).
Think of a famous real person or fictional character. The game, ALGO, asks up to
15 yes / no / not-sure questions and then guesses who it is. It knows 500
characters (350 real people, 150 fictional).

Built as a final project for COMP9001 (Introduction to Programming, University of Sydney).

## How to start

You need Python 3.8 or later. No extra packages are needed.

```bash
cd src
python3 main.py
```

Run it from inside `src/`, because the game reads `../dataset/` and `../model/`.

Use a real terminal (macOS Terminal, iTerm, or a Windows/Linux terminal) at least
60 columns wide. The arcade screen uses colours, clears the screen and centres
itself in the window. IDE run windows such as PyCharm's cannot clear the screen
or centre text, so the layout breaks there.

For one plain line per question, with no colours or animation:

```bash
python3 main.py --plain
```

## How to play

1. **Title screen.** Press Enter to start.
2. **Think of someone.** A 3-2-1 countdown starts the round. Don't type the name yet.
3. **Answer the questions.** Each screen is one stage (STAGE 01/15 ...). Type an
   answer and press Enter:

   | Type | Means |
   |---|---|
   | `y` or `yes` | yes |
   | `n` or `no` | no |
   | `?`, `not sure`, `maybe` or `u` | not sure (use it when you really don't know) |

   After each answer you see how sure ALGO is (the MIND-READ meter) and how many
   suspects are left. A wrong answer does not end the game; it only makes that
   character less likely.
4. **The guess.** After 15 questions, or earlier once ALGO is far more sure of one
   character than the rest (COMBO BREAKER), it shows its answer and the next two
   possibilities. Then reply:
   - `y` if it is right: **K.O., ALGO wins**, with a rank for how few questions it needed;
   - `n` if it is wrong: **YOU WIN**. Then type who you were thinking of (or press Enter to skip);
   - or type the name straight away instead of `n`.
5. **Battle replay.** If you name your character, ALGO shows which of your answers
   did not match its data. A name it does not know gets "CHARACTER NOT FOUND".
6. **Continue?** `y` plays another round (the score ALGO : P1 is kept); `n` ends the
   game with GAME OVER and the final score.

Press Ctrl-C at any time to quit.

**Tips**
- Pick someone well known: leaders, scientists, athletes, singers, actors,
  superheroes, cartoon and video-game characters.
- Names are matched forgivingly: case does not matter, a surname alone is enough
  ("einstein"), and small typos are accepted.

## How it works

1. **Simulated players** (`simulate.py`): for every character, answer sheets are
   generated the way real players answer (sometimes wrong or unsure), more of them
   for more famous characters (`probability.py`).
2. **ID3 decision tree** (`decision_tree.py`, trained by `train.py`): entropy and
   information gain pick the best question at each node. The tree is saved to
   `model/tree.json` and chooses the first questions of every round.
3. **Focus mode** (`game.py`): once the tree's branch has too little training data,
   the next question is the one that best splits the 20 most likely characters
   (lowest expected entropy).
4. **Scoring** (`game.py`): after every answer, all 500 characters are scored with
   all the answers so far, so one wrong answer lowers a score instead of ruling a
   character out.
5. **Linked questions**: each question knows its broader parent (UK -> Europe), so
   answers that already follow from earlier ones are never asked.

To retrain the tree after changing the dataset (about a minute):

```bash
cd src
python3 train.py
```

## Files

| Path | Contents |
|---|---|
| `src/main.py` | Starts the game (arcade screen by default, `--plain` for plain lines) |
| `src/game.py` | Game logic: choosing questions, scoring, guessing, the round and the score |
| `src/decision_tree.py` | The hand-written ID3 decision tree |
| `src/train.py` | Trains the tree and saves `model/tree.json` |
| `src/simulate.py` | How simulated players answer (the answer models) |
| `src/probability.py` | Popularity prior: famous characters start more likely |
| `src/dataset.py` | Reads `dataset/characters.csv` and `dataset/questions.csv` |
| `src/display.py` | Everything on screen, for both the arcade and the plain screen |
| `src/animation.py` | Arcade timing: pauses, countdown, typing effect, loading bar |
| `dataset/` | The 500 characters and 188 questions (see `dataset/README.md`) |
| `model/tree.json` | The trained decision tree |

## Data

Character facts come from [Wikidata](https://www.wikidata.org/) (CC0), with hand
corrections where Wikidata differs from what ordinary players believe. Popularity
uses the number of Wikipedia language editions of each article. The pipeline that
built the dataset, the tests and the evaluation script are not part of this
submission; they are on the `feat/arcade-screen` branch of the GitHub repository.

## AI Usage Declaration

In accordance with the University of Sydney's academic integrity policy on generative AI,
I declare the following use of AI tools (Claude) in this assignment.

- I wrote the core game logic and the ID3 decision tree (game.py, decision_tree.py,
  train.py, simulate.py, probability.py, dataset.py) with Claude explaining concepts
  step by step and reviewing my code.
- Claude wrote the data pipeline that built dataset/ (not submitted; on the
  feat/arcade-screen branch) and the test and evaluation scripts (not submitted).
- Claude wrote the arcade screen (the arcade parts of display.py, and animation.py)
  and some changes to game.py (score, arcade round flow, re-prompt after an invalid
  answer); I reviewed them line by line.

## License

[MIT](LICENSE)
