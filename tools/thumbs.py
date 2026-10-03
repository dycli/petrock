"""Thumb-key geometry shared by widen.py, split_thumbs.py and plate.py (upstream frame).

The thumb keys sit on one arc: the outer key is level, the middle key is the
outer key turned by STEP and moved along, and the inner key is the middle key
turned and moved by that same step again, so its corners line up with the
middle key's as the middle key's do with the outer key's. On the right half the
trackpoint holds the outer key's place, and the arc is the left one mirrored.

The inner key is split into two 1u keys, stacked one choc row (17 mm) apart
along the inner key's own up-down axis; the lower one is the arc position.

The board edge around the thumb keys runs EDGE_GAP from their keycaps.
"""
import math

ROW_PITCH = 17.0                     # choc 18 x 17 mm spacing: rows are 17 mm apart
CAP_W, CAP_H = 17.5, 16.5            # keycap across / up-down, in the key's own frame
CAP_R = 1.0                          # keycap corner radius
EDGE_GAP = 0.95                      # keycap to board edge, as on the outer column

# Upstream centres and orientations of the outer and middle thumb keys.
HALVES = {
    "left": dict(outer=(92.6, 117.52, 0.0), middle=(112.65, 120.11, -15.0)),
    "right": dict(outer=(206.71, 117.52, 0.0), middle=(186.66, 120.11, 15.0)),
}
# Upstream centre of the old 1.5u inner key, which the split keys replace.
OLD_INNER = {"left": (133.25, 123.32), "right": (166.0625, 123.32)}


def rot(x, y, deg):
    """Rotate a vector the way KiCad rotates footprints (CCW on screen, y down)."""
    a = math.radians(deg)
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


def down(deg):
    """Unit vector from a key's centre toward its keycap's bottom edge."""
    return rot(0, 1, deg)


def keys(half):
    """[(centre, orientation)] for the outer, middle, lower inner and upper inner keys."""
    h = HALVES[half]
    (x0, y0, d0), (x1, y1, d1) = h["outer"], h["middle"]
    step = d1 - d0
    dx, dy = rot(x1 - x0, y1 - y0, step)          # the same turn applied to the same shift
    lower, deg = (x1 + dx, y1 + dy), d1 + step
    ux, uy = down(deg)
    upper = (lower[0] - ROW_PITCH * ux, lower[1] - ROW_PITCH * uy)
    return [((x0, y0), d0), ((x1, y1), d1), (lower, deg), (upper, deg)]


def inner_keys(half):
    """(lower centre, upper centre, orientation) of the split inner keys."""
    _, _, (lower, deg), (upper, _) = keys(half)
    return lower, upper, deg
