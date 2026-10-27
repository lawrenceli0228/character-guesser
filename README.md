# Character Guesser

A terminal guessing game in the spirit of Akinator. Think of a famous real person
or fictional character; the game asks up to 15 yes / no / not-sure questions and
then guesses who it is. It knows 500 characters (350 real people, 150 fictional).

Built as a final project for COMP9001 (Introduction to Programming, University of Sydney).

## How to run

Requires Python 3.8 or later; no third-party packages.

```bash
cd src
python3 main.py
```

Answer each question with `y` (yes), `n` (no) or `?` (not sure). If the guess is
wrong, type who you were thinking of and the game shows which of your answers
disagreed with its data.

To retrain the decision tree after changing the dataset (about 30 seconds):

```bash
cd src
python3 train.py
```

## How it works

1. **Simulated players** (`simulate.py`): for every character, thousands of answer
   sheets are generated with a realistic error rate (players are sometimes wrong
   or unsure), weighted by how famous the character is (`probability.py`).
2. **ID3 decision tree** (`decision_tree.py`): a hand-written ID3 tree (entropy and
   information gain, no machine-learning libraries) is trained on these sheets and
   saved to `model/tree.json`. It chooses the first questions.
3. **Focus mode** (`game.py`): once the tree has too little training data for the
   current branch, the next question is the one that best splits the 20 most
   likely characters (lowest expected entropy).
4. **Guessing** (`game.py`): every character is scored with all answers given, so
   one wrong answer lowers a score instead of ruling the character out. The game
   guesses early once the leader is 20 times more likely than the runner-up.
5. **Linked questions**: questions know their broader parent question (UK -> Europe),
   so answers that follow from earlier ones are never asked.

## Project structure

| Path | Contents |
|---|---|
| `src/` | The game: `main.py`, `game.py`, `decision_tree.py`, `simulate.py`, `probability.py`, `dataset.py`, `display.py`, `train.py` |
| `tests/` | Tests for the game (`python3 -m pytest tests`) |
| `dataset/` | The 500 characters and 134 questions the game reads (see `dataset/README.md`) |
| `model/tree.json` | The trained decision tree |
| `data_pipeline/` | How the dataset was built from Wikidata (see `data_pipeline/DATA.md`) |
| `playtests.md` | Every playtest, why a guess failed, and the fix that followed |

## Running the tests

```bash
python3 -m pytest tests
python3 -m pytest data_pipeline/tests
```

## Data

Character facts come from [Wikidata](https://www.wikidata.org/) (CC0), with hand
corrections where Wikidata differs from what ordinary players believe. Popularity
uses the number of Wikipedia language editions of each article.

## Acknowledgements

The data pipeline and the dataset were prepared with the help of an AI assistant
(Claude), as approved for this project. The game code was written with step-by-step
guidance from the same assistant.

## License

[MIT](LICENSE)
