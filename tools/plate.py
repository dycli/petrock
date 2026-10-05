"""Switch plates from the finished PCB: one design (the right half's), flipped
for the left half; for the trackpoint half(s) a copy that clears the sensor.

The plate is the PCB's right-half outline, less the strip by the controller
(left open for the controller, OLED and jack): see keep(). It has a choc
switch hole (the stock plate's SW_Hole) at every key, the trackpoint's key
included; the trackpoint copy replaces that hole with an opening round the
sensor board.

Plate frame: the PCB's right half moved by -RIGHT_DX + PLATE_DX, as the stock
plate sits relative to the stock PCB.

usage: plate.py STOCK_PLATE PCB PLAIN_OUT TRACKPOINT_OUT
"""
import os
import sys

import pcbnew

import outline
import stagger
import thumbs
import widen

MM = pcbnew.FromMM
PLATE_DX = -4.0
SENSOR_MARGIN = 0.3      # plate opening round the trackpoint sensor board (it is soldered in place)
# Plate frame: the inner index column's keycap edge on the right half, where the
# opening by the controller starts (tools/inner_strip.py spaces the controller off
# the same line), so the plate clears the controller's socket strips.
INNER_X = widen.MIRROR_X - stagger.INNER_INDEX_X - thumbs.CAP_W / 2 + PLATE_DX
PLATE_THICKNESS = 1.2    # mm: order the switch plates at this thickness
OLED_CLEAR = 1.0         # plate edge to the OLED header's pads
DX = -widen.RIGHT_DX + PLATE_DX


def to_plate(p):
    return (p[0] + DX, p[1])


def polygon(points):
    p = pcbnew.SHAPE_POLY_SET()
    p.NewOutline()
    for x, y in points:
        p.Append(MM(x), MM(y))
    return p


def keep(oled):
    """Where the plate may be: everything but the strip by the controller. Its edge
    runs straight across from the board's inner edge to the inner index column's
    keycap edge (INNER_X), then up it. The level is where a line from the board's inner
    corner above the inner thumb keys, parallel to the upper inner thumb key's top,
    comes OLED_CLEAR from the OLED header's pads (oled, plate frame) or level with
    that key's outer top corner, whichever is first: under the OLED header, and
    clear of the key."""
    bend = outline.left_outline()[0][4]                       # left half, upstream frame
    b = (widen.MIRROR_X - bend[0] + PLATE_DX, bend[1])        # the right half's, plate frame
    _, _, _, (c, deg) = thumbs.keys("right")
    c = (c[0] + PLATE_DX, c[1])
    top = [thumbs.corner(c, deg, sx, -1) for sx in (-1, 1)]
    far = max(top, key=lambda q: (q[0] - b[0]) ** 2 + (q[1] - b[1]) ** 2)   # outer top corner
    d = thumbs.rot(1, 0, deg)
    if d[0] * (far[0] - b[0]) + d[1] * (far[1] - b[1]) < 0:
        d = (-d[0], -d[1])
    t_end = d[0] * (far[0] - b[0]) + d[1] * (far[1] - b[1])   # level with the outer top corner
    t = 0.0
    while t < t_end:
        q = (b[0] + t * d[0], b[1] + t * d[1])
        if any(x0 - OLED_CLEAR <= q[0] <= x1 + OLED_CLEAR and y0 - OLED_CLEAR <= q[1] <= y1 + OLED_CLEAR
               for x0, y0, x1, y1 in oled):
            break
        t += 0.05
    p = (b[0] + t * d[0], b[1] + t * d[1])
    return polygon([(INNER_X, 0), (500, 0), (500, 400), (b[0] - 100, 400), (b[0] - 100, p[1]), (INNER_X, p[1])])


def pcb_parts(path):
    """The PCB's right-half outline, its keys (plate frame) and the sensor board's
    opening, if this PCB has a right trackpoint."""
    pcb = pcbnew.LoadBoard(path)
    out = pcbnew.SHAPE_POLY_SET()
    pcb.GetBoardPolygonOutlines(out, False)
    right = max(range(out.OutlineCount()), key=lambda i: out.Outline(i).BBox().Centre().x)
    half = pcbnew.SHAPE_POLY_SET()
    half.AddOutline(out.Outline(right))
    half.Move(pcbnew.VECTOR2I(MM(DX), 0))
    split = pcbnew.ToMM(half.BBox().GetLeft()) - DX
    keys = [(to_plate((pcbnew.ToMM(f.GetPosition().x), pcbnew.ToMM(f.GetPosition().y))), f.GetOrientationDegrees())
            for f in pcb.GetFootprints()
            if "SW_choc" in f.GetFPIDAsString() and pcbnew.ToMM(f.GetPosition().x) > split]
    (c0, d0) = thumbs.keys("right")[0]
    tp_key = (to_plate((c0[0] + widen.RIGHT_DX, c0[1])), d0)
    sensor, oled = None, []
    for f in pcb.GetFootprints():
        if f.GetReference() == "J4":                          # the right half's OLED header
            for pad in f.Pads():
                bb = pad.GetBoundingBox()
                oled.append(tuple(pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())))
        if f.GetReference() == "TP1":
            (body,) = [g.GetBoundingBox() for g in f.GraphicalItems()
                       if g.GetLayer() == pcbnew.F_Fab and g.GetClass() == "PCB_SHAPE" and g.GetShapeStr() == "Rect"]
            x0, y0, x1, y1 = (pcbnew.ToMM(v) for v in (body.GetLeft(), body.GetTop(), body.GetRight(), body.GetBottom()))
            sensor = polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
            sensor.Inflate(MM(SENSOR_MARGIN), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
            sensor.Move(pcbnew.VECTOR2I(MM(DX), 0))
    oled = [(x0 + DX, y0, x1 + DX, y1) for x0, y0, x1, y1 in oled]
    return half, keys, tp_key, sensor, oled


def edge(board, shape):
    s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_POLY)
    s.SetPolyShape(shape)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(0.05))
    s.SetFilled(False)
    board.Add(s)


def main(stock, pcb_path, dst, dst_tp):
    board_outline, keys, tp_key, sensor, oled = pcb_parts(pcb_path)
    plate = pcbnew.SHAPE_POLY_SET(board_outline)
    plate.BooleanIntersection(keep(oled))
    board = pcbnew.LoadBoard(stock)
    # Choc v1 switches and stabilisers clip into a 1.2 mm plate; 1.6 mm FR4 is too thick.
    board.GetDesignSettings().SetBoardThickness(MM(PLATE_THICKNESS))
    old = list(board.GetFootprints()) + [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    template = pcbnew.FOOTPRINT(old[0])
    for item in old:                  # removing invalidates other handles, so all at once
        board.Remove(item)

    def hole(n, at, deg):
        h = pcbnew.FOOTPRINT(template)
        h.ResetUuid()                 # copies must not share the template's IDs
        for item in list(h.Pads()) + list(h.GraphicalItems()) + list(h.GetFields()):
            item.ResetUuid()
        h.SetReference(f"SW{n}")
        h.SetOrientationDegrees(deg)
        h.SetPosition(pcbnew.VECTOR2I(MM(at[0]), MM(at[1])))
        board.Add(h)
        return h

    for n, (at, deg) in enumerate(sorted(keys), 1):
        hole(n, at, deg)
    edge(board, plate)
    tp_hole = hole(len(keys) + 1, *tp_key)
    board.Save(dst)
    if dst_tp:
        # The trackpoint copy: the sensor stands taller than the gap under the
        # plate, so it gets its own opening (a hole in the outline polygon gets
        # stored with a slit) in place of the key's switch hole.
        board.Remove(tp_hole)
        edge(board, sensor)
        board.Save(dst_tp)


if __name__ == "__main__":
    main(*sys.argv[1:4], sys.argv[4] if len(sys.argv) > 4 else None)
    sys.stdout.flush()
    os._exit(0)
