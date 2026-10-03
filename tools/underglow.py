"""Move the underglow LED beside the trackpoint driver (LED32, right half) and
its twin on the left half (LED5) to the open board between the bottom row's
per-key LEDs, mirrored on the two halves, so the driver's hand-soldered pads
have room.

usage: underglow.py IN OUT
"""
import os
import sys

import pcbnew

MM = pcbnew.FromMM
SPOT = (72.21, 104.6)       # LED5, left half; every pad 1 mm clear, courtyard free
MIRROR_X = 299.31           # tools/widen.py
RIGHT_DX = 12.4             # tools/widen.py


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    spots = {"LED5": SPOT, "LED32": (MIRROR_X - SPOT[0] + RIGHT_DX, SPOT[1])}
    for f in board.GetFootprints():
        if f.GetReference() in spots:
            f.SetPosition(pcbnew.VECTOR2I(MM(spots[f.GetReference()][0]), MM(spots[f.GetReference()][1])))
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
