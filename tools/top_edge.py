"""The top edge's geometry (tools/outline.py draws it): a straight slope from
the inner top corner up to the middle-finger column, flat across its top, and a
straight slope down to the outer top corner.

All three parts follow the keys: the flat top runs thumbs.EDGE_GAP above the
middle column's top key, exactly as wide as it; each slope leaves one of its
corners and passes EDGE_GAP over the top corner of the key it reaches (ring on
the outer side, inner index on the inner).
"""
import math

import stagger
import thumbs
import widen


def corner_centre(x, side):
    """Rounding centre of a column's top key's top corner (left half; side
    +1 = inner corner, -1 = outer)."""
    top = stagger.MIDDLE_TOP + stagger.COLUMNS[x] - thumbs.CAP_H / 2
    return (x + side * (thumbs.CAP_W / 2 - thumbs.CAP_R), top + thumbs.CAP_R)


SLOPE_DEG = 7.5           # both top slopes


def slopes():
    """Left half: (corner, slope) of the outer and inner slopes. The flat top runs
    EDGE_GAP above the middle column's top key. Each slope falls at SLOPE_DEG and
    clears the top corners of the keys beside it (middle and ring on the outer
    side; middle, index and inner index on the inner) by EDGE_GAP at the closest;
    the stagger (tools/stagger.py) keeps them in line with it to within 0.0002 mm.
    It meets the flat at a corner."""
    r = thumbs.CAP_R + thumbs.EDGE_GAP
    flat_y = stagger.MIDDLE_TOP - thumbs.CAP_H / 2 - thumbs.EDGE_GAP
    out = []
    for cols, side in (((80.5, 62.5), -1), ((80.5, 98.5, 116.5), 1)):
        k = math.tan(math.radians(SLOPE_DEG)) * side   # y grows away from the middle column
        # The line clearing every corner circle by r: the highest of the candidates.
        n = math.hypot(k, 1)
        b = min(c[1] - k * c[0] - r * n for c in (corner_centre(x, side) for x in cols))
        out.append((((flat_y - b) / k, flat_y), k))
    return out


def inner_line(half):
    """(point, slope) of the inner slope in the PCB frame."""
    (px, py), k = slopes()[1]
    if half == "right":
        return (widen.MIRROR_X - px + widen.RIGHT_DX, py), -k
    return (px, py), k


def on_line(half, x):
    (px, py), k = inner_line(half)
    return py + (x - px) * k
