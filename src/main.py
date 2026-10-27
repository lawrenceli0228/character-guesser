from display import Display
from game import Game


def main():
    Display.FANCY = True    # the game screen: title box, progress bar, framed guess
    Game.play()


if __name__ == "__main__":
    main()
