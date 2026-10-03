"""Silkscreen protractor marks in the thumb cluster's three 15-degree gaps (outer
-> middle, middle -> inner, bottom index key -> middle): an arc across each
gap and its "15°" label, in the open end where the keycaps leave plate showing.

usage: angle_marks.py BOARD pcb      both halves, front silkscreen (a bare-board easter egg)
       angle_marks.py BOARD plate    the right-half plate design, both faces: the
                                     back face is the top of the flipped left plate
"""
import math
import os
import sys

import pcbnew

import thumbs
import widen

MM = pcbnew.FromMM
ARC_R, TEXT_R = 9.0, 12.5    # from each gap's vertex
TEXT_H, LINE_W = 1.0, 0.15
PLATE_DX = -4.0              # tools/plate.py: plate frame = PCB right half - RIGHT_DX + PLATE_DX


def unit(v):
    L = math.hypot(*v)
    return (v[0] / L, v[1] / L)


def intersect(p, d, q, e):
    den = d[0] * e[1] - d[1] * e[0]
    t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return (p[0] + t * d[0], p[1] + t * d[1])


def gaps():
    """Left half, upstream frame: (vertex, direction along one keycap edge, along
    the other) for each gap, the directions pointing into its open end."""
    (c0, d0), (c1, d1), (c2, d2), _ = thumbs.keys("left")
    sx, sy = thumbs.shift("left")
    index = thumbs.INDEX_BOTTOM["left"]
    k = thumbs.corner
    edges = [
        # facing edges, each as (from the hinge end, to the open end)
        ((k(c0, d0, 1, 1), k(c0, d0, 1, -1)), (k(c1, d1, -1, 1), k(c1, d1, -1, -1))),
        ((k(c1, d1, 1, 1), k(c1, d1, 1, -1)), (k(c2, d2, -1, 1), k(c2, d2, -1, -1))),
        ((k(index, 0.0, -1, 1), k(index, 0.0, 1, 1)), (k(c1, d1, -1, -1), k(c1, d1, 1, -1))),
    ]
    out = []
    for (a0, a1), (b0, b1) in edges:
        da, db = unit((a1[0] - a0[0], a1[1] - a0[1])), unit((b1[0] - b0[0], b1[1] - b0[1]))
        out.append((intersect(a0, da, b0, db), da, db))
    return out


def marks(board, layer, place, mirror_text=False):
    """place(p) maps a left-half upstream point to the board; mirrored halves
    flip the x of every direction."""
    for v, da, db in gaps():
        bis = unit((da[0] + db[0], da[1] + db[1]))
        pts = [(v[0] + ARC_R * u[0], v[1] + ARC_R * u[1]) for u in (da, bis, db)]
        a = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        a.SetArcGeometry(*(pcbnew.VECTOR2I(MM(x), MM(y)) for x, y in map(place, pts)))
        a.SetLayer(layer)
        a.SetWidth(MM(LINE_W))
        board.Add(a)
        t = pcbnew.PCB_TEXT(board)
        t.SetText("15°")
        t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(MM(TEXT_H), MM(TEXT_H)))
        t.SetTextThickness(MM(LINE_W))
        tx, ty = place((v[0] + TEXT_R * bis[0], v[1] + TEXT_R * bis[1]))
        t.SetPosition(pcbnew.VECTOR2I(MM(tx), MM(ty)))
        # Read along the gap, upright.
        bx, by = place((v[0] + bis[0], v[1] + bis[1]))
        ox, oy = place(v)
        ang = -math.degrees(math.atan2(by - oy, bx - ox))
        if ang > 90 or ang < -90:
            ang += 180
        t.SetTextAngleDegrees(ang)
        t.SetMirrored(mirror_text)
        board.Add(t)


def main(path, target):
    board = pcbnew.LoadBoard(path)
    right = lambda p: (widen.MIRROR_X - p[0] + widen.RIGHT_DX, p[1])
    if target == "pcb":
        marks(board, pcbnew.F_SilkS, lambda p: p)
        marks(board, pcbnew.F_SilkS, right)
    else:
        plate = lambda p: (right(p)[0] - widen.RIGHT_DX + PLATE_DX, p[1])
        marks(board, pcbnew.F_SilkS, plate)
        marks(board, pcbnew.B_SilkS, plate, mirror_text=True)
    board.Save(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
