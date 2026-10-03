"""Two-layer grid router for single connections on an existing board.

Rasterises every copper item of other nets (inflated by clearance plus half the
track width), the board edge, holes and no-track/no-via rule areas, then runs A*
over a 0.1 mm grid with 45-degree moves and vias. The path is simplified to
straight segments and added to the board.

usage: maze.py IN OUT NET WIDTH START GOAL
  START/GOAL: REF:PAD (a pad, e.g. TP2:5), X,Y,LAYERS (e.g. 217.51,103.8,FB),
  or GOAL "any".
  layers: F, B or FB (start/goal reachable on those layers). "any" routes to
  the nearest same-net copper not already touching the start.
"""
import heapq
import math
import os
import sys

import numpy as np
import pcbnew

MM = pcbnew.FromMM
CELL = 0.1
CLEAR = 0.26         # board rule is 0.2; the extra covers grid rounding and snapped ends
PAD_CLEAR = 0.36     # pads carry upstream's 0.3 mm pad clearance
EDGE_CLEAR = 0.5
CUTOUT_CLEAR = 0.5
PAD_ESCAPE = 1.2      # mm around start/goal where LED-window clearance is relaxed to 0.25
HOLE_TO_HOLE = 0.25
HOLE_CLEAR = 0.3      # copper to hole edge
VIA_D, VIA_DRILL = 0.6, 0.4
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)
VIA_COST = 40


class Grid:
    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0 = x0, y0
        self.w = int(math.ceil((x1 - x0) / CELL)) + 1
        self.h = int(math.ceil((y1 - y0) / CELL)) + 1
        self.xs = x0 + np.arange(self.w) * CELL
        self.ys = y0 + np.arange(self.h) * CELL

    def cell(self, x, y):
        return int(round((y - self.y0) / CELL)), int(round((x - self.x0) / CELL))

    def xy(self, r, c):
        return self.x0 + c * CELL, self.y0 + r * CELL

    def fill_poly(self, mask, poly):
        """Rasterise every outline (with holes) of a SHAPE_POLY_SET into mask."""
        for i in range(poly.OutlineCount()):
            rings = [poly.Outline(i)] + [poly.Hole(i, j) for j in range(poly.HoleCount(i))]
            pts = [np.array([[pcbnew.ToMM(r.CPoint(k).x), pcbnew.ToMM(r.CPoint(k).y)] for k in range(r.PointCount())]) for r in rings]
            allp = np.vstack(pts)
            c0 = max(0, int((allp[:, 0].min() - self.x0) / CELL) - 1)
            c1 = min(self.w, int((allp[:, 0].max() - self.x0) / CELL) + 2)
            r0 = max(0, int((allp[:, 1].min() - self.y0) / CELL) - 1)
            r1 = min(self.h, int((allp[:, 1].max() - self.y0) / CELL) + 2)
            if c0 >= c1 or r0 >= r1:
                continue
            X, Y = np.meshgrid(self.xs[c0:c1], self.ys[r0:r1])
            inside = np.zeros(X.shape, bool)
            for ring in pts:      # even-odd rule over outline and holes
                xa, ya = ring[:, 0], ring[:, 1]
                xb, yb = np.roll(xa, -1), np.roll(ya, -1)
                for k in range(len(xa)):
                    cond = (ya[k] > Y) != (yb[k] > Y)
                    with np.errstate(divide="ignore", invalid="ignore"):
                        xint = xa[k] + (Y - ya[k]) * (xb[k] - xa[k]) / (yb[k] - ya[k])
                    inside ^= cond & (X < xint)
            mask[r0:r1, c0:c1] |= inside


def item_poly(item, layer, grow):
    p = pcbnew.SHAPE_POLY_SET()
    item.TransformShapeToPolygon(p, layer, MM(grow), MM(0.01), pcbnew.ERROR_OUTSIDE)
    return p


def circle(centre, radius, n=32):
    p = pcbnew.SHAPE_POLY_SET()
    p.NewOutline()
    cx, cy = pcbnew.ToMM(centre.x), pcbnew.ToMM(centre.y)
    for k in range(n):
        a = 2 * math.pi * k / n
        p.Append(MM(cx + radius / math.cos(math.pi / n) * math.cos(a)), MM(cy + radius / math.cos(math.pi / n) * math.sin(a)))
    return p


def build_masks(board, grid, net, half_w):
    """Blocked cells for a track centre on each layer, and for a via centre."""
    blocked = {l: np.zeros((grid.h, grid.w), bool) for l in LAYERS}
    others = {l: np.zeros((grid.h, grid.w), bool) for l in LAYERS}
    via_blocked = np.zeros((grid.h, grid.w), bool)
    target = {l: np.zeros((grid.h, grid.w), bool) for l in LAYERS}
    items = [p for f in board.GetFootprints() for p in f.Pads()] + list(board.GetTracks())
    gx0, gy0 = grid.x0 - 3, grid.y0 - 3
    gx1, gy1 = grid.x0 + grid.w * CELL + 3, grid.y0 + grid.h * CELL + 3
    for it in items:
        bb = it.GetBoundingBox()
        if (pcbnew.ToMM(bb.GetRight()) < gx0 or pcbnew.ToMM(bb.GetX()) > gx1 or
                pcbnew.ToMM(bb.GetBottom()) < gy0 or pcbnew.ToMM(bb.GetY()) > gy1):
            continue
        same = it.GetNetname() == net and net != ""
        for l in LAYERS:
            if not it.IsOnLayer(l):
                continue
            if same:
                grid.fill_poly(target[l], item_poly(it, l, 0))
            else:
                grid.fill_poly(others[l], item_poly(it, l, (PAD_CLEAR if it.GetClass() == "PAD" else CLEAR) + half_w))
                blocked[l] |= others[l]
                grid.fill_poly(via_blocked, item_poly(it, l, CLEAR + VIA_D / 2))
        if it.GetClass() == "PCB_VIA":         # drilled holes keep apart whatever their net
            grid.fill_poly(via_blocked, circle(it.GetPosition(), pcbnew.ToMM(it.GetDrill()) / 2 + HOLE_TO_HOLE + VIA_DRILL / 2 + 0.05))
        if it.GetClass() == "PAD" and it.GetDrillSizeX() > 0:   # holes block both layers
            r = pcbnew.ToMM(it.GetDrillSizeX()) / 2
            if not same:
                hole = circle(it.GetPosition(), r + HOLE_CLEAR + half_w)
                for l in LAYERS:
                    grid.fill_poly(blocked[l], hole)
            grid.fill_poly(via_blocked, circle(it.GetPosition(), r + max(HOLE_CLEAR + VIA_D / 2, HOLE_TO_HOLE + VIA_DRILL / 2 + 0.05)))
    # Board edge: keep everything EDGE_CLEAR inside the outline (and out of internal cutouts).
    # Outer edge at EDGE_CLEAR; internal cutouts (the reverse-mount LED windows,
    # whose own pads sit close by design) at CUTOUT_CLEAR.
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline, False)
    grow = max(half_w, VIA_D / 2)
    ok = np.zeros((grid.h, grid.w), bool)
    holes = pcbnew.SHAPE_POLY_SET()
    for i in range(outline.OutlineCount()):
        outer = pcbnew.SHAPE_POLY_SET()
        outer.AddOutline(outline.Outline(i))
        outer.Deflate(MM(EDGE_CLEAR + grow), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
        grid.fill_poly(ok, outer)
        for j in range(outline.HoleCount(i)):
            holes.AddOutline(outline.Hole(i, j))
    tight = pcbnew.SHAPE_POLY_SET(holes)
    holes.Inflate(MM(CUTOUT_CLEAR + grow), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
    tight.Inflate(MM(0.25 + grow), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
    cut = np.zeros((grid.h, grid.w), bool)
    grid.fill_poly(cut, holes)
    cut_tight = np.zeros((grid.h, grid.w), bool)
    grid.fill_poly(cut_tight, tight)
    ok &= ~cut
    grid.relaxable = cut & ~cut_tight      # blocked only by the wide LED-window margin
    for l in LAYERS:
        blocked[l] |= ~ok
    via_blocked |= ~ok
    for z in board.Zones():
        if not z.GetIsRuleArea():
            continue
        for l in LAYERS:
            if z.IsOnLayer(l):
                if z.GetDoNotAllowTracks():
                    area = pcbnew.SHAPE_POLY_SET(z.Outline())
                    area.Inflate(MM(half_w + 0.1), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
                    grid.fill_poly(blocked[l], area)
                if z.GetDoNotAllowVias():
                    area = pcbnew.SHAPE_POLY_SET(z.Outline())
                    area.Inflate(MM(VIA_D / 2 + 0.1), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
                    grid.fill_poly(via_blocked, area)
    for l in LAYERS:
        blocked[l] &= ~target[l]
    via_blocked |= blocked[LAYERS[0]] | blocked[LAYERS[1]]
    return blocked, via_blocked, target, others


MOVES = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
         (-1, -1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (1, 1, 1.414)]


def astar(grid, blocked, via_blocked, start, goal_cells, goal_layers, goal_xy):
    gr, gc = goal_xy
    def h(r, c):
        dr, dc = abs(r - gr), abs(c - gc)
        return (dr + dc) + (1.414 - 2) * min(dr, dc)
    openq, came, cost = [], {}, {}
    for s in start:
        cost[s] = 0.0
        heapq.heappush(openq, (h(s[1], s[2]), 0.0, s, None))
    while openq:
        f, g, node, prev_dir = heapq.heappop(openq)
        if g > cost.get(node, 1e18):
            continue
        l, r, c = node
        if goal_cells[l][r, c] and l in goal_layers:
            path = [node]
            while node in came:
                node = came[node]
                path.append(node)
            return path[::-1]
        for dr, dc, step in MOVES:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < grid.h and 0 <= nc < grid.w) or blocked[l][nr, nc]:
                continue
            if dr and dc and (blocked[l][r + dr, c] or blocked[l][r, c + dc]):
                continue      # no corner cutting past an obstacle
            turn = 0.0 if prev_dir in (None, (dr, dc)) else 0.6
            nxt = (l, nr, nc)
            ng = g + step + turn
            if ng < cost.get(nxt, 1e18):
                cost[nxt] = ng
                came[nxt] = node
                heapq.heappush(openq, (ng + h(nr, nc), ng, nxt, (dr, dc)))
        if not via_blocked[r, c]:
            nxt = (1 - l, r, c)
            ng = g + VIA_COST
            if ng < cost.get(nxt, 1e18):
                cost[nxt] = ng
                came[nxt] = node
                heapq.heappush(openq, (ng + h(r, c), ng, nxt, None))
    return None


def simplify(path):
    """Collapse the cell path into (layer, [points]) runs with corners only."""
    runs, cur = [], [path[0]]
    for a, b in zip(path, path[1:]):
        if a[0] != b[0]:
            runs.append(cur)
            cur = [b]
        else:
            cur.append(b)
    runs.append(cur)
    out = []
    for run in runs:
        pts = [run[0]]
        for i in range(1, len(run) - 1):
            d0 = (run[i][1] - run[i - 1][1], run[i][2] - run[i - 1][2])
            d1 = (run[i + 1][1] - run[i][1], run[i + 1][2] - run[i][2])
            if d0 != d1:
                pts.append(run[i])
        if len(run) > 1:
            pts.append(run[-1])
        out.append((run[0][0], pts))
    return out


def island(mask, r, c):
    """Cells of mask 4-connected to (r, c)."""
    seen = np.zeros_like(mask)
    if not mask[r, c]:
        return seen
    stack = [(r, c)]
    seen[r, c] = True
    while stack:
        y, x = stack.pop()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                stack.append((ny, nx))
    return seen


def dump(path, bf, bb, bv, s, g, goal):
    """Debug PNG: red = front blocked, blue = back blocked, green = goal cells."""
    import struct, zlib
    h, w = bf.shape
    img = np.full((h, w, 3), 255, np.uint8)
    img[bf] = (255, 160, 160)
    img[bb] = (160, 160, 255)
    img[bf & bb] = (150, 110, 150)
    img[goal[0] | goal[1]] = (0, 200, 0)
    for (r, c), col in ((s, (255, 140, 0)), (g, (0, 120, 0))):
        img[max(0, r - 3):r + 4, max(0, c - 3):c + 4] = col
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)


def endpoint(board, spec):
    """REF:PAD -> (x, y, layers); X,Y,LAYERS -> same."""
    if ":" in spec:
        ref, num = spec.split(":")
        for f in board.GetFootprints():
            if f.GetReference() == ref:
                for p in f.Pads():
                    if p.GetNumber() == num:
                        pos = p.GetPosition()
                        layers = "".join(ch for ch, l in (("F", pcbnew.F_Cu), ("B", pcbnew.B_Cu)) if p.IsOnLayer(l))
                        return pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y), layers
        raise LookupError(spec)
    x, y, layers = spec.split(",")
    return float(x), float(y), layers


def main(src, dst, net, width, start_spec, goal_spec):
    probe = pcbnew.LoadBoard(src)
    sx, sy, sl = endpoint(probe, start_spec)
    nearest = goal_spec == "any"
    gx, gy, gl = (sx, sy, "FB") if nearest else endpoint(probe, goal_spec)
    del probe
    width = float(width)
    board = pcbnew.LoadBoard(src)
    m = float(os.environ.get("MAZE_MARGIN", "20"))
    xs, ys = [sx, gx], [sy, gy]
    if nearest:   # search area must reach the net's other copper
        for it in [p for f in board.GetFootprints() for p in f.Pads()] + list(board.GetTracks()):
            if it.GetNetname() == net:
                xs.append(pcbnew.ToMM(it.GetPosition().x)); ys.append(pcbnew.ToMM(it.GetPosition().y))
        if net in ("GNDA", "GND", "VDD", "VCC"):   # big nets: stay local
            xs, ys = [sx], [sy]
    grid = Grid(min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m)
    blocked, via_blocked, target, others = build_masks(board, grid, net, width / 2)
    lmap = {"F": 0, "B": 1}
    sr, sc = grid.cell(sx, sy)
    gr, gc = grid.cell(gx, gy)
    start = [(lmap[ch], sr, sc) for ch in sl]
    for l, r, c in start:
        blocked[LAYERS[l]][r, c] = False
    # Let the route leave/enter pads that sit close to an LED window.
    yy, xx = np.ogrid[:grid.h, :grid.w]
    near = np.zeros((grid.h, grid.w), bool)
    for r, c in ((sr, sc), (gr, gc)):
        near |= (yy - r) ** 2 + (xx - c) ** 2 <= (PAD_ESCAPE / CELL) ** 2
    for l in LAYERS:
        blocked[l] &= ~(grid.relaxable & near & ~others[l])
    # Goal: for "any", the net's copper not already touching the start; otherwise
    # the goal point and the copper it sits on, so a route stops where it first
    # reaches that copper instead of running alongside it to the exact point.
    goal = {l: np.zeros((grid.h, grid.w), bool) for l in (0, 1)}
    if nearest:
        for l in (0, 1):
            goal[l] = target[LAYERS[l]] & ~island(target[LAYERS[l]], sr, sc)
    else:
        for ch in gl:
            l = lmap[ch]
            goal[l] = island(target[LAYERS[l]], gr, gc) & ~island(target[LAYERS[l]], sr, sc)
            goal[l][gr, gc] = True
            blocked[LAYERS[l]][gr, gc] = False
    if os.environ.get("MAZE_DEBUG"):
        dump(os.environ["MAZE_DEBUG"], blocked[LAYERS[0]], blocked[LAYERS[1]], via_blocked, (sr, sc), (gr, gc), goal)
    path = astar(grid, [blocked[LAYERS[0]], blocked[LAYERS[1]]], via_blocked, start, goal,
                 {lmap[ch] for ch in gl}, (gr, gc))
    if path is None:
        raise SystemExit(f"{net}: no route")
    n = board.FindNet(net)
    runs = simplify(path)
    # Real coordinates for every corner; the ends snap to the exact start/goal points.
    runs = [(layer, [grid.xy(p[1], p[2]) for p in pts]) for layer, pts in runs]
    runs[0][1][0] = (sx, sy)
    if not nearest and path[-1][1:] == (gr, gc):
        runs[-1][1][-1] = (gx, gy)
    for i, (layer, pts) in enumerate(runs):
        for a, b in zip(pts, pts[1:]):
            if a == b:
                continue
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1])))
            t.SetEnd(pcbnew.VECTOR2I(MM(b[0]), MM(b[1])))
            t.SetLayer(LAYERS[layer]); t.SetWidth(MM(width)); t.SetNet(n)
            board.Add(t)
        if i > 0:
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(MM(pts[0][0]), MM(pts[0][1])))
            v.SetWidth(MM(VIA_D)); v.SetDrill(MM(VIA_DRILL)); v.SetLayerPair(*LAYERS); v.SetNet(n)
            board.Add(v)
    vias = len(runs) - 1
    print(f"{net}: routed, {len(path)} cells, {vias} vias", file=sys.stderr)
    board.Save(dst)


if __name__ == "__main__":
    main(*sys.argv[1:])
    sys.stdout.flush()
    os._exit(0)
