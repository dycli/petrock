"""Replace each half's stepped top edge with a peak: a straight slope from the
inner top corner up to the middle-finger column, flat across its top, and a
straight slope down to the outer top corner.

PEAKS holds each half's four points in the PCB frame after tools/widen.py.
"""
import os
import sys

import pcbnew

MM = pcbnew.FromMM

PEAKS = {
    # side edge's top end, middle column's two top corners, other side edge's top end
    "left": [(16.8, 60.92), (70.52, 51.47), (90.48, 51.47), (152.91, 57.46)],
    "right": [(158.8, 57.46), (221.23, 51.47), (241.19, 51.47), (294.91, 60.92)],
}
TOP_Y = 61.0             # every stepped top-edge segment lies above this


def mm(v):
    return round(pcbnew.ToMM(v.x), 2), round(pcbnew.ToMM(v.y), 2)


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    doomed = []
    for d in board.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts:
            continue
        (ax, ay), (bx, by) = mm(d.GetStart()), mm(d.GetEnd())
        for pts in PEAKS.values():
            if max(ay, by) < TOP_Y and pts[0][0] - 0.01 <= min(ax, bx) and max(ax, bx) <= pts[-1][0] + 0.01:
                doomed.append(d)
    for d in doomed:          # removing invalidates other handles, so all at once
        board.Remove(d)
    record = open(os.environ["NEW_EDGES"], "a") if os.environ.get("NEW_EDGES") else None
    for pts in PEAKS.values():
        for a, b in zip(pts, pts[1:]):
            if record:
                record.write(f"{a[0]} {a[1]} {b[0]} {b[1]}\n")
            s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1])))
            s.SetEnd(pcbnew.VECTOR2I(MM(b[0]), MM(b[1])))
            s.SetLayer(pcbnew.Edge_Cuts)
            s.SetWidth(MM(0.05))
            board.Add(s)
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
