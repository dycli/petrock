"""Apply the right-thumb trackpoint change to the holykeebs Corne Choc PCB.

- Widens both halves by WIDEN mm along their inner edge.
- Turns both TRRS jacks to face the top edge, in the new strip beside each
  controller.
- Removes the right 1.5u thumb switch (SW42) and its diode, and the right OLED
  header (its pins now carry the trackpoint's PS/2 lines).
- Places a Pro Micro-pattern header (TP1) for the holykeebs trackpoint module
  where SW42 was.
- Moves the inner mounting hole of each half outward with the edge.

All coordinates below are in the upstream file's frame. The right half is
shifted by RIGHT_DX first so the widened halves don't overlap in the file.
"""
import math
import os
import sys

import pcbnew

MM = pcbnew.FromMM

WIDEN = 6.2
SPLIT_X = 149.6          # halves are left/right of this line upstream
RIGHT_DX = 2 * WIDEN     # keeps the upstream gap between the halves

# Old SW42 centre. The nub lands NUB_ALONG mm along the thumb key's long axis
# (toward the bottom edge) and NUB_ACROSS mm across it (negative = away from SW41).
KEY = (166.0625, 123.32)
NUB_ALONG = 0.0
NUB_ACROSS = -1.0
MODULE_ROT = 30.0
# Nub position in the controller footprint's frame, measured from holykeebs'
# assembly photo (about +-1 mm).
NUB_LOCAL = (0.7, 1.4)
# Controller / module outline in the footprint frame (from its F.Fab layer).
MODULE_BOX = (-8.9, -18.3, 8.9, 14.75)
# Pads the holykeebs adapter solders to, and the nets they carry.
MODULE_NETS = {"5": "SDA_r", "6": "SCL_r", "21": "VDD", "23": "GNDA"}
# Unwired corner pins that hold the module's far end down; the rest are dropped.
MODULE_SUPPORT = {"1", "12", "13", "24"}

TOP_EDGE = 56.96
JACK_PORT = 0.25         # jack origin sits this far inside its port edge
# Beside each controller; pads clear the new edge by >=0.5 mm (board rule).
JACKS = {"J1": 149.39, "J3": 149.92}
# Inner mounting holes: follow the widened edge and clear the module.
HOLES = {(144.56, 110.27): (150.56, 106.0), (154.75, 110.27): (148.75, 106.0)}

EDGES = {
    # half: (sign, vertical, top arc, top line inner end, angled, corner arc, bottom inner end, inside)
    "left": (+1, ((146.71, 57.46), (146.79, 117.4)), ((146.21, 56.96), (146.71, 57.46)), (146.21, 56.96),
             ((146.79, 117.4), (134.54, 138.58)), ((134.54, 138.58), (132.61, 138.96)), (132.61, 138.96),
             ((119.05, 131.13), (132.61, 138.96)), (125.0, 110.0)),
    "right": (-1, ((152.6, 57.46), (152.52, 117.4)), ((152.6, 57.46), (153.1, 56.96)), (153.1, 56.96),
              ((152.52, 117.4), (164.77, 138.58)), ((164.77, 138.58), (166.7, 138.96)), (166.7, 138.96),
              ((166.7, 138.96), (180.26, 131.13)), (175.0, 110.0)),
}


def rx(p):
    """Right-half point after the half is shifted."""
    return (round(p[0] + RIGHT_DX, 2), p[1])


def V(p):
    return pcbnew.VECTOR2I(MM(p[0]), MM(p[1]))


def mm(v):
    return (round(pcbnew.ToMM(v.x), 2), round(pcbnew.ToMM(v.y), 2))


def rot(x, y, deg):
    """Rotate a vector the way KiCad rotates footprints (CCW on screen, y down)."""
    a = math.radians(deg)
    return (x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a))


def module_origin():
    u = rot(0, 1, MODULE_ROT)
    v = rot(1, 0, MODULE_ROT)
    nub = (KEY[0] + NUB_ALONG * u[0] + NUB_ACROSS * v[0], KEY[1] + NUB_ALONG * u[1] + NUB_ACROSS * v[1])
    off = rot(*NUB_LOCAL, MODULE_ROT)
    return rx((nub[0] - off[0], nub[1] - off[1]))


_FOOTPRINTS = {}


def footprint(board, ref):
    # Index once: SWIG proxies from GetFootprints() go stale after Remove().
    if not _FOOTPRINTS:
        for f in board.GetFootprints():
            _FOOTPRINTS.setdefault(f.GetReference(), []).append(f)
    found = _FOOTPRINTS.get(ref, [])
    if len(found) != 1:
        raise LookupError(f"{ref}: {len(found)} matches")
    return found[0]


def footprint_at(board, fpid, pos):
    for f in board.GetFootprints():
        if f.GetFPIDAsString() == fpid and mm(f.GetPosition()) == pos:
            return f
    raise LookupError((fpid, pos))


def shift_right_half(board):
    d = V((RIGHT_DX, 0))
    items = list(board.GetFootprints()) + list(board.GetTracks()) + list(board.GetDrawings()) + list(board.Zones())
    for item in items:
        if pcbnew.ToMM(item.GetBoundingBox().Centre().x) > SPLIT_X:
            item.Move(d)


def place_module(board):
    src = footprint(board, "U2")
    fp = pcbnew.FOOTPRINT(src)
    fp.SetOrientationDegrees(0)
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    fp.SetReference("TP1")
    fp.SetValue("holykeebs trackpoint module")
    x0, y0, x1, y1 = MODULE_BOX
    for layer, m, w in ((pcbnew.F_CrtYd, 0.25, 0.05), (pcbnew.F_SilkS, 0.1, 0.12)):
        r = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_RECTANGLE)
        r.SetLayer(layer)
        r.SetStart(V((x0 - m, y0 - m)))
        r.SetEnd(V((x1 + m, y1 + m)))
        r.SetWidth(MM(w))
        fp.Add(r)
    for pad in list(fp.Pads()):
        name = MODULE_NETS.get(pad.GetNumber())
        if name:
            pad.SetNet(board.FindNet(name))
        elif pad.GetNumber() in MODULE_SUPPORT:
            pad.SetNetCode(0)
        else:
            fp.Remove(pad)
    fp.SetOrientationDegrees(MODULE_ROT)
    fp.SetPosition(V(module_origin()))
    board.Add(fp)


def line_intersect(p, d, q, e):
    den = d[0] * e[1] - d[1] * e[0]
    t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return (p[0] + t * d[0], p[1] + t * d[1])


def fillet(p, d, q, e, r, inside):
    """Fillet of radius r between lines (p,d) and (q,e); 'inside' is a point on the board."""
    def normal(a, dd):
        L = math.hypot(*dd)
        n = (-dd[1] / L, dd[0] / L)
        if (inside[0] - a[0]) * n[0] + (inside[1] - a[1]) * n[1] < 0:
            n = (-n[0], -n[1])
        return n
    n1, n2 = normal(p, d), normal(q, e)
    c = line_intersect((p[0] + r * n1[0], p[1] + r * n1[1]), d, (q[0] + r * n2[0], q[1] + r * n2[1]), e)
    t1 = (c[0] - r * n1[0], c[1] - r * n1[1])
    t2 = (c[0] - r * n2[0], c[1] - r * n2[1])
    bis = ((t1[0] + t2[0]) / 2 - c[0], (t1[1] + t2[1]) / 2 - c[1])
    L = math.hypot(*bis)
    return t1, (c[0] + r * bis[0] / L, c[1] + r * bis[1] / L), t2


def arc_radius(a, m, b):
    ax, ay = a; bx, by = m; cx, cy = b
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
    uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d
    return math.hypot(ax - ux, ay - uy)


def widen(board, half):
    sign, vertical, top_arc, top_end, angled, corner, bottom_end, bottom, inside = EDGES[half]
    f = rx if half == "right" else (lambda p: p)
    edges = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]

    def find(shape, a, b):
        a, b = f(a), f(b)
        for d in edges:
            if d.GetShapeStr() == shape and {mm(d.GetStart()), mm(d.GetEnd())} == {a, b}:
                return d
        raise LookupError((shape, a, b))

    def touching(p):
        p = f(p)
        return [d for d in edges if p in (mm(d.GetStart()), mm(d.GetEnd()))]

    def move_end(seg, old, new):
        if mm(seg.GetStart()) == f(old):
            seg.SetStart(V(new))
        elif mm(seg.GetEnd()) == f(old):
            seg.SetEnd(V(new))
        else:
            raise LookupError(old)

    d = V((sign * WIDEN, 0))
    seg_v, seg_ta, seg_a = find("Line", *vertical), find("Arc", *top_arc), find("Line", *angled)
    seg_c = find("Arc", *corner)
    seg_t = [s for s in touching(top_end) if s.GetShapeStr() == "Line"][0]
    seg_b = [s for s in touching(bottom_end) if s.GetShapeStr() == "Line"][0]
    r = arc_radius(f(corner[0]), mm(seg_c.GetArcMid()), f(corner[1]))

    for s in (seg_v, seg_ta, seg_a):
        s.Move(d)
    move_end(seg_t, top_end, (f(top_end)[0] + sign * WIDEN, f(top_end)[1]))

    a0, a1 = (f(p) for p in angled)
    a0, a1 = (a0[0] + sign * WIDEN, a0[1]), (a1[0] + sign * WIDEN, a1[1])
    b0, b1 = (f(p) for p in bottom)
    c = fillet(a0, (a1[0] - a0[0], a1[1] - a0[1]), b0, (b1[0] - b0[0], b1[1] - b0[1]), r, f(inside))
    seg_a.SetStart(V(a0)); seg_a.SetEnd(V(c[0]))
    seg_c.SetArcGeometry(V(c[0]), V(c[1]), V(c[2]))
    move_end(seg_b, bottom_end, c[2])

    # Stretch each copper zone's inner side with the edge.
    for z in board.Zones():
        cx = pcbnew.ToMM(z.GetBoundingBox().Centre().x)
        if (half == "right") != (cx > SPLIT_X + RIGHT_DX / 2):
            continue
        o = z.Outline()
        xs = [pcbnew.ToMM(o.CVertex(i).x) for i in range(o.TotalVertices())]
        edge_x = max(xs) if sign > 0 else min(xs)
        for i in range(o.TotalVertices()):
            p = o.CVertex(i)
            if abs(pcbnew.ToMM(p.x) - edge_x) < 0.5:
                o.SetVertex(i, pcbnew.VECTOR2I(p.x + MM(sign * WIDEN), p.y))


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    for ref in ("SW42", "D42", "J4"):
        footprint(board, ref)  # index before anything moves or goes
    shift_right_half(board)

    for ref in ("SW42", "D42", "J4"):
        board.Remove(footprint(board, ref))

    widen(board, "left")
    widen(board, "right")

    for ref, x in JACKS.items():
        fp = footprint(board, ref)
        fp.SetOrientationDegrees(0)
        # The ground pad sits too close to the board edge and the other pads for
        # thermal spokes, so the pour connects to it solidly.
        for pad in fp.Pads():
            if pad.GetNumber() == "C":
                pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        p = (x, TOP_EDGE + JACK_PORT)
        fp.SetPosition(V(rx(p) if ref == "J3" else p))
    for old, new in HOLES.items():
        right = old[0] > SPLIT_X
        fp = footprint_at(board, "holykeebs:M2_HOLE_NPH", rx(old) if right else old)
        fp.SetPosition(V(rx(new) if right else new))

    place_module(board)
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    # pcbnew's SWIG objects crash Python's final garbage collection.
    sys.stdout.flush()
    os._exit(0)
