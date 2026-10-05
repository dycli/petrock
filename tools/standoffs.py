"""Move the two standoffs that sat between the two pinky columns: the lower one
to the nearest clear spot to TARGET, under the ring column's fourth key, and the
upper one to the nearest clear spot to TOP_TARGET, up in the outer top corner,
so both ends of the board stay supported (five per half, as stock); and move any standoff
the logo (tools/logo.py) would cover to the nearest clear spot outside it. Each
move is mirrored on the two halves.

usage: standoffs.py IN OUT
"""
import math
import os
import sys

import pcbnew

import logo
import parts
import stagger
import thumbs
import widen

MM = pcbnew.FromMM
# Left half, upstream frame. Where the pinky and ring columns meet: between their
# top two rows and between their bottom two rows, as stock's two between its
# pinky columns. And the one by the trackpoint, low, below the line from the
# thumb standoff to the bottom outer one (not in line with them).
# Each one between four keys sits at their centre: halfway between the two
# columns, and halfway between the two columns' row gaps (they're staggered).
def centre(x0, x1, row):
    gap = lambda x: stagger.MIDDLE_TOP + stagger.COLUMNS[x] + (row + 0.5) * thumbs.ROW_PITCH
    return ((x0 + x1) / 2, (gap(x0) + gap(x1)) / 2)


TOP_TARGET = centre(stagger.INNER_PINKY_X, stagger.RING_X, 0)        # pinky | ring, rows 1-2
TARGET = centre(stagger.INNER_PINKY_X, stagger.RING_X, 2)            # pinky | ring, rows 3-4
INDEX_TARGET = centre(98.5, stagger.INNER_INDEX_X, 0)                 # index | inner index, rows 1-2
INDEX_BOTTOM_TARGET = centre(98.5, stagger.INNER_INDEX_X, 2)          # index | inner index, below row 3
# The four make a rectangle: the pinky sits a step below the ring column and the
# inner index a step below the index, so both bottom centres share a height.
def thumb_target():
    """The thumb one: equally far from the three keycap corners round it (the inner
    index column's bottom key, the middle thumb key, the upper inner thumb key)."""
    near = (125.73, 113.73)                    # stock's, among those corners
    index = ((stagger.INNER_INDEX_X, stagger.MIDDLE_TOP + stagger.COLUMNS[stagger.INNER_INDEX_X] + 2 * thumbs.ROW_PITCH), 0.0)
    keys = thumbs.keys("left")
    a, b, c = (min((thumbs.corner(k, deg, sx, sy) for sx in (-1, 1) for sy in (-1, 1)),
                   key=lambda p: math.hypot(p[0] - near[0], p[1] - near[1]))
               for k, deg in (index, keys[1], keys[3]))
    d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
    sq = lambda p: p[0] ** 2 + p[1] ** 2
    return ((sq(a) * (b[1] - c[1]) + sq(b) * (c[1] - a[1]) + sq(c) * (a[1] - b[1])) / d,
            (sq(a) * (c[0] - b[0]) + sq(b) * (a[0] - c[0]) + sq(c) * (b[0] - a[0])) / d)
GAP = 0.5                   # its pad to any other pad
EDGE = 3.0                  # its centre inside the board edge
REACH, STEP = 12.0, 0.25
LOGO_CLEAR = 1.5            # its pad to the logo (its screw head then clears it by about 1.25)


def body(f):
    c = f.GetCourtyard(pcbnew.B_CrtYd)
    if c.OutlineCount():
        return c
    bb = f.GetBoundingBox(False)
    p = pcbnew.SHAPE_POLY_SET()
    p.NewOutline()
    for x, y in ((bb.GetLeft(), bb.GetTop()), (bb.GetRight(), bb.GetTop()), (bb.GetRight(), bb.GetBottom()), (bb.GetLeft(), bb.GetBottom())):
        p.Append(x, y)
    return p


def clear(board, f, outline):
    (pad,) = list(f.Pads())
    hole = pad.GetEffectiveShape(pcbnew.B_Cu)
    for o in board.GetFootprints():
        if o.m_Uuid == f.m_Uuid:
            continue
        for p in o.Pads():
            for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                if (p.IsOnLayer(layer) or p.GetDrillSizeX() > 0) and p.GetEffectiveShape(layer).Collide(hole, MM(GAP)):
                    return False
        if o.IsFlipped() and body(o).Collide(pad.GetPosition(), pad.GetBoundingBox().GetWidth() // 2):
            return False
    return outline.Contains(f.GetPosition())


def off_logo(f, mark):
    """f's pad is LOGO_CLEAR off the logo (both halves' copies are given)."""
    (pad,) = list(f.Pads())
    c = pad.GetPosition()
    r = pad.GetBoundingBox().GetWidth() // 2 + MM(LOGO_CLEAR)
    return not any(m.Collide(c, r) for m in mark)


def blockers(board, f):
    """Footprints whose pads or courtyard keep f's spot from being clear."""
    (pad,) = list(f.Pads())
    hole = pad.GetEffectiveShape(pcbnew.B_Cu)
    out = []
    for o in board.GetFootprints():
        if o.m_Uuid == f.m_Uuid:
            continue
        hit = any((p.IsOnLayer(layer) or p.GetDrillSizeX() > 0) and p.GetEffectiveShape(layer).Collide(hole, MM(GAP))
                  for p in o.Pads() for layer in (pcbnew.F_Cu, pcbnew.B_Cu))
        if hit or (o.IsFlipped() and body(o).Collide(pad.GetPosition(), pad.GetBoundingBox().GetWidth() // 2)):
            out.append(o)
    return out


def nudge_diodes(board, f):
    """If only key diodes block f's spot, slide each straight away from f (its
    copper dragged along) until it clears. Returns whether f's spot is clear."""
    for _ in range(40):
        hits = blockers(board, f)
        if not hits:
            return True
        if any(not o.GetReference().startswith("D") for o in hits):
            return False
        for o in hits:
            print(f"  nudging {o.GetReference()} clear of the standoff")
            c, d = f.GetPosition(), o.GetPosition()
            v = (pcbnew.ToMM(d.x - c.x), pcbnew.ToMM(d.y - c.y))
            n = math.hypot(*v) or 1.0
            parts.drag(board, [o], parts.shift(0.05 * v[0] / n, 0.05 * v[1] / n))
    return False


def move(board, pair, target, outline, mark):
    left, right = pair
    mirror = lambda v: widen.MIRROR_X - v + widen.RIGHT_DX
    # The exact spot first, making room by nudging key diodes if that's all it takes.
    left.SetPosition(pcbnew.VECTOR2I(MM(target[0]), MM(target[1])))
    right.SetPosition(pcbnew.VECTOR2I(MM(mirror(target[0])), MM(target[1])))
    if all(outline.Contains(f.GetPosition()) and off_logo(f, mark) and nudge_diodes(board, f) for f in (left, right)):
        return target
    n = int(REACH / STEP)
    for _, i, j in sorted((math.hypot(i, j), i, j) for i in range(-n, n + 1) for j in range(-n, n + 1) if math.hypot(i, j) * STEP <= REACH):
        px, py = target[0] + i * STEP, target[1] + j * STEP
        left.SetPosition(pcbnew.VECTOR2I(MM(px), MM(py)))
        right.SetPosition(pcbnew.VECTOR2I(MM(mirror(px)), MM(py)))
        if all(clear(board, f, outline) and off_logo(f, mark) for f in (left, right)):
            return px, py
    raise SystemExit(f"no room for a standoff near {target}")


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline, False)
    outline.Deflate(MM(EDGE), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
    mark = []
    for pts in (logo.placed(), [(widen.MIRROR_X - x + widen.RIGHT_DX, y) for x, y in logo.placed()]):
        poly = pcbnew.SHAPE_POLY_SET()
        poly.NewOutline()
        for x, y in pts:
            poly.Append(MM(x), MM(y))
        mark.append(poly)
    spacers = [f for f in board.GetFootprints() if f.GetFPIDAsString() == "holykeebs:M2_SPACER"]
    x = lambda f: pcbnew.ToMM(f.GetPosition().x)
    y = lambda f: pcbnew.ToMM(f.GetPosition().y)
    mirror = lambda v: widen.MIRROR_X - v + widen.RIGHT_DX
    twin = lambda f: min(spacers, key=lambda o: math.hypot(x(o) - mirror(x(f)), y(o) - y(f)))
    # The two standoffs that sat between the pinky columns go where the pinky and
    # ring columns meet, top and bottom; the one stock had below the ring column
    # goes low by the trackpoint.
    upper, lower = sorted(sorted(spacers, key=x)[:2], key=y)
    left = [f for f in spacers if x(f) < widen.SPLIT_X]
    mid = min(left, key=lambda f: math.hypot(x(f) - 76.41, y(f) - 109.18))   # stock's bottom middle one, moved to the index bottom
    index = min(left, key=lambda f: math.hypot(x(f) - 107.25, y(f) - 72.05))   # stock's, between index and inner index
    thumb = min(left, key=lambda f: math.hypot(x(f) - 125.73, y(f) - 113.73))  # stock's, by the thumbs
    for f, target, name in ((upper, TOP_TARGET, "outer top"), (lower, TARGET, "outer bottom"),
                            (index, INDEX_TARGET, "index top"), (thumb, thumb_target(), "thumb"),
                            (mid, INDEX_BOTTOM_TARGET, "index bottom")):
        px, py = move(board, (f, twin(f)), target, outline, mark)
        print(f"{name} standoff: {px:.2f}, {py:.2f}")
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
