"""Nudge copper the new outline crowds back inside it instead of cutting it.

Every track corner and via closer to the board edge than the edge clearance
(plus half its width) moves straight in from the nearest edge by the shortfall,
up to MAX_SHIFT; the tracks meeting there stretch with it, as when dragging a
corner in KiCad. Track ends on pads stay. Copper further out is
tools/trim.py's.

usage: edge_fit.py BOARD   (edits BOARD in place; prints the count moved)
"""
import math
import os
import sys

import pcbnew

EDGE_CLEAR = 0.5 + 0.02     # board rule, with a little margin
MAX_SHIFT = 1.0


def mm(v):
    return (pcbnew.ToMM(v.x), pcbnew.ToMM(v.y))


def nearest(p, segments):
    """(distance, unit normal from the edge toward p) to the nearest edge segment."""
    best = None
    for (ax, ay), (bx, by) in segments:
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2)) if L2 else 0.0
        qx, qy = ax + t * dx, ay + t * dy
        d = math.hypot(p[0] - qx, p[1] - qy)
        if best is None or d < best[0]:
            best = (d, (qx, qy), (dx, dy))
    return best


def main(path):
    board = pcbnew.LoadBoard(path)
    segments = [(mm(d.GetStart()), mm(d.GetEnd())) for d in board.GetDrawings()
                if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_SEGMENT]
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline, False)
    pads = [p for f in board.GetFootprints() for p in f.Pads()]
    on_pad = lambda v: any(p.HitTest(v) for p in pads)
    V = lambda p: pcbnew.VECTOR2I(pcbnew.FromMM(p[0]), pcbnew.FromMM(p[1]))
    tracks = list(board.GetTracks())
    # Each corner's move: the largest any copper at it needs.
    moves = {}
    for t in tracks:
        ends = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
        half = pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu) if t.GetClass() == "PCB_VIA" else t.GetWidth()) / 2
        for v in ends:
            p = mm(v)
            d, q, (dx, dy) = nearest(p, segments)
            inside = outline.Contains(v)
            short = EDGE_CLEAR + half - (d if inside else -d)
            if short <= 0 or short > MAX_SHIFT or on_pad(v):
                continue
            L = math.hypot(dx, dy)
            n = (-dy / L, dx / L)
            probe = V((q[0] + n[0] * 0.1, q[1] + n[1] * 0.1))
            if not outline.Contains(probe):
                n = (-n[0], -n[1])
            key = (v.x, v.y)
            if short > moves.get(key, (0, None))[0]:
                moves[key] = (short, (p[0] + n[0] * short, p[1] + n[1] * short))
    for t in tracks:
        if t.GetClass() == "PCB_VIA":
            m = moves.get((t.GetPosition().x, t.GetPosition().y))
            if m:
                t.SetPosition(V(m[1]))
            continue
        for get, set_ in ((t.GetStart, t.SetStart), (t.GetEnd, t.SetEnd)):
            m = moves.get((get().x, get().y))
            if m:
                set_(V(m[1]))
    board.Save(path)
    print(len(moves))


if __name__ == "__main__":
    main(sys.argv[1])
    sys.stdout.flush()
    os._exit(0)
