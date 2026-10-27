import sys

from animation import Animation
from display import Display
from game import Game


def main():
    # python3 main.py --arcade : the arcade screen (colours, countdown, K.O.); plain lines without it
    if "--arcade" in sys.argv[1:]:
        Display.FANCY = True
        Animation.ON = True
    Game.play()


if __name__ == "__main__":
    main()
