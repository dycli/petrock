"""Remove the holykeebs and Corne logos.

usage: strip_logos.py IN OUT
"""
import os
import sys

import pcbnew

LOGOS = ("holykeebs:logo", "kbd:corne-logo")


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    doomed = [f for f in board.GetFootprints() if f.GetFPIDAsString().startswith(LOGOS)]
    for f in doomed:            # removing invalidates other handles, so all at once
        board.Remove(f)
    board.Save(dst)
    print(len(doomed))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
