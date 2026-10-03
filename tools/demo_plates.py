"""Put both switch plates on a render-only board, at switch-plate height.

The plates are STEP exports of the right plate design (plate frame: the PCB's
right half shifted by -RIGHT_DX + PLATE_DX, tools/plate.py) and of the plain
design, mirrored for the left half.

usage: demo_plates.py IN RIGHT_PLATE.step PLAIN_PLATE.step OUT
"""
import os
import sys

import pcbnew

from demo_board import model

PLATE_TOP = 2.2          # choc: plate top above the PCB
THICKNESS = 1.6          # plate stackup
TO_RIGHT = 12.4 + 4.0    # plate frame -> PCB right half (RIGHT_DX - PLATE_DX)
MIRROR = 299.31 - 4.0    # plate frame -> PCB left half, mirrored (tools/widen.py MIRROR_X)


def main(src, right, plain, dst):
    board = pcbnew.LoadBoard(src)
    holder = pcbnew.FOOTPRINT(board)
    z = PLATE_TOP - THICKNESS
    holder.Models().push_back(model(right, z=z, offset=(TO_RIGHT, 0.0)))
    left = model(plain, z=z, offset=(MIRROR, 0.0))
    left.m_Scale = pcbnew.VECTOR3D(-1, 1, 1)
    holder.Models().push_back(left)
    holder.Reference().SetVisible(False)
    holder.Value().SetVisible(False)
    board.Add(holder)
    board.Save(dst)


if __name__ == "__main__":
    main(*sys.argv[1:5])
    sys.stdout.flush()
    os._exit(0)
