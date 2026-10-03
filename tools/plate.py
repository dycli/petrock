"""Switch plate for the split inner thumb keys (one design, flipped for the left half).

Replaces the inner 1.5u opening with two 1u openings at the new key centres and
grows the outline to cover them, without reaching past the PCB's angled edge.
The plate frame is the upstream PCB's right-half frame shifted by PLATE_DX.
"""
import math
import os
import sys

import pcbnew

MM = pcbnew.FromMM
PLATE_DX = -4.0
KEY_1_5U = "SW21"        # in the plate file
TEMPLATE_1U = "SW20"
# Upstream-frame centres of the two 1u keys (tools/split_thumbs.py, right half).
OLD = (166.0625, 123.32)
DEG = -60.0
PITCH = 18.0
MARGIN = 1.0             # plate beyond each key's 18 x 17 mm pitch box
OLD_CORNER = (167.81, 104.03)   # upstream plate: foot of the inner straight edge
# Peaked top edge (tools/top_edge.py), in the plate frame: from the plate's own
# inner top corner up to the middle-finger column, across it, down to the outer corner.
PEAK = [(167.81, 57.47), (204.83, 51.47), (224.79, 51.47), (278.51, 60.92)]
RIGHT_DX = 12.4          # tools/widen.py: right half shift in the PCB file


def rot(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


def key_centres():
    ux, uy = rot(1, 0, DEG)
    if uy < 0:
        ux, uy = -ux, -uy
    lower = (OLD[0] + PITCH * 0.25 * ux, OLD[1] + PITCH * 0.25 * uy)
    upper = (lower[0] - PITCH * ux, lower[1] - PITCH * uy)
    return [(x + PLATE_DX, y) for x, y in (lower, upper)]


def box(cx, cy, w, h, deg):
    p = pcbnew.SHAPE_POLY_SET()
    p.NewOutline()
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        dx, dy = rot(sx * w / 2, sy * h / 2, deg)
        p.Append(MM(cx + dx), MM(cy + dy))
    return p


def line_intersect(p, d, q, e):
    den = d[0] * e[1] - d[1] * e[0]
    t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return p[0] + t * d[0], p[1] + t * d[1]


def bevel(upper):
    """Fill the notch between the upper key and the old plate's straight inner
    edge: one level line from the key area's corner across to that edge.
    (Carrying the key's top edge on instead would pass 0.26 mm from the right
    OLED header.)"""
    cx, cy = upper
    ux, uy = rot(1, 0, DEG)
    if uy < 0:
        ux, uy = -ux, -uy
    vx, vy = -uy, ux                      # across the key, toward the old outline
    if vx < 0:
        vx, vy = -vx, -vy
    hl, hw = PITCH / 2 + MARGIN, 17 / 2 + MARGIN
    a = (cx - hl * ux + hw * vx, cy - hl * uy + hw * vy)     # key area corner nearest the old edge
    d = line_intersect(a, (ux, uy), OLD_CORNER, (-vx, -vy))  # down the key side to the old diagonal edge
    p = pcbnew.SHAPE_POLY_SET()
    p.NewOutline()
    ox, oy = OLD_CORNER[0] + 0.3, OLD_CORNER[1] + 0.2     # overlap the old plate so the union has no seam
    for x, y in (a, (ox, a[1]), (ox, oy), d):
        p.Append(MM(x), MM(y))
    return p


def polygon(points):
    p = pcbnew.SHAPE_POLY_SET()
    p.NewOutline()
    for x, y in points:
        p.Append(MM(x), MM(y))
    return p


def peak(plate):
    """Replace the stepped top edge with PEAK."""
    (x0, _), (x1, _) = PEAK[0], PEAK[-1]
    plate.BooleanAdd(polygon(PEAK + [(x1, 75.0), (x0, 75.0)]))
    plate.BooleanSubtract(polygon(PEAK + [(x1, 0.0), (x0, 0.0)]))


def pcb_outline(path):
    """The edited PCB's right-half outline, moved into the plate frame."""
    pcb = pcbnew.LoadBoard(path)
    out = pcbnew.SHAPE_POLY_SET()
    pcb.GetBoardPolygonOutlines(out, False)
    right = max(range(out.OutlineCount()), key=lambda i: out.Outline(i).BBox().Centre().x)
    poly = pcbnew.SHAPE_POLY_SET()
    poly.AddOutline(out.Outline(right))
    poly.Move(pcbnew.VECTOR2I(MM(-RIGHT_DX + PLATE_DX), 0))
    return poly


def main(src, pcb_path, dst):
    clip = pcb_outline(pcb_path)
    board = pcbnew.LoadBoard(src)
    old, tmpl = None, None
    for f in board.GetFootprints():
        if f.GetReference() == KEY_1_5U:
            old = f
        elif f.GetReference() == TEMPLATE_1U:
            tmpl = f
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline, False)
    plate = pcbnew.SHAPE_POLY_SET()
    plate.AddOutline(outline.Outline(0))
    centres = key_centres()
    for i, (x, y) in enumerate(centres):
        h = pcbnew.FOOTPRINT(tmpl)
        h.ResetUuid()                       # copies must not share the template's IDs
        for item in list(h.Pads()) + list(h.GraphicalItems()) + list(h.GetFields()):
            item.ResetUuid()
        h.SetReference(f"SW{45 + i}")
        h.SetOrientationDegrees(DEG)
        h.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        board.Add(h)
        plate.BooleanAdd(box(x, y, PITCH + 2 * MARGIN, 17 + 2 * MARGIN, DEG))
    board.Remove(old)
    plate.BooleanAdd(bevel(centres[1]))
    peak(plate)
    plate.BooleanIntersection(clip)             # never past the PCB's edge
    for d in [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]:
        board.Remove(d)
    s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_POLY)
    s.SetPolyShape(plate)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(0.05))
    s.SetFilled(False)
    board.Add(s)
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])   # upstream plate, edited PCB, output
    sys.stdout.flush()
    os._exit(0)
