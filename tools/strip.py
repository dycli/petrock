"""Remove the holykeebs and Corne logos, holykeebs' revision stamp (the short
git hash printed on the back), and their M2 holes: on the PCB those mount
holykeebs' OLED cover (unused here); on the stock plate they're its screw holes,
which tools/plate.py puts back over our standoffs.

usage: strip.py IN OUT
"""
import os
import sys

import pcbnew

GONE = ("holykeebs:logo", "kbd:corne-logo", "holykeebs:M2_HOLE_NPH")
STAMP = "271364f"           # holykeebs' design revision


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    doomed = [f for f in board.GetFootprints() if f.GetFPIDAsString().startswith(GONE)]
    doomed += [d for d in board.GetDrawings() if d.GetClass() == "PCB_TEXT" and d.GetText() == STAMP]
    for f in doomed:            # removing invalidates other handles, so all at once
        board.Remove(f)
    board.Save(dst)
    print(len(doomed))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
