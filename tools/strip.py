"""Remove the holykeebs and Corne logos, and the mounting holes for holykeebs'
OLED cover (unused here; the switch plate covers them).

usage: strip.py IN OUT
"""
import os
import sys

import pcbnew

GONE = ("holykeebs:logo", "kbd:corne-logo", "holykeebs:M2_HOLE_NPH")


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    doomed = [f for f in board.GetFootprints() if f.GetFPIDAsString().startswith(GONE)]
    for f in doomed:            # removing invalidates other handles, so all at once
        board.Remove(f)
    board.Save(dst)
    print(len(doomed))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
