"""Thumb-key geometry shared by widen.py, split_thumbs.py and plate.py (upstream frame).

The thumb keys sit on one arc: the outer key is level, the middle key is the
outer key turned by STEP and moved along, and the inner key is the middle key
turned and moved by that same step again, so its corners line up with the
middle key's as the middle key's do with the outer key's. On the right half the
trackpoint holds the outer key's place, and the arc is the left one mirrored.

The inner key is split into two 1u keys, stacked one choc row (17 mm) apart
along the inner key's own up-down axis; the lower one is the arc position.

The whole cluster sits so the bottom index key reads as the arc's step before
the middle key, turned to come down from above: the middle key meets it at the
same corner gap, opening at the same 15 degrees, as it meets the inner key.
Upstream sits SHIFT short of that.

The board edge around the thumb keys runs EDGE_GAP from their keycaps.
"""
import math

ROW_PITCH = 17.0                     # choc 18 x 17 mm spacing: rows are 17 mm apart
CAP_W, CAP_H = 17.5, 16.5            # keycap across / up-down, in the key's own frame
CAP_R = 1.0                          # keycap corner radius
# Keycap to board edge wherever the edge follows keys; leaves every hot-swap
# socket pad 0.33 mm from the edge (the stock outer column had 0.95: 0.13 mm).
EDGE_GAP = 1.15

# Upstream centres and orientations of the outer and middle thumb keys.
HALVES = {
    "left": dict(outer=(92.6, 117.52, 0.0), middle=(112.65, 120.11, -15.0)),
    "right": dict(outer=(206.71, 117.52, 0.0), middle=(186.66, 120.11, 15.0)),
}
# Upstream centre of the old 1.5u inner key, which the split keys replace.
OLD_INNER = {"left": (133.25, 123.32), "right": (166.0625, 123.32)}
# Upstream centre of the bottom key of the inner index column, above the middle thumb key.
INDEX_BOTTOM = {"left": (116.5, 99.93), "right": (182.8125, 99.93)}


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


def arc(half):
    """Upstream-placed arc: [(centre, orientation)] for the outer, middle, lower
    inner and upper inner keys."""
    h = HALVES[half]
    (x0, y0, d0), (x1, y1, d1) = h["outer"], h["middle"]
    step = d1 - d0
    dx, dy = rot(x1 - x0, y1 - y0, step)          # the same turn applied to the same shift
    lower, deg = (x1 + dx, y1 + dy), d1 + step
    ux, uy = down(deg)
    upper = (lower[0] - ROW_PITCH * ux, lower[1] - ROW_PITCH * uy)
    return [((x0, y0), d0), ((x1, y1), d1), (lower, deg), (upper, deg)]


def shift(half):
    """Move from the upstream-placed arc to the index-aligned one."""
    _, (c1, d1), (c2, d2), _ = arc(half)
    side = 1 if half == "left" else -1            # +x is inward on the left half
    # Middle -> inner: the middle key's bottom inner-side corner to the inner
    # key's bottom outer-side corner, in the middle key's frame.
    a, b = corner(c1, d1, side, 1), corner(c2, d2, -side, 1)
    hinge = rot(b[0] - a[0], b[1] - a[1], -d1)
    # Index -> middle is that pairing turned a quarter, from beside to below:
    # the index key's bottom outer-side corner to the middle key's top one.
    hx, hy = rot(*hinge, -90 * side)
    ix, iy = corner(INDEX_BOTTOM[half], 0.0, -side, 1)
    tx, ty = corner(c1, d1, -side, -1)
    return (ix + hx - tx, iy + hy - ty)


def keys(half):
    """[(centre, orientation)] for the outer, middle, lower inner and upper inner keys."""
    sx, sy = shift(half)
    return [((c[0] + sx, c[1] + sy), d) for c, d in arc(half)]


def inner_keys(half):
    """(lower centre, upper centre, orientation) of the split inner keys."""
    _, _, (lower, deg), (upper, _) = keys(half)
    return lower, upper, deg
