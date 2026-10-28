"""Start the game (run from src/): python3 main.py

The arcade screen is the default: Player 1 against ALGO, colours, countdown, K.O.
python3 main.py --plain shows one plain line per question instead.
"""
import sys

from animation import Animation
from display import Display
from game import Game


def main():
    if "--plain" not in sys.argv[1:]:
        Display.FANCY = True      # the arcade screen (display.py)
        Animation.ON = True       # pauses, countdown and typing effect (animation.py)
    Game.play()


if __name__ == "__main__":
    main()
