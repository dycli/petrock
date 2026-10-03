"""Replace each half's stepped top edge with a peak: a straight slope from the
inner top corner up to the middle-finger column, flat across its top, and a
straight slope down to the outer top corner.

PEAKS holds each half's four points in the PCB frame (inner ends as for a 6.2 mm
widening); both ends then slide along their slopes to the side edges where
tools/widen.py left them, and those edges' top ends meet them.
"""
import os
import sys

import pcbnew

import thumbs
import widen

MM = pcbnew.FromMM

PEAKS = {
    # side edge's top end, middle column's two top corners, other side edge's top end
    "left": [(16.8, 60.92), (70.52, 51.47), (90.48, 51.47), (152.91, 57.46)],
    "right": [(158.8, 57.46), (221.23, 51.47), (241.19, 51.47), (294.91, 60.92)],
}
TOP_Y = 61.0             # every stepped top-edge segment lies above this


def mm(v):
    return round(pcbnew.ToMM(v.x), 2), round(pcbnew.ToMM(v.y), 2)


def slide_end(pts, x):
    """pts with whichever end is nearer x slid along its slope to x."""
    (x0, y0), (x1, y1) = (pts[0], pts[1]) if abs(pts[0][0] - x) < abs(pts[-1][0] - x) else (pts[-1], pts[-2])
    end = (round(x, 3), round(y0 + (x - x0) * (y1 - y0) / (x1 - x0), 3))
    return [end] + pts[1:] if (x0, y0) == pts[0] else pts[:-1] + [end]


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    # Where tools/widen.py left each half's side edges: outer, then inner.
    left_out = widen.OUTER_COL_X - thumbs.CAP_W / 2 - thumbs.EDGE_GAP
    left_in = widen.EDGES["left"][1][0][0] + widen.WIDEN
    sides = {"left": [(PEAKS["left"][0], left_out), (PEAKS["left"][-1], left_in)],
             "right": [(PEAKS["right"][-1], widen.MIRROR_X - left_out + widen.RIGHT_DX),
                       (PEAKS["right"][0], widen.EDGES["right"][1][0][0] - widen.WIDEN + widen.RIGHT_DX)]}
    peaks = {}
    for h, pts in PEAKS.items():
        for _, x in sides[h]:
            pts = slide_end(pts, x)
        peaks[h] = pts
    # The side edges' top ends rise or drop to the slid ends.
    for d in board.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShapeStr() == "Line":
            for h, ends in sides.items():
                for old, x in ends:
                    end = min(peaks[h][0], peaks[h][-1], key=lambda p: abs(p[0] - x))
                    for get, put in ((d.GetStart, d.SetStart), (d.GetEnd, d.SetEnd)):
                        if mm(get()) == (round(x, 2), old[1]):
                            put(pcbnew.VECTOR2I(MM(end[0]), MM(end[1])))
    doomed = []
    for d in board.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts:
            continue
        (ax, ay), (bx, by) = mm(d.GetStart()), mm(d.GetEnd())
        for pts in peaks.values():
            if max(ay, by) < TOP_Y and pts[0][0] - 0.01 <= min(ax, bx) and max(ax, bx) <= pts[-1][0] + 0.01:
                doomed.append(d)
    for d in doomed:          # removing invalidates other handles, so all at once
        board.Remove(d)
    record = open(os.environ["NEW_EDGES"], "a") if os.environ.get("NEW_EDGES") else None
    for pts in peaks.values():
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
