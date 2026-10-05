"""Take the silkscreen off the jacks, reset buttons and OLED headers (their
outlines and labels, both faces), leaving their pads: the controller corner
stays plain whether or not the parts are fitted.

usage: quiet_silk.py BOARD   (edits BOARD in place)
"""
import os
import sys

import pcbnew

QUIET = ("J1", "J3", "RSW1", "RSW2", "J2", "J4")
SILK = (pcbnew.F_SilkS, pcbnew.B_SilkS)


def main(path):
    board = pcbnew.LoadBoard(path)
    doomed = [(f, g) for f in board.GetFootprints() if f.GetReference() in QUIET
              for g in f.GraphicalItems() if g.GetLayer() in SILK]
    for f, g in doomed:        # last: removing leaves other handles stale
        f.Remove(g)
    board.Save(path)
    print(len(doomed))


if __name__ == "__main__":
    main(sys.argv[1])
    sys.stdout.flush()
    os._exit(0)
