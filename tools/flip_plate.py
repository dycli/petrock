"""Mirror a plate design left to right (about x = 0), every item flipped to the
other face: the left half's plate as it really sits, for the 3D renders
(a mirrored STEP model renders inside out).

usage: flip_plate.py IN OUT
"""
import os
import sys

import pcbnew


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    origin = pcbnew.VECTOR2I(0, 0)
    for item in list(board.GetFootprints()) + list(board.GetDrawings()):
        item.Flip(origin, pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
