"""Shift the right half clear of the left, settle how far both halves widen at
their inner edge, and turn the TRRS jacks to face the top edge in the strip
beside each controller. tools/outline.py draws the widened outline.

Shifts the right half by RIGHT_DX first so the widened halves don't overlap in
the file; every later step works in the shifted frame. Coordinates below are in
the upstream frame; rx() maps right-half points.
"""
import os
import sys

import pcbnew

import thumbs

MM = pcbnew.FromMM

MIN_WIDEN = 6.2         # room beside each controller for its jack
SPLIT_X = 149.6          # halves are left/right of this line upstream
RIGHT_DX = 12.4          # right half's shift in the file; keeps the halves apart
MIRROR_X = 299.31        # upstream: the right half is the left mirrored about this
INNER_X = 146.71         # upstream left half's straight inner edge

TOP_EDGE = 56.96
JACK_PORT = 0.25         # jack origin sits this far inside its port edge
JACK_MASK_MARGIN = 0.0   # the jack pads' solder-mask opening beyond the pad (stock: the board's, wider than the gap to the pour)
JACK_PAD_LEN = 2.1       # slot pads' length along the jack (stock 2.5): 0.9 mm between data and ground
# Beside each controller, as placed for MIN_WIDEN (pads clear the edge by about
# 1 mm); any extra widening splits evenly either side of the jack (jack_x).
JACKS = {"J1": 149.39, "J3": 149.92}


def inner_widen():
    """How far the straight inner edge moves out: MIN_WIDEN, or more if the upper
    inner thumb key's keycap would otherwise come closer than thumbs.EDGE_GAP."""
    _, _, _, (c, deg) = thumbs.keys("left")
    reach = max(thumbs.corner(c, deg, sx, sy)[0] for sx in (-1, 1) for sy in (-1, 1))
    return max(MIN_WIDEN, round(reach + thumbs.EDGE_GAP - INNER_X, 3))


WIDEN = inner_widen()


def inner_x(half):
    """x of the widened straight inner edge, in the PCB frame."""
    x = INNER_X + WIDEN
    return x if half == "left" else MIRROR_X - x + RIGHT_DX


def jack_x(ref):
    """The jack's x in the upstream frame, kept centred in its widened strip."""
    extra = (WIDEN - MIN_WIDEN) / 2
    return JACKS[ref] + (extra if ref == "J1" else -extra)


def rx(p):
    """Right-half point after the half is shifted."""
    return (round(p[0] + RIGHT_DX, 2), p[1])


def V(p):
    return pcbnew.VECTOR2I(MM(p[0]), MM(p[1]))


def shift_right_half(board):
    d = V((RIGHT_DX, 0))
    items = list(board.GetFootprints()) + list(board.GetTracks()) + list(board.GetDrawings()) + list(board.Zones())
    for item in items:
        if pcbnew.ToMM(item.GetBoundingBox().Centre().x) > SPLIT_X:
            item.Move(d)


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    index = {}
    for f in board.GetFootprints():
        index.setdefault(f.GetReference(), []).append(f)
    shift_right_half(board)
    for ref in JACKS:
        x = jack_x(ref)
        (fp,) = index[ref]
        fp.SetOrientationDegrees(0)
        # The ground pad sits too close to the edge and the other pads for
        # thermal spokes, so the pour connects to it solidly.
        for pad in fp.Pads():
            if pad.GetNumber() == "C":
                pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
            # Shorter slot pads leave 0.9 mm between data and ground for hand
            # soldering (stock: 0.5 mm), with a 0.3 mm ring round the 1.5 mm slot.
            if pad.GetNumber() in ("A", "B", "C", "D"):
                size = pad.GetSize(pcbnew.F_Cu)
                pad.SetSize(pcbnew.F_Cu, pcbnew.VECTOR2I(size.x, MM(JACK_PAD_LEN)))
                # A solder-mask opening no bigger than the pad, so the mask covers
                # the pour right up to it and no bare ground shows beside the pads
                # (a hand-soldered bridge from the supply pad would short it).
                pad.SetLocalSolderMaskMargin(MM(JACK_MASK_MARGIN))
        p = (x, TOP_EDGE + JACK_PORT)
        fp.SetPosition(V(rx(p) if ref == "J3" else p))
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    # pcbnew's SWIG objects crash Python's final garbage collection.
    sys.stdout.flush()
    os._exit(0)
