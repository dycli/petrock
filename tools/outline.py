"""Draw both halves' board outline from the key geometry, replacing upstream's.

Left half, upstream frame (the right half is its mirror image):
- top: tools/top_edge.py's flat top and 7.5-degree slopes;
- inner side: straight down at the widened inner edge (tools/widen.py), then
  along the inner thumb keys' side;
- bottom: one straight line falling at BOTTOM_DEG from EDGE_GAP out and below
  the bottom pinky key's outer corner to the thumb keys' side; every keycap
  stays EDGE_GAP above it and the trackpoint's boards DRIVER_EDGE;
- outer side: along the pinky column, EDGE_GAP out.
The trackpoint's room is kept on both halves, so the halves stay mirror images.

Copper zones are reset to cover each half's outline. The new edge segments go
to $NEW_EDGES.

usage: outline.py IN OUT
"""
import math
import os
import sys

import pcbnew

import outer_thumb
import stagger
import thumbs
import top_edge
import widen

MM = pcbnew.FromMM
DRIVER_EDGE = 0.5          # trackpoint driver board to the bottom edge
ZONE_MARGIN = 2.0
BOTTOM_DEG = 7.5           # the bottom edge's fall toward the thumb keys, like the top slopes


def unit(v):
    L = math.hypot(*v)
    return (v[0] / L, v[1] / L)


def meet(p, d, q, e):
    den = d[0] * e[1] - d[1] * e[0]
    t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return (p[0] + t * d[0], p[1] + t * d[1])


def corners(c, deg):
    return [thumbs.corner(c, deg, sx, sy) for sx in (-1, 1) for sy in (-1, 1)]


def left_outline():
    """Left half, upstream frame: the corner points in order round the board."""
    g = thumbs.EDGE_GAP
    (c0, d0), (c1, d1), (c2, d2), (c3, _) = thumbs.keys("left")
    main = stagger.main_keys()
    # Outer side: along the pinky column.
    pinky = [k for k in main if k[0][0] < stagger.PINKY_X]
    (oc_, odeg) = min(pinky, key=lambda k: k[0][0])
    tl = thumbs.corner(oc_, odeg, -1, -1)
    out = thumbs.rot(-1, 0, odeg)
    side_o = ((tl[0] + g * out[0], tl[1] + g * out[1]), thumbs.down(odeg))
    # Top.
    (oc, ko), (ic, ki) = top_edge.slopes()
    x_in = widen.inner_x("left")
    # Thumb side, beside the inner keys.
    across = thumbs.rot(1, 0, d2)
    side_t = ((c2[0] + (thumbs.CAP_W / 2 + g) * across[0], c2[1] + (thumbs.CAP_W / 2 + g) * across[1]), thumbs.down(d2))
    # Bottom: one line at BOTTOM_DEG, falling inward from EDGE_GAP out and below the
    # bottom pinky key's outer bottom corner, to the thumb side.
    (pc, pdeg) = max(pinky, key=lambda k: k[0][1])
    kc = thumbs.corner(pc, pdeg, -1, 1)
    dn = thumbs.down(pdeg)
    bl = (kc[0] + g * (out[0] + dn[0]), kc[1] + g * (out[1] + dn[1]))
    t = math.radians(BOTTOM_DEG)
    bottom = (bl, (math.cos(t), math.sin(t)))
    # Everything above it keeps its distance: keycaps EDGE_GAP, the trackpoint's
    # sensor and driver boards DRIVER_EDGE (on both halves, so they mirror).
    n = (math.sin(t), -math.cos(t))                    # its normal, into the board
    above = lambda p: (p[0] - bl[0]) * n[0] + (p[1] - bl[1]) * n[1]
    caps = [p for c, d in main + thumbs.keys("left") for p in corners(c, d)]
    sx0, sx1 = c0[0] - outer_thumb.SENSOR_HALF_W, c0[0] + outer_thumb.SENSOR_HALF_W
    dx = c0[0] + outer_thumb.DRIVER_OFFSET[0]
    boards = [(x, c0[1] + outer_thumb.STEM_DROP + outer_thumb.SENSOR_BELOW) for x in (sx0, sx1)] + \
             [(x, c0[1] + outer_thumb.DRIVER_OFFSET[1] + outer_thumb.DRIVER_HALF_L) for x in (dx - outer_thumb.DRIVER_HALF_W, dx + outer_thumb.DRIVER_HALF_W)]
    cap_gap, board_gap = min(map(above, caps)), min(map(above, boards))
    if cap_gap < g - 1e-6 or board_gap < DRIVER_EDGE:
        raise SystemExit(f"bottom edge too close: keycaps {cap_gap:.2f}, trackpoint boards {board_gap:.2f}")
    points = [
        meet(*side_o, oc, (1, ko)),            # outer top corner
        oc, ic,                                # the flat top
        meet((x_in, 0), (0, 1), ic, (1, ki)),  # inner top corner
        meet((x_in, 0), (0, 1), *side_t),      # inner side's bend onto the thumb side
        meet(*side_t, *bottom),                # inner bottom corner
        bl,                                    # outer bottom corner
    ]
    return points, dict(caps=cap_gap, boards=board_gap)


def mirror(p):
    return (widen.MIRROR_X - p[0] + widen.RIGHT_DX, p[1])


def V(p):
    return pcbnew.VECTOR2I(MM(p[0]), MM(p[1]))


def draw(board, points, record):
    n = len(points)
    for i in range(n):
        a, b = points[i], points[(i + 1) % n]
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(a))
        s.SetEnd(V(b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(MM(0.05))
        board.Add(s)
        if record:
            record.write(f"{a[0]:.3f} {a[1]:.3f} {b[0]:.3f} {b[1]:.3f}\n")


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    points, info = left_outline()
    print("bottom edge: keycaps %.2f clear, trackpoint boards %.2f" % (info["caps"], info["boards"]), flush=True)
    halves = {"left": points, "right": [mirror(p) for p in reversed(points)]}
    # Each copper zone covers its half's outline.
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        cx = pcbnew.ToMM(z.GetBoundingBox().Centre().x)
        pts = halves["right" if cx > widen.SPLIT_X + widen.RIGHT_DX / 2 else "left"]
        x0, y0 = min(p[0] for p in pts) - ZONE_MARGIN, min(p[1] for p in pts) - ZONE_MARGIN
        x1, y1 = max(p[0] for p in pts) + ZONE_MARGIN, max(p[1] for p in pts) + ZONE_MARGIN
        if z.GetNetname():             # ground pours: no floating fragments (the no-net front fills keep theirs, as stock)
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        o = z.Outline()
        o.RemoveAllContours()
        o.NewOutline()
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            o.Append(MM(x), MM(y))
    # Last: removing items leaves stale handles that crash later board calls.
    old = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    for d in old:
        board.Remove(d)
    record = open(os.environ["NEW_EDGES"], "a") if os.environ.get("NEW_EDGES") else None
    for pts in halves.values():
        draw(board, pts, record)
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
