"""Lay out each half's controller corner: across the strip between the inner
index keycaps and the inner edge, the controller (a nice!nano's board) and the
jack's body sit with even gaps (keycap, controller, jack, edge); each drops
until its square top inner corner is EDGE_GAP inside the inner top slope
(tools/top_edge.py), measured square to it as for the keycaps. The USB
connector and the jack's round port overhang, as intended. The OLED header
moves with the controller, and the reset button sits centred under the jack.

Part sizes from their 3D models: the nice!nano's board is 17.78 x 33.0 mm, its
USB end 3.79 mm beyond the pin nearest it (Nice_Nano_V2.step in infused-kim's
kb_ergogen_fp, measured); the PJ320A jack's body is 6.0 mm wide, its front
face at the footprint's origin, the round port 2 mm beyond it.

usage: inner_strip.py IN OUT
"""
import math
import os
import sys

import pcbnew

import parts
import stagger
import thumbs
import top_edge
import widen

MM = pcbnew.FromMM
PARTS = {   # controller, OLED header, jack, reset button
    "left": ("U1", "J2", "J1", "RSW1"),
    "right": ("U2", "J4", "J3", "RSW2"),
}
RESET_BELOW_JACK = 2.0     # reset button's pads below the jack's
CONTROLLER_W = 17.78       # nice!nano board
CONTROLLER_USB_END = 3.79  # board's USB end beyond the nearest pin
JACK_W = 6.0               # PJ320A body; the footprint origin is its front face, centred


def mm(v):
    return pcbnew.ToMM(v)


def pads_box(f):
    bb = [p.GetBoundingBox() for p in f.Pads()]
    return (mm(min(b.GetLeft() for b in bb)), mm(min(b.GetTop() for b in bb)),
            mm(max(b.GetRight() for b in bb)), mm(max(b.GetBottom() for b in bb)))


def slope_gap(half, x, y):
    """How far (x, y) sits inside the inner top slope, square to it."""
    (_, _), k = top_edge.inner_line(half)
    return (y - top_edge.on_line(half, x)) / math.hypot(1, k)


def place(board, half):
    side = 1 if half == "left" else -1             # +x is inward on the left half
    refs = PARTS[half]
    fp = {f.GetReference(): f for f in board.GetFootprints() if f.GetReference() in refs}
    u, oled, jack, reset = (fp[r] for r in refs)
    # Across the strip: keycap edge, gap, controller, gap, jack body, gap, board edge.
    index_x = stagger.INNER_INDEX_X if half == "left" else widen.MIRROR_X - stagger.INNER_INDEX_X + widen.RIGHT_DX
    keycap = index_x + side * thumbs.CAP_W / 2
    edge = widen.inner_x(half)
    gap = (abs(edge - keycap) - CONTROLLER_W - JACK_W) / 3
    u_centre = keycap + side * (gap + CONTROLLER_W / 2)
    j_centre = keycap + side * (2 * gap + CONTROLLER_W + JACK_W / 2)
    # Controller: its board's top inner corner EDGE_GAP inside the slope.
    px0, py0, px1, _ = pads_box(u)
    pin_y = min(pcbnew.ToMM(p.GetPosition().y) for p in u.Pads())
    cx = (px0 + px1) / 2
    top = pin_y - CONTROLLER_USB_END
    corner = u_centre + side * CONTROLLER_W / 2
    dx = u_centre - cx
    dy = thumbs.EDGE_GAP - slope_gap(half, corner, top)
    # (solve for the drop exactly: moving down by d moves the corner d * cos square to the slope)
    (_, _), k = top_edge.inner_line(half)
    dy *= math.hypot(1, k)
    # With its copper: the tracks among its pins and the header's, and those
    # running above it, move whole; the ones leading away stretch (tools/parts.py drag).
    bx0, by0, bx1, by1 = (min(a, b) if i < 2 else max(a, b) for i, (a, b) in enumerate(zip(pads_box(u), pads_box(oled))))
    parts.drag(board, [u, oled], parts.shift(dx, dy),
               inside=lambda p: bx0 - 1 <= p[0] <= bx1 + 1 and p[1] <= by1 + 1)
    # Jack: its body's top inner corner EDGE_GAP inside the slope.
    jx, jy = mm(jack.GetPosition().x), mm(jack.GetPosition().y)
    j_corner = j_centre + side * JACK_W / 2
    jdy = (thumbs.EDGE_GAP - slope_gap(half, j_corner, jy)) * math.hypot(1, k)
    parts.drag(board, [jack], parts.shift(j_centre - jx, jdy))
    # Reset button: centred under the jack.
    rx0, ry0, rx1, ry1 = pads_box(reset)
    _, _, _, jack_bottom = pads_box(jack)
    target = (j_centre, jack_bottom + RESET_BELOW_JACK + (ry1 - ry0) / 2)
    centre = ((rx0 + rx1) / 2, (ry0 + ry1) / 2)
    parts.drag(board, [reset], parts.shift(target[0] - centre[0], target[1] - centre[1]))
    return dx, dy, gap


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    for half in PARTS:
        dx, dy, gap = place(board, half)
        print(f"{half}: gaps {gap:.2f} mm; controller moves {dx:+.2f}, drops {dy:.2f} mm")
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
