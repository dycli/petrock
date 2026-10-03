"""Switch plates for the split inner thumb keys: one design, flipped for the left
half, and a copy for the right half that also clears the trackpoint sensor.

Replaces the inner 1.5u opening with two 1u openings at the new key centres and
grows the outline to cover them and to follow the PCB's edge round the thumbs.
The plate frame is the upstream PCB's right-half frame shifted by PLATE_DX.
"""
import math
import os
import sys

import pcbnew

import thumbs

MM = pcbnew.FromMM
PLATE_DX = -4.0
KEY_1_5U = "SW21"        # in the plate file
TEMPLATE_1U = "SW20"
LOWER, UPPER, DEG = thumbs.inner_keys("right")     # upstream frame
PITCH = 18.0
SENSOR_MARGIN = 0.3      # plate opening round the trackpoint sensor board (it is soldered in place)
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
    return [(x + PLATE_DX, y) for x, y in (LOWER, UPPER)]


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
    ux, uy = thumbs.down(DEG)             # down the stack of inner keys
    vx, vy = -uy, ux                      # across the key, toward the old outline
    if vx < 0:
        vx, vy = -vx, -vy
    hl, hw = thumbs.ROW_PITCH / 2 + MARGIN, PITCH / 2 + MARGIN
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


def follow_bottom(plate, clip):
    """Grow the plate to the PCB's redrawn edge round the thumb keys and the
    trackpoint (tools/widen.py), so the two stay flush there."""
    # PCB-frame x range: the inner edge to just past the diagonal's top end;
    # y range: below the inner mounting hole, down past the lowest point.
    x0, x1 = 150.0 - RIGHT_DX + PLATE_DX, 245.0 - RIGHT_DX + PLATE_DX
    band = polygon([(x0, 112.0), (x1, 112.0), (x1, 141.0), (x0, 141.0)])
    band.BooleanIntersection(clip)
    plate.BooleanAdd(band)


def follow_outer(plate, clip):
    """Grow the plate to the PCB's outer side edge, moved out by tools/widen.py."""
    x0, x1 = 290.0 - RIGHT_DX + PLATE_DX, 300.0 - RIGHT_DX + PLATE_DX      # PCB frame: outer column's edge
    band = polygon([(x0, 55.0), (x1, 55.0), (x1, 120.0), (x0, 120.0)])
    band.BooleanIntersection(clip)
    plate.BooleanAdd(band)


def pcb_shapes(path):
    """The edited PCB's right-half outline and the trackpoint sensor board
    grown by SENSOR_MARGIN, both moved into the plate frame."""
    pcb = pcbnew.LoadBoard(path)
    out = pcbnew.SHAPE_POLY_SET()
    pcb.GetBoardPolygonOutlines(out, False)
    right = max(range(out.OutlineCount()), key=lambda i: out.Outline(i).BBox().Centre().x)
    poly = pcbnew.SHAPE_POLY_SET()
    poly.AddOutline(out.Outline(right))
    (tp,) = [f for f in pcb.GetFootprints() if f.GetReference() == "TP1"]
    (body,) = [g.GetBoundingBox() for g in tp.GraphicalItems()        # the sensor board
               if g.GetLayer() == pcbnew.F_Fab and g.GetClass() == "PCB_SHAPE" and g.GetShapeStr() == "Rect"]
    x0, y0, x1, y1 = body.GetLeft(), body.GetTop(), body.GetRight(), body.GetBottom()
    sensor = pcbnew.SHAPE_POLY_SET()
    sensor.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        sensor.Append(x, y)
    sensor.Inflate(MM(SENSOR_MARGIN), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
    for p in (poly, sensor):
        p.Move(pcbnew.VECTOR2I(MM(-RIGHT_DX + PLATE_DX), 0))
    return poly, sensor


def main(src, pcb_path, dst, dst_right):
    clip, sensor = pcb_shapes(pcb_path)
    board = pcbnew.LoadBoard(src)
    old, tmpl, slot = None, None, None
    tx, ty, _ = thumbs.HALVES["right"]["outer"]          # the trackpoint's key slot
    for f in board.GetFootprints():
        x, y = pcbnew.ToMM(f.GetPosition().x), pcbnew.ToMM(f.GetPosition().y)
        if f.GetReference() == KEY_1_5U:
            old = f
        elif f.GetReference() == TEMPLATE_1U:
            tmpl = f
        elif abs(x - tx - PLATE_DX) < 0.05 and abs(y - ty) < 0.05:
            slot = f
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
    follow_bottom(plate, clip)
    follow_outer(plate, clip)
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
    # The right half's plate also clears the trackpoint sensor, which stands
    # taller than the gap under the plate: a cut-out of its own, like the
    # switch holes (a hole in the outline polygon gets stored with a slit).
    o = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_POLY)
    o.SetPolyShape(sensor)
    o.SetLayer(pcbnew.Edge_Cuts)
    o.SetWidth(MM(0.05))
    o.SetFilled(False)
    board.Add(o)
    board.Remove(slot)                          # its switch hole lies inside the sensor opening
    board.Save(dst_right)


if __name__ == "__main__":
    main(*sys.argv[1:5])   # upstream plate, edited PCB, left plate (flipped), right plate
    sys.stdout.flush()
    os._exit(0)
