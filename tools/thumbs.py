"""Thumb-key geometry shared by widen.py, split_thumbs.py and plate.py (upstream frame).

The thumb keys sit on one arc: the outer key is level, the middle key is the
outer key turned by STEP and moved along, and the inner key is the middle key
turned and moved by that same step again, so its corners line up with the
middle key's as the middle key's do with the outer key's. On the right half the
trackpoint holds the outer key's place, and the arc is the left one mirrored.

The inner key is split into two 1u keys, stacked one choc row (17 mm) apart
along the inner key's own up-down axis; the lower one is the arc position.

The bottom index key reads as the arc's step before the middle key, turned to
come down from above. Every step turns 15 degrees about a hinge where the two
keys' facing corners sit level, HINGE_GAP apart, as between ordinary columns.

The board edge around the thumb keys runs EDGE_GAP from their keycaps.
"""
import math

ROW_PITCH = 17.0                     # choc 18 x 17 mm spacing: rows are 17 mm apart
CAP_W, CAP_H = 17.5, 16.5            # keycap across / up-down, in the key's own frame
# Keycap corner radius the edges are worked out for: none, i.e. square corners,
# the worst case. Gaps are then set by the keycap's edges, and any real cap,
# however rounded, sits at least EDGE_GAP from the board edge everywhere.
CAP_R = 0.0
# Keycap to board edge wherever the edge follows keys; leaves every hot-swap
# socket pad 0.33 mm from the edge (the stock outer column had 0.95: 0.13 mm).
EDGE_GAP = 1.15
HINGE_GAP = 0.5                      # between neighbouring thumb keys' facing corners, as between columns

# Upstream centres and orientations of the outer and middle thumb keys.
HALVES = {
    "left": dict(outer=(92.6, 117.52, 0.0), middle=(112.65, 120.11, -15.0)),
    "right": dict(outer=(206.71, 117.52, 0.0), middle=(186.66, 120.11, 15.0)),
}
# Upstream centre of the old 1.5u inner key, which the split keys replace.
OLD_INNER = {"left": (133.25, 123.32), "right": (166.0625, 123.32)}
# x of the inner index column, whose bottom key sits above the middle thumb key.
INDEX_X = {"left": 116.5, "right": 182.8125}


def index_bottom(half):
    """Centre of the inner index column's bottom key, on tools/stagger.py's stagger."""
    import stagger                               # (stagger.py imports this module)
    return (INDEX_X[half], stagger.MIDDLE_TOP + stagger.COLUMNS[116.5] + 2 * ROW_PITCH)


def rot(x, y, deg):
    """Rotate a vector the way KiCad rotates footprints (CCW on screen, y down)."""
    a = math.radians(deg)
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


def down(deg):
    """Unit vector from a key's centre toward its keycap's bottom edge."""
    return rot(0, 1, deg)


def corner(c, deg, sx, sy):
    """A keycap's corner: sx, sy = -1/+1 in the key's own frame."""
    dx, dy = rot(sx * CAP_W / 2, sy * CAP_H / 2, deg)
    return (c[0] + dx, c[1] + dy)


def keys(half):
    """[(centre, orientation)] for the outer, middle, lower inner and upper inner
    keys. Each step along the arc (bottom index key -> middle, outer -> middle,
    middle -> inner) turns 15 degrees about a hinge where the two keys' facing
    corners sit level, HINGE_GAP apart: the same gap as between ordinary keys."""
    side = 1 if half == "left" else -1            # +x is inward on the left half
    d0, d1 = HALVES[half]["outer"][2], HALVES[half]["middle"][2]
    d2 = 2 * d1 - d0
    g = HINGE_GAP
    # Middle: its top outer corner g below the bottom index key's bottom outer corner.
    ix, iy = corner(index_bottom(half), 0.0, -side, 1)
    ox, oy = rot(-side * CAP_W / 2, -CAP_H / 2, d1)
    c1 = (ix - ox, iy + g - oy)
    # Inner: its bottom outer corner g along from the middle key's bottom inner one.
    mx, my = corner(c1, d1, side, 1)
    hx, hy = rot(side * g, 0, d1)
    ox, oy = rot(-side * CAP_W / 2, CAP_H / 2, d2)
    c2 = (mx + hx - ox, my + hy - oy)
    # Outer: the middle key's bottom outer corner g along from its bottom inner one.
    mx, my = corner(c1, d1, -side, 1)
    c0 = (mx - side * g - side * CAP_W / 2, my - CAP_H / 2)
    ux, uy = down(d2)
    c3 = (c2[0] - ROW_PITCH * ux, c2[1] - ROW_PITCH * uy)
    return [(c0, d0), (c1, d1), (c2, d2), (c3, d2)]


def moves(half):
    """How far the outer and middle keys move from upstream."""
    (c0, _), (c1, _), _, _ = keys(half)
    h = HALVES[half]
    return {"outer": (c0[0] - h["outer"][0], c0[1] - h["outer"][1]),
            "middle": (c1[0] - h["middle"][0], c1[1] - h["middle"][1])}


def inner_keys(half):
    """(lower centre, upper centre, orientation) of the split inner keys."""
    _, _, (lower, deg), (upper, _) = keys(half)
    return lower, upper, deg
