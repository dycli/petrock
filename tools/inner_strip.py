"""Fit the controller corner to the inner top slope (tools/top_edge.py), which
now sits lower at the inner edge: the controller (with the OLED header that
goes with it) drops until its circuit board's top inner corner, where the slope
is lowest, is INSET inside the edge (the USB connector overhangs), the jack's
housing likewise (its round port overhangs), and the
reset button moves into the strip beside the
controller, just below the jack, where the switch plate leaves it reachable.

usage: inner_strip.py IN OUT
"""
import os
import sys

import pcbnew

import parts
import thumbs
import top_edge
import widen

MM = pcbnew.FromMM
PARTS = {   # controller, OLED header, jack, reset button
    "left": ("U1", "J2", "J1", "RSW1"),
    "right": ("U2", "J4", "J3", "RSW2"),
}
INSET = thumbs.EDGE_GAP    # controller's and jack's top inner corners inside the edge, like the keys
RESET_BELOW_JACK = 2.0     # reset button's pads below the jack's
# The jack's square housing (from its 3D model, PJ320A): 6 mm wide, centred on the
# footprint origin, its port end at the origin; the round port sticks out 2 mm past it.
JACK_HALF_W = 3.0


def mm(v):
    return pcbnew.ToMM(v)


def pads_box(f):
    bb = [p.GetBoundingBox() for p in f.Pads()]
    return (mm(min(b.GetLeft() for b in bb)), mm(min(b.GetTop() for b in bb)),
            mm(max(b.GetRight() for b in bb)), mm(max(b.GetBottom() for b in bb)))


def fab_box(f):
    bb = [g.GetBoundingBox() for g in f.GraphicalItems() if g.GetLayer() == pcbnew.F_Fab]
    return (mm(min(b.GetLeft() for b in bb)), mm(min(b.GetTop() for b in bb)),
            mm(max(b.GetRight() for b in bb)), mm(max(b.GetBottom() for b in bb)))


def place(board, half):
    refs = PARTS[half]
    fp = {f.GetReference(): f for f in board.GetFootprints() if f.GetReference() in refs}
    u, oled, jack, reset = (fp[r] for r in refs)
    # Controller (and its OLED header): its top inner corner just inside the edge.
    x0, top, x1, _ = fab_box(u)
    dy = top_edge.on_line(half, x1 if half == "left" else x0) + INSET - top
    # With its copper: the tracks among its pins and the header's, and those
    # running above it (the slope would cut them off), move whole; the ones
    # leading away stretch (tools/parts.py drag).
    bx0, by0, bx1, by1 = (min(a, b) if i < 2 else max(a, b) for i, (a, b) in enumerate(zip(pads_box(u), pads_box(oled))))
    parts.drag(board, [u, oled], parts.shift(0, dy),
               inside=lambda p: bx0 - 1 <= p[0] <= bx1 + 1 and p[1] <= by1 + 1)
    # Jack: likewise, its housing's top inner corner INSET inside the edge (the
    # round port beyond it overhangs, like the controller's USB connector).
    jx, jy = mm(jack.GetPosition().x), mm(jack.GetPosition().y)
    corner_x = jx + JACK_HALF_W if half == "left" else jx - JACK_HALF_W
    parts.drag(board, [jack], parts.shift(0, top_edge.on_line(half, corner_x) + INSET - jy))
    # Reset button: centred in the strip between the controller's pins and the
    # inner edge, just below the jack.
    ux0, _, ux1, _ = pads_box(u)
    edge_x = widen.inner_x(half)
    strip = (ux1, edge_x) if half == "left" else (edge_x, ux0)
    rx0, ry0, rx1, ry1 = pads_box(reset)
    _, _, _, jack_bottom = pads_box(jack)
    target = ((strip[0] + strip[1]) / 2, jack_bottom + RESET_BELOW_JACK + (ry1 - ry0) / 2)
    centre = ((rx0 + rx1) / 2, (ry0 + ry1) / 2)
    parts.drag(board, [reset], parts.shift(target[0] - centre[0], target[1] - centre[1]))
    return dy


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    for half in PARTS:
        print(half, "controller drops", round(place(board, half), 2), "mm")
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
