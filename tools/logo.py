"""The Petrock logo, on the switch plate's silkscreen and the PCB's: an upright R
tucked into the corner under the middle column's bottom key, beside the ring
column, reaching toward the trackpoint.

The shape is traced on the thumb cluster as if every key filled its whole cell
(18 x 17 mm, the thumb fan hinged corner to corner, no gaps), so its angles are
exact: from the upper inner thumb key's top outer corner along that key's top
edge to the inner index column's side, down that side to its bottom corner,
across to the column's outer bottom corner, along the middle thumb key's top and
inner side, and up the inner thumb keys' outer side (two keys, 34 mm) back to
the start. Its corners are 90, 60, 90, 15, 90 and 15 degrees.

Turned upright (the long edge vertical, on the left), it stands GAP (the
board's keycap-to-edge gap) off the ring column and below the middle key, and is
as big as fits with its arm GAP short of the plate's trackpoint sensor opening.
On the PCB (top silkscreen) the left half has it upright, long edge on the left,
and the right half its mirror image. The plate is the right half's design, so
it carries the mirror image on both faces; the left plate, flipped, shows it
upright.

In the logo's open notch, at the centre of the key cell it outlines (midway
between its two arm tips), sits a DOT mm dot like the trackpoint's cap, on
the PCB and the plate.

usage: logo.py BOARD pcb|plate   (edits BOARD in place)
"""
import math
import os
import sys

import pcbnew

import outer_thumb
import plate
import stagger
import thumbs
import widen

MM = pcbnew.FromMM
GAP = thumbs.EDGE_GAP         # to the keycaps and the sensor opening, like the board's edges
MIDDLE_X = 80.5             # left half, upstream frame: the middle column


def shape():
    """Left half, upstream frame: the logo traced on the gap-free thumb cluster."""
    saved = thumbs.CAP_W, thumbs.CAP_H, thumbs.HINGE_GAP
    thumbs.CAP_W, thumbs.CAP_H, thumbs.HINGE_GAP = thumbs.CAP_W + saved[2], thumbs.CAP_H + saved[2], 0.0   # full cells
    try:
        _, (c1, d1), (c2, d2), (c3, _) = thumbs.keys("left")
        ib = thumbs.index_bottom("left")
        k = thumbs.corner
        p1 = k(c3, d2, -1, -1)
        tx, ty = k(c3, d2, 1, -1)[0] - p1[0], k(c3, d2, 1, -1)[1] - p1[1]   # that key's top edge
        x2 = k(ib, 0, 1, 1)[0]
        p2 = (x2, p1[1] + (x2 - p1[0]) / tx * ty)
        return [p1, p2, k(ib, 0, 1, 1), k(ib, 0, -1, 1), k(c1, d1, 1, -1), k(c2, d2, -1, 1)]
    finally:
        thumbs.CAP_W, thumbs.CAP_H, thumbs.HINGE_GAP = saved


def placed():
    """Left half, upstream frame: the logo upright in its corner."""
    sh = [(-x, y) for x, y in shape()]               # mirrored: the long edge on the left once upright
    p1, p6 = sh[0], sh[5]
    a = math.atan2(p6[0] - p1[0], p6[1] - p1[1])     # turn the long edge straight down
    ca, sa = math.cos(a), math.sin(a)
    sh = [((x - p1[0]) * ca - (y - p1[1]) * sa, (x - p1[0]) * sa + (y - p1[1]) * ca) for x, y in sh]
    main = stagger.main_keys()
    ring = max((k for k in main if abs(k[0][0] - stagger.RING_X) < 1e-6), key=lambda k: k[0][1])
    middle = max((k for k in main if abs(k[0][0] - MIDDLE_X) < 1e-6), key=lambda k: k[0][1])
    left = ring[0][0] + thumbs.CAP_W / 2 + GAP
    top = middle[0][1] + thumbs.CAP_H / 2 + GAP
    opening = thumbs.keys("left")[0][0][0] - outer_thumb.SENSOR_HALF_W - plate.SENSOR_MARGIN
    xs, ys = [p[0] for p in sh], [p[1] for p in sh]
    s = (opening - GAP - left) / (max(xs) - min(xs))
    return [(left + (x - min(xs)) * s, top + (y - min(ys)) * s) for x, y in sh]


DOT = 7.0                   # the dot's diameter, a trackpoint cap's


def notch_centre():
    """Left half, upstream frame: the centre of the key cell the logo's lower notch
    (its 90-degree inside corner) outlines: midway between the notch's arm tips."""
    pts = placed()
    n = len(pts)

    def turn(i):
        a, v, b = pts[i - 1], pts[i], pts[(i + 1) % n]
        u, w = (a[0] - v[0], a[1] - v[1]), (b[0] - v[0], b[1] - v[1])
        return math.degrees(math.atan2(u[0] * w[1] - u[1] * w[0], u[0] * w[0] + u[1] * w[1]))
    i = max((i for i in range(n) if abs(turn(i) - 90) < 1), key=lambda i: pts[i][1])
    a, b = pts[i - 1], pts[(i + 1) % n]
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def circle(board, centre, radius, layer, width=0.0):
    """A filled dot (width 0) or a ring of the given stroke width."""
    c = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_CIRCLE)
    c.SetCenter(pcbnew.VECTOR2I(MM(centre[0]), MM(centre[1])))
    c.SetEnd(pcbnew.VECTOR2I(MM(centre[0] + radius), MM(centre[1])))
    c.SetFilled(width == 0)
    c.SetWidth(MM(width))
    c.SetLayer(layer)
    board.Add(c)


def pcb_dots(board):
    x, y = notch_centre()
    for cx in (x, widen.MIRROR_X - x + widen.RIGHT_DX):
        circle(board, (cx, y), DOT / 2, pcbnew.F_SilkS)


def add(board, pts, layer):
    poly = pcbnew.SHAPE_POLY_SET()
    poly.NewOutline()
    for x, y in pts:
        poly.Append(MM(x), MM(y))
    g = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_POLY)
    g.SetPolyShape(poly)
    g.SetLayer(layer)
    g.SetFilled(True)
    g.SetWidth(0)
    board.Add(g)


def main(path, target):
    pts = placed()
    board = pcbnew.LoadBoard(path)
    if target == "pcb":
        add(board, pts, pcbnew.F_SilkS)
        add(board, [(widen.MIRROR_X - x + widen.RIGHT_DX, y) for x, y in pts], pcbnew.F_SilkS)
        pcb_dots(board)
    else:
        on_plate = [(widen.MIRROR_X - x + plate.PLATE_DX, y) for x, y in pts]     # the right half's design
        x, y = notch_centre()
        for layer in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            add(board, on_plate, layer)
            circle(board, (widen.MIRROR_X - x + plate.PLATE_DX, y), DOT / 2, layer)
    board.Save(path)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    print("logo %.1f x %.1f mm" % (max(xs) - min(xs), max(ys) - min(ys)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
