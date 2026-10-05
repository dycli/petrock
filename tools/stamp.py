"""Print the board's name, version and repository on the back, lengthways
between each controller's pin rows (where holykeebs printed their revision).

usage: stamp.py BOARD NAME VERSION   (edits BOARD in place)
"""
import os
import sys

import pcbnew

MM = pcbnew.FromMM
REPO = "github.com/dycli/petrock"
SIZE, THICK, LEADING = 1.0, 0.15, 1.6     # mm: text height, stroke, line spacing


def main(path, name, version):
    board = pcbnew.LoadBoard(path)
    for u in (f for f in board.GetFootprints() if f.GetReference() in ("U1", "U2")):
        xs = [pcbnew.ToMM(p.GetPosition().x) for p in u.Pads()]
        ys = [pcbnew.ToMM(p.GetPosition().y) for p in u.Pads()]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        for i, line in enumerate((f"{name.upper()} {version}", REPO)):
            t = pcbnew.PCB_TEXT(board)
            t.SetText(line)
            t.SetLayer(pcbnew.B_SilkS)
            t.SetMirrored(True)
            t.SetTextSize(pcbnew.VECTOR2I(MM(SIZE), MM(SIZE)))
            t.SetTextThickness(MM(THICK))
            t.SetTextAngleDegrees(90)
            t.SetPosition(pcbnew.VECTOR2I(MM(cx + (i - 0.5) * LEADING), MM(cy)))
            board.Add(t)
    board.Save(path)


if __name__ == "__main__":
    main(*sys.argv[1:4])
    sys.stdout.flush()
    os._exit(0)
