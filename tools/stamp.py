"""Print the commit the board was built from (its short git hash) on the back,
centred between each controller's pin rows, as holykeebs printed theirs: check
that commit out and the build reproduces this board.

usage: stamp.py BOARD HASH   (edits BOARD in place)
"""
import os
import sys

import pcbnew

MM = pcbnew.FromMM
SIZE, THICK = 1.5, 0.22          # mm: text height, stroke


def main(path, stamp):
    board = pcbnew.LoadBoard(path)
    for u in (f for f in board.GetFootprints() if f.GetReference() in ("U1", "U2")):
        xs = [pcbnew.ToMM(p.GetPosition().x) for p in u.Pads()]
        ys = [pcbnew.ToMM(p.GetPosition().y) for p in u.Pads()]
        t = pcbnew.PCB_TEXT(board)
        t.SetText(stamp)
        t.SetLayer(pcbnew.B_SilkS)
        t.SetMirrored(True)
        t.SetTextSize(pcbnew.VECTOR2I(MM(SIZE), MM(SIZE)))
        t.SetTextThickness(MM(THICK))
        t.SetPosition(pcbnew.VECTOR2I(MM((min(xs) + max(xs)) / 2), MM((min(ys) + max(ys)) / 2)))
        board.Add(t)
    board.Save(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
