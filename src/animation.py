"""Timed printing for the arcade screen: pauses, a typing effect, frames and a loading bar.

ON = False prints everything at once, so the plain screen and the tests never wait.
"""
import re
import sys
import time


class Animation:
    ON = False
    TOKENS = re.compile(r"\033\[[0-9;]*[A-Za-z]|.", re.DOTALL)   # one colour code, or one character

    @staticmethod
    def pause(seconds):
        if Animation.ON:
            time.sleep(seconds)

    @staticmethod
    def show(text, delay=0.0):
        """Print text; with ON and a delay, one character at a time like an old terminal."""
        if not text:
            return
        if not Animation.ON or delay <= 0:
            print(text)
            return
        for token in Animation.TOKENS.findall(text):
            sys.stdout.write(token)
            sys.stdout.flush()
            if len(token) == 1 and not token.isspace():
                time.sleep(delay)
        print()

    @staticmethod
    def frames(frames, delay):
        """Print each frame on its own line with a pause after it (the countdown, the clue list)."""
        for frame in frames:
            print(frame)
            Animation.pause(delay)

    @staticmethod
    def progress(frames, delay):
        """Draw the frames over each other on one line, so a bar fills up in place."""
        if not frames:
            return
        if not Animation.ON:
            print(frames[-1])
            return
        for frame in frames:
            sys.stdout.write("\r\033[K" + frame)   # back to the start of the line and wipe it
            sys.stdout.flush()
            time.sleep(delay)
        print()
