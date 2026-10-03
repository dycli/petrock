"""Widen both halves along their inner edge and move the TRRS jacks to the top.

The straight part of the inner edge moves out; the edge below it, round the
thumb keys, is redrawn EDGE_GAP from their keycaps (tools/thumbs.py).

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

import thumbs

MM = pcbnew.FromMM

WIDEN = 6.2
SPLIT_X = 149.6          # halves are left/right of this line upstream
RIGHT_DX = 2 * WIDEN     # keeps the upstream gap between the halves

TOP_EDGE = 56.96
JACK_PORT = 0.25         # jack origin sits this far inside its port edge
# Beside each controller; pads clear the new edge by >=0.5 mm (board rule).
JACKS = {"J1": 149.39, "J3": 149.92}
# Inner mounting holes: follow the widened edge and clear the new thumb key.
# Left half, upstream frame: the thumb-area edge being redrawn lies in CHAIN_X
# below CHAIN_Y; it starts at the inner edge's bend and ends on the main block's
# bottom edge (BODY: the end it meets, then a point further along it). The right
# half mirrors it about MIRROR_X.
BODY = ((71.29, 113.77), (36.41, 113.74))
CHAIN_X, CHAIN_Y = (71.2, 146.8), 113.76
MIRROR_X = 299.31
# Corner radii along the chain. The tip below the lower inner key is rounded
# about the keycap's own rounded corner, so the gap holds round it; the rest
# keep upstream's radii.
CHAIN_RADII = [thumbs.CAP_R + thumbs.EDGE_GAP, 3.41, 0.52, 0.5]
# The trackpoint sensor board's half width, and how far it reaches below the
# outer key's centre (tools/make_footprints.py, placed by tools/outer_thumb.py).
SENSOR_HALF_W, SENSOR_BELOW = 6.6, 10.84
HOLES = {(144.56, 110.27): (150.56, 106.0), (154.75, 110.27): (148.75, 106.0)}

EDGES = {
    # half: (sign, straight inner edge, top arc, top line's inner end)
    "left": (+1, ((146.71, 57.46), (146.79, 117.4)), ((146.21, 56.96), (146.71, 57.46)), (146.21, 56.96)),
    "right": (-1, ((152.6, 57.46), (152.52, 117.4)), ((152.6, 57.46), (153.1, 56.96)), (153.1, 56.96)),
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


def add_shape(board, kind, a, b, mid=None):
    s = pcbnew.PCB_SHAPE(board, kind)
    if mid is None:
        s.SetStart(V(a))
        s.SetEnd(V(b))
    else:
        s.SetArcGeometry(V(a), V(mid), V(b))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(0.05))
    board.Add(s)
    return s


def corner(prev, c, nxt, r):
    """Round the corner at c (between the lines from prev and to nxt) with radius r:
    (start tangent point, arc midpoint, end tangent point)."""
    u1 = unit((prev[0] - c[0], prev[1] - c[1]))
    u2 = unit((nxt[0] - c[0], nxt[1] - c[1]))
    half_angle = math.acos(max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1]))) / 2
    t = r / math.tan(half_angle)
    bis = unit((u1[0] + u2[0], u1[1] + u2[1]))
    h = r / math.sin(half_angle) - r
    return ((c[0] + t * u1[0], c[1] + t * u1[1]), (c[0] + h * bis[0], c[1] + h * bis[1]),
            (c[0] + t * u2[0], c[1] + t * u2[1]))


def unit(v):
    L = math.hypot(*v)
    return (v[0] / L, v[1] / L)


def rotated_corner(c, deg, sx, sy, inset):
    """A keycap corner (sx, sy = -1/+1 in the key's frame), moved inset toward the centre on both axes."""
    dx, dy = thumbs.rot(sx * (thumbs.CAP_W / 2 - inset), sy * (thumbs.CAP_H / 2 - inset), deg)
    return (c[0] + dx, c[1] + dy)


def thumb_chain():
    """Left half, upstream frame: the edge from the bend in the inner edge round the
    thumb keys to the bottom of the main block, as corner points (bend first, a
    point on the main block's bottom edge last) and the radius for each corner
    in between.

    Beside and under the inner keys the edge runs thumbs.EDGE_GAP from their
    keycaps. Under the middle and outer keys it is one level line, EDGE_GAP
    below the middle keycap's lowest point, which leaves the trackpoint room
    on the right half. Its outer corner sits as far out from the trackpoint
    sensor's bottom outer corner as it is below it, and the slant from there
    up to the main block leans like the inner edge (mirrored)."""
    (c0, d0), (c1, d1), (c2, d2), _ = thumbs.keys("left")
    gh = thumbs.CAP_H / 2 + thumbs.EDGE_GAP
    gw = thumbs.CAP_W / 2 + thumbs.EDGE_GAP

    def along(c, v, k):
        return (c[0] + k * v[0], c[1] + k * v[1])

    across = lambda deg: thumbs.rot(1, 0, deg)
    v0, v1 = EDGES["left"][1]
    vertical = ((v0[0] + WIDEN, v0[1]), (v1[0] - v0[0], v1[1] - v0[1]))
    side = (along(c2, across(d2), gw), thumbs.down(d2))           # beside the inner keys
    end = (along(c2, thumbs.down(d2), gh), across(d2))            # under the lower inner key
    lowest = max(rotated_corner(c1, d1, sx, sy, thumbs.CAP_R)[1] for sx in (-1, 1) for sy in (-1, 1)) + thumbs.CAP_R
    level_y = lowest + thumbs.EDGE_GAP
    sensor_x = c0[0] - SENSOR_HALF_W                              # the sensor's outer side (mirrored)
    sensor_y = c0[1] + SENSOR_BELOW                               # and its bottom end
    corner_pt = (sensor_x - (level_y - sensor_y), level_y)
    level = (corner_pt, (1.0, 0.0))                               # under the middle and outer keys
    sx, sy = thumbs.down(d2)                                      # the inner edge's direction, mirrored
    diagonal = (corner_pt, (sx, -sy))
    body = (BODY[0], (BODY[1][0] - BODY[0][0], BODY[1][1] - BODY[0][1]))
    lines = [vertical, side, end, level, diagonal, body]
    points = [line_intersect(*a, *b) for a, b in zip(lines, lines[1:])]
    return points + [BODY[1]], CHAIN_RADII


def widen(board, half):
    sign, vertical, top_arc, top_end = EDGES[half]
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
    seg_v, seg_ta = find("Line", *vertical), find("Arc", *top_arc)
    seg_t = [s for s in touching(top_end) if s.GetShapeStr() == "Line"][0]

    # The straight inner edge moves out.
    for s in (seg_v, seg_ta):
        s.Move(d)
    move_end(seg_t, top_end, (f(top_end)[0] + sign * WIDEN, f(top_end)[1]))
    # Everything below the bend is redrawn from the thumb keys: worked out on the
    # left half (upstream frame) and mirrored for the right.
    g = (lambda p: p) if half == "left" else (lambda p: rx((MIRROR_X - p[0], p[1])))
    chain_box = (CHAIN_X[0], CHAIN_X[1]) if half == "left" else (MIRROR_X - CHAIN_X[1], MIRROR_X - CHAIN_X[0])
    lo, hi = f((chain_box[0], 0))[0], f((chain_box[1], 0))[0]
    old_chain = [d for d in edges if d is not seg_v and
                 all(lo - 0.01 <= q[0] <= hi + 0.01 and q[1] >= CHAIN_Y for q in (mm(d.GetStart()), mm(d.GetEnd())))]
    seg_body = [d for d in edges if d.GetShapeStr() == "Line" and g(BODY[0]) in (mm(d.GetStart()), mm(d.GetEnd()))][0]
    points, radii = thumb_chain()
    points = [g(p) for p in points]
    corners = [corner(points[i - 1], points[i], points[i + 1], radii[i - 1]) for i in range(1, len(points) - 1)]
    if abs(pcbnew.ToMM(seg_v.GetStart().y) - points[0][1]) < abs(pcbnew.ToMM(seg_v.GetEnd().y) - points[0][1]):
        seg_v.SetStart(V(points[0]))
    else:
        seg_v.SetEnd(V(points[0]))
    if mm(seg_body.GetStart()) == g(BODY[0]):
        seg_body.SetStart(V(corners[-1][2]))
    else:
        seg_body.SetEnd(V(corners[-1][2]))
    for d in old_chain:                       # last: removing invalidates other handles
        board.Remove(d)
    new = [seg_v]
    at = points[0]
    for t1, mid, t2 in corners:
        new.append(add_shape(board, pcbnew.SHAPE_T_SEGMENT, at, t1))
        add_shape(board, pcbnew.SHAPE_T_ARC, t1, t2, mid)
        at = t2

    if os.environ.get("NEW_EDGES"):           # edges this step created, for cleanup.py
        with open(os.environ["NEW_EDGES"], "a") as rec:
            for seg in new:                   # the top line is replaced by top_edge.py
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
