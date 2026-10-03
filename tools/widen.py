"""Widen both halves along their inner edge and move the TRRS jacks to the top.

Only the straight part of the inner edge moves out; the stock angled edge below
it, which the inner thumb keys run along, stays put and extends up to meet it.

Shifts the right half by RIGHT_DX first so the widened halves don't overlap in
the file; every later step works in the shifted frame. Both inner edges move
out by WIDEN, the jacks turn to face the top edge in the new strip beside each
controller, and the inner mounting hole of each half moves outward.

Coordinates below are in the upstream frame; rx() maps right-half points.
"""
import math
import os
import sys

import pcbnew

MM = pcbnew.FromMM

WIDEN = 6.2
SPLIT_X = 149.6          # halves are left/right of this line upstream
RIGHT_DX = 2 * WIDEN     # keeps the upstream gap between the halves

TOP_EDGE = 56.96
JACK_PORT = 0.25         # jack origin sits this far inside its port edge
# Beside each controller; pads clear the new edge by >=0.5 mm (board rule).
JACKS = {"J1": 149.39, "J3": 149.92}
# Inner mounting holes: follow the widened edge and clear the new thumb key.
# The angled inner edge moves out so the inner thumb keycaps sit as far from
# it as the outer column's keycaps sit from the outer edge (0.95 mm).
THUMB_EDGE_OUT = 0.44
BOTTOM_EDGE_OUT = 0.34   # same, for the short bottom edge under the lower inner thumb key
HOLES = {(144.56, 110.27): (150.56, 106.0), (154.75, 110.27): (148.75, 106.0)}

EDGES = {
    # half: (sign, straight inner edge, top arc, top line's inner end, angled edge (bend end first),
    #        bottom corner arc, bottom edge (corner end first), a point on the board)
    "left": (+1, ((146.71, 57.46), (146.79, 117.4)), ((146.21, 56.96), (146.71, 57.46)), (146.21, 56.96),
             ((146.79, 117.4), (134.54, 138.58)), ((134.54, 138.58), (132.61, 138.96)),
             ((132.61, 138.96), (119.05, 131.13)), (125.0, 110.0)),
    "right": (-1, ((152.6, 57.46), (152.52, 117.4)), ((152.6, 57.46), (153.1, 56.96)), (153.1, 56.96),
              ((152.52, 117.4), (164.77, 138.58)), ((164.77, 138.58), (166.7, 138.96)),
              ((166.7, 138.96), (180.26, 131.13)), (175.0, 110.0)),
}


def rx(p):
    """Right-half point after the half is shifted."""
    return (round(p[0] + RIGHT_DX, 2), p[1])


def V(p):
    return pcbnew.VECTOR2I(MM(p[0]), MM(p[1]))


def mm(v):
    return (round(pcbnew.ToMM(v.x), 2), round(pcbnew.ToMM(v.y), 2))


def shift_right_half(board):
    d = V((RIGHT_DX, 0))
    items = list(board.GetFootprints()) + list(board.GetTracks()) + list(board.GetDrawings()) + list(board.Zones())
    for item in items:
        if pcbnew.ToMM(item.GetBoundingBox().Centre().x) > SPLIT_X:
            item.Move(d)


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
    sign, vertical, top_arc, top_end, angled, corner, bottom, inside = EDGES[half]
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
    seg_t = [s for s in touching(top_end) if s.GetShapeStr() == "Line"][0]

    # The straight inner edge moves out; the stock angled edge stays where it is
    # (the inner thumb keys run along it) and extends up to meet it.
    for s in (seg_v, seg_ta):
        s.Move(d)
    move_end(seg_t, top_end, (f(top_end)[0] + sign * WIDEN, f(top_end)[1]))
    # The angled edge moves THUMB_EDGE_OUT outward (away from the board) and still
    # meets the straight edge above and, through a stock-radius corner, the bottom edge.
    a0, a1 = (f(p) for p in angled)
    dx, dy = a1[0] - a0[0], a1[1] - a0[1]
    L = math.hypot(dx, dy)
    nx, ny = dy / L, -dx / L
    ins = f(inside)
    if (ins[0] - a0[0]) * nx + (ins[1] - a0[1]) * ny > 0:
        nx, ny = -nx, -ny
    a0o = (a0[0] + THUMB_EDGE_OUT * nx, a0[1] + THUMB_EDGE_OUT * ny)
    v0, v1 = (f(p) for p in vertical)
    v0, v1 = (v0[0] + sign * WIDEN, v0[1]), (v1[0] + sign * WIDEN, v1[1])
    bend = line_intersect(v0, (v1[0] - v0[0], v1[1] - v0[1]), a0o, (dx, dy))
    # Whichever end of the straight edge was at the old bend goes to the new one.
    if abs(pcbnew.ToMM(seg_v.GetStart().y) - a0[1]) < 0.05:
        seg_v.SetStart(V(bend))
    else:
        seg_v.SetEnd(V(bend))
    # The short bottom edge under the lower inner thumb key moves out too; its far
    # end re-meets the next bottom edge through the small arc that joined them.
    b0, b1 = (f(p) for p in bottom)
    bdx, bdy = b1[0] - b0[0], b1[1] - b0[1]
    bL = math.hypot(bdx, bdy)
    bnx, bny = bdy / bL, -bdx / bL
    if (ins[0] - b0[0]) * bnx + (ins[1] - b0[1]) * bny > 0:
        bnx, bny = -bnx, -bny
    b0o = (b0[0] + BOTTOM_EDGE_OUT * bnx, b0[1] + BOTTOM_EDGE_OUT * bny)
    seg_b = find("Line", *bottom)
    seg_s = [d for d in touching(bottom[1]) if d.GetShapeStr() == "Arc"][0]
    s_far = [p for p in (mm(seg_s.GetStart()), mm(seg_s.GetEnd())) if p != f(bottom[1])][0]
    seg_n = [d for d in edges if d.GetShapeStr() == "Line" and s_far in (mm(d.GetStart()), mm(d.GetEnd())) and d is not seg_b][0]
    n_far = [p for p in (mm(seg_n.GetStart()), mm(seg_n.GetEnd())) if p != s_far][0]
    rs = arc_radius(f(bottom[1]), mm(seg_s.GetArcMid()), s_far)
    # This corner bends into the board, so its arc's centre lies outside it.
    outside = (ins[0], ins[1] + 200.0)
    s2 = fillet(b0o, (bdx, bdy), n_far, (s_far[0] - n_far[0], s_far[1] - n_far[1]), rs, outside)
    seg_s.SetArcGeometry(V(s2[0]), V(s2[1]), V(s2[2]))
    if mm(seg_n.GetStart()) == s_far:
        seg_n.SetStart(V(s2[2]))
    else:
        seg_n.SetEnd(V(s2[2]))

    seg_c = find("Arc", *corner)
    r = arc_radius(f(corner[0]), mm(seg_c.GetArcMid()), f(corner[1]))
    c = fillet(a0o, (dx, dy), b0o, (bdx, bdy), r, ins)
    seg_a.SetStart(V(bend))
    seg_a.SetEnd(V(c[0]))
    seg_c.SetArcGeometry(V(c[0]), V(c[1]), V(c[2]))
    seg_b.SetStart(V(c[2]))
    seg_b.SetEnd(V(s2[0]))

    if os.environ.get("NEW_EDGES"):           # edges this step created, for cleanup.py
        with open(os.environ["NEW_EDGES"], "a") as rec:
            for seg in (seg_v, seg_a, seg_b):          # the top line is replaced by top_edge.py
                (ax, ay), (bx, by) = mm(seg.GetStart()), mm(seg.GetEnd())
                rec.write(f"{ax} {ay} {bx} {by}\n")

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
    index = {}
    for f in board.GetFootprints():
        index.setdefault(f.GetReference(), []).append(f)
    holes = [(f, mm(f.GetPosition())) for f in board.GetFootprints() if f.GetFPIDAsString() == "holykeebs:M2_HOLE_NPH"]
    shift_right_half(board)
    widen(board, "left")
    widen(board, "right")
    for ref, x in JACKS.items():
        (fp,) = index[ref]
        fp.SetOrientationDegrees(0)
        # The ground pad sits too close to the edge and the other pads for
        # thermal spokes, so the pour connects to it solidly.
        for pad in fp.Pads():
            if pad.GetNumber() == "C":
                pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        p = (x, TOP_EDGE + JACK_PORT)
        fp.SetPosition(V(rx(p) if ref == "J3" else p))
    for old, new in HOLES.items():
        (fp,) = [f for f, at in holes if at == old]
        fp.SetPosition(V(rx(new) if old[0] > SPLIT_X else new))
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    # pcbnew's SWIG objects crash Python's final garbage collection.
    sys.stdout.flush()
    os._exit(0)
