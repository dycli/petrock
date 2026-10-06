"""Route the board by rule, as by hand: columns straight up the front, rows
along the back under each key, the same short diode links on every key, and
the column wires gathered into an even bus to the controller. Handles both
boards: the 40 (trackpoint on each half) and the 41 (extra thumb key on the left).

usage: route.py IN OUT
"""
import os
import sys

import pcbnew

SRC, OUT = sys.argv[1:3]
b = pcbnew.LoadBoard(SRC)
for t in list(b.GetTracks()):            # whatever copper placement dragged along goes: all is drawn here
    b.Remove(t)
MM = pcbnew.FromMM
F, B = pcbnew.F_Cu, pcbnew.B_Cu
W = 0.25                 # signal width
ROW_DY = 3.0             # row line below each key centre
COL_DX = 4.0             # column line right of each key centre (passes left of the side hole)
BUS_DY = 4.4             # first bus wire below the row-0 key centre
BUS_PITCH = 0.65


def fp(ref):
    return b.FindFootprintByReference(ref)


def pad(ref, num, tht=None):
    """Position (mm) of a part's pad; tht=True picks the plated hole one."""
    for p in fp(ref).Pads():
        if p.GetNumber() == num and (tht is None or (p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH) == tht):
            return pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
    raise KeyError((ref, num))


def net(ref, num):
    for p in fp(ref).Pads():
        if p.GetNumber() == num:
            return p.GetNet()


def track(n, layer, pts, w=W):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if (x1, y1) == (x2, y2):
            continue
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1)))
        t.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
        t.SetWidth(MM(w))
        t.SetLayer(layer)
        t.SetNet(n)
        b.Add(t)


def via(n, p):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(MM(p[0]), MM(p[1])))
    v.SetWidth(MM(0.6))
    v.SetDrill(MM(0.4))
    v.SetNet(n)
    b.Add(v)


def jog(x0, y0, x1, y1):
    """Horizontal from (x0,y0) to (x1,y1) with one 45-degree step at the end."""
    dy = y1 - y0
    s = 1 if x1 >= x0 else -1
    return [(x0, y0), (x1 - s * abs(dy), y0), (x1, y1)]


import math

DIODE = (-6.6, -3.7)     # diode centre from its key centre: anode within socket pad 2's height, clear of the standoffs


def local(key):
    """Map key-local mm offsets (unrotated key, y down) onto the board."""
    f = fp(key)
    cx, cy = pcbnew.ToMM(f.GetPosition().x), pcbnew.ToMM(f.GetPosition().y)
    t = math.radians(f.GetOrientationDegrees())
    return lambda x, y: (cx + x * math.cos(t) + y * math.sin(t), cy - x * math.sin(t) + y * math.cos(t))


# Every diode in the same place beside its key.
for f in list(b.GetFootprints()):
    r = f.GetReference()
    if not r.startswith("SW") or not net(r, "2").GetNetname().startswith("Net-(D"):
        continue
    an = net(r, "2").GetNetname()
    d = fp(an[len("Net-("):an.index("-A")])
    x, y = local(r)(*DIODE)
    d.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    d.SetOrientationDegrees(90 + f.GetOrientationDegrees())

DUAL = any(f.GetReference() == "A4" for f in b.GetFootprints())   # the 40: a trackpoint on the left too

# ---- the key matrix of the left half ------------------------------------
# Main keys: socket unrotated, diode to its left. Columns by x, rows by y.
keys = {}
for f in b.GetFootprints():
    r = f.GetReference()
    if r.startswith("SW") and f.GetOrientationDegrees() == 0 and pcbnew.ToMM(f.GetPosition().x) < 155:
        keys[r] = (pcbnew.ToMM(f.GetPosition().x), pcbnew.ToMM(f.GetPosition().y))
diode_of = {}
for r in keys:
    anode = net(r, "2").GetNetname()            # e.g. Net-(D2-A)
    diode_of[r] = anode[len("Net-("):anode.index("-A")]

xs = [round(x, 2) for x, _ in keys.values()]
keys = {r: p for r, p in keys.items() if xs.count(round(p[0], 2)) >= 3}   # the 41's extra thumb has no column
cols = sorted({round(x, 2) for x, _ in keys.values()})
grid = {}                                       # (col, row) -> ref, for rows 0..2
for r, (x, y) in keys.items():
    c = cols.index(round(x, 2))
    grid.setdefault(c, []).append((y, r))
for c in grid:
    grid[c].sort()

main = {}                                       # (c, row) -> ref for the 3 full rows
for c, ys in grid.items():
    for i, (y, r) in enumerate(ys[:3]):
        main[(c, i)] = r

# Diode links: anode straight across to the socket's pad 2; cathode straight
# down to the row line under the key.
for (c, i), r in main.items():
    cx, cy = keys[r]
    d = diode_of[r]
    ax, ay = pad(d, "2")
    kx, ky = pad(d, "1")
    track(net(d, "2"), B, [(ax, ay), (cx - 3.24, ay)])
    track(net(d, "1"), B, [(cx - 7.0, ky), (cx - 7.0, cy + ROW_DY)])

# Rows 0..2: one line under the keys, a 45-degree step between columns.
rows_end = {}
for i in range(3):
    n = net(diode_of[main[(0, i)]], "1")
    pts = []
    for c in range(len(cols)):
        cx, cy = keys[main[(c, i)]]
        y = cy + ROW_DY
        if not pts:
            pts.append((cx - 7.0, y))
        else:                              # a 45-degree step centred on the gap between the keys
            x0, y0 = pts[-1]
            gap = cols[c] - 9.0
            h = abs(y - y0) / 2
            pts += [(gap - h, y0), (gap + h, y), (cx - 7.0, y)]
    rows_end[i] = (n, pts)

# Columns: straight down the front through every switch pin of the column.
for c in range(len(cols)):
    ys = grid[c]
    top, bot = ys[0][1], ys[-1][1]
    x = cols[c] + COL_DX
    n = net(top, "1")
    track(n, F, [(x, pad(top, "1", tht=True)[1]), (x, pad(bot, "1", tht=True)[1])])

# ---- into the controller --------------------------------------------------
U = "U1"


def pin_of(netname):
    for p in fp(U).Pads():
        if p.GetNetname() == netname:
            return pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
    raise KeyError(netname)


LEFT_PINS = pin_of("col0")[0]            # the controller's pin row facing the keys
GAP = 0.65                               # an even step between neighbouring wires

# Rows: through the gap between two near-side pins, then across underneath the
# controller to their own pin on the far side.
INSIDE = LEFT_PINS + 2.84                # first wire lane inside the controller
for i, (n, pts) in rows_end.items():
    px, py = pin_of(n.GetNetname())
    x, y = pts[-1]
    if i < 2:
        gy = py - 6.35 if i == 0 else py + 3.81      # half way between two near-side pins
        pts += jog(x, y, LEFT_PINS - 1.2, gy)[1:]
        pts += [(INSIDE, gy), (INSIDE, py + (1 if gy > py else -1)), (INSIDE + 1, py), (px, py)]
    else:
        # Below the controller's last pin, then up the inside.
        lane = INSIDE + 1.5 * (i - 1)
        drop = LEFT_PINS + 1.45 + 0.65 * (i - 2)
        pts += [(drop, y), (drop, 95.0)]
        pts += [(lane, 95.0 - (lane - drop)), (lane, py + 1), (lane + 1, py), (px, py)]
    track(n, B, pts)

# Columns: each drops to the back in the gap under the middle row, joins an even
# bus there, and comes up again beside the controller to fan into its pins.
BUS_DY, BUS_PITCH = 4.0, 0.7
ncol = len(cols)
cy1 = [keys[main[(c, 1)]][1] for c in range(ncol)]
vias_at = {}
for c in range(ncol):
    k = ncol - 1 - c                     # the inner column's wire runs on top
    n = net(main[(c, 0)], "1")
    x = cols[c] + COL_DX
    y = cy1[c] + BUS_DY + k * BUS_PITCH
    via(n, (x, y))
    pts = [(x, y)]
    for j in range(c, ncol - 1):
        dy = cy1[j + 1] - cy1[j]
        x0 = cols[j] + 9.0 - 0.85 + (k * BUS_PITCH * (1 - math.sqrt(2)) if dy > 0 else k * BUS_PITCH * (math.sqrt(2) - 1))
        pts += [(x0, pts[-1][1]), (x0 + abs(dy), pts[-1][1] + dy)]
    vx = LEFT_PINS - 1.86 - k * GAP
    pts.append((vx, pts[-1][1]))
    track(n, B, pts)
    via(n, (vx, pts[-1][1]))
    px, py = pin_of(n.GetNetname())
    vy = pts[-1][1]
    if vy - py > 0.7:
        track(n, F, [(vx, vy), (vx, py + 0.6), (vx + 0.6, py), (px, py)])
    else:
        track(n, F, [(vx, vy), (px, py)])

# ---- the bottom row, thumbs and screen ------------------------------------
L = {r: local(r) for r in ("SW1", "SW13", "SW20", "SW21", "SW43") + (() if DUAL else ("SW19",))}


def diode_links(r, end=None):
    """The same two links as on every key, in the key's own frame; the cathode
    link runs down to the row line, or to END where the row meets it sooner."""
    an = net(r, "2").GetNetname()
    d = an[len("Net-("):an.index("-A")]
    f = local(r)
    ly_a, ly_k = DIODE[1] - 1.77, DIODE[1] + 1.77     # anode above, cathode below
    track(net(d, "2"), B, [f(DIODE[0], ly_a), f(-3.24, ly_a)])
    track(net(d, "1"), B, [f(-7.0, ly_k), end or f(-7.0, ROW_DY)])


def meet(p, u, q, v):
    """Where the line p + t u crosses the line q + s v."""
    det = u[0] * -v[1] - u[1] * -v[0]
    t = ((q[0] - p[0]) * -v[1] - (q[1] - p[1]) * -v[0]) / det
    return p[0] + t * u[0], p[1] + t * u[1]


def cut(a, c, e, d=1.0):
    """Replace the corner C (coming from A, going to E) by a chamfer D mm each way."""
    def unit(p, q):
        ln = math.hypot(q[0] - p[0], q[1] - p[1])
        return (q[0] - p[0]) / ln, (q[1] - p[1]) / ln
    ui, uo = unit(a, c), unit(c, e)
    return [(c[0] - ui[0] * d, c[1] - ui[1] * d), (c[0] + uo[0] * d, c[1] + uo[1] * d)]


def along(f, a, b2):
    (x1, y1), (x2, y2) = f(*a), f(*b2)
    return (x1, y1), (x2 - x1, y2 - y1)


row3 = net(diode_of[main[(0, 2)]], "1").GetNetname().replace("row2", "row3")
n3 = b.FindNet(row3)
UNDER = 128.6                            # under the trackpoint driver
s1, s13 = L["SW1"](-7, ROW_DY), L["SW13"](-7, ROW_DY)
e13 = L["SW13"](8, ROW_DY)
# Down the thumb's own diode line to meet the run under the driver.
p20, u20 = along(L["SW20"], (-7, ROW_DY), (-7, ROW_DY + 1))
low = meet(p20, u20, (0, UNDER), (1, 0))
g13, h13 = cols[1] - 9.0, abs(s13[1] - s1[1]) / 2
pts = [s1, (g13 - h13, s1[1]), (g13 + h13, s13[1]), s13]
if DUAL:
    pts += [e13, (e13[0] + UNDER - e13[1], UNDER), low, p20]
else:
    # The 41: straight on through the extra thumb's diode to the next thumb's diode line.
    s19 = L["SW19"](-7, ROW_DY)
    g19, h19 = (e13[0] + s19[0]) / 2, abs(s19[1] - s13[1]) / 2
    pts += [(g19 - h19, s13[1]), (g19 + h19, s19[1]), s19, meet(s19, (1, 0), p20, u20)]
track(n3, B, pts)
# Under the first thumb, on to the next thumb's diode line.
q20, v20 = along(L["SW20"], (-7, ROW_DY), (0, ROW_DY))
q21, v21 = along(L["SW21"], (-7, ROW_DY), (-7, ROW_DY - 1))
m21 = meet(q20, v20, q21, v21)
track(n3, B, [p20, m21])
for r in L:
    diode_links(r, m21 if r == "SW21" else None)
# Up beside the second thumb's diode to the third thumb, which sits in line above it.
f21 = L["SW21"]
s43 = L["SW43"](-7, ROW_DY)
track(n3, B, [f21(-7, 0.6), f21(-7.6, 0), f21(-7.6, -12.8), f21(-7, -13.4), s43])
# Then into the controller, down the gap beside the screen header.
px, py = pin_of(row3)
drop = LEFT_PINS + 1.45 + 0.65
lane = INSIDE + 3.0
sq = L["SW43"](-7 - (s43[0] - drop) / math.cos(math.radians(30)), ROW_DY)   # square off the thumb line
track(n3, B, [s43, sq, (drop, 95.0), (lane, 95.0 - (lane - drop)), (lane, py + 1), (lane + 1, py), (px, py)])

# Thumb columns, on the front: the middle, index and inner columns run on to
# the outer, middle and inner thumb (the bottom pinky and ring keys hold the
# pinky and ring columns in that row).
THUMBS = ("SW20", "SW21", "SW43") if DUAL else ("SW19", "SW20", "SW21")
for r, c in zip(THUMBS, (2, 3, 4)):
    for p in fp(r).Pads():
        if p.GetNumber() == "1":
            p.SetNet(net(main[(c, 0)], "1"))
n3c, n4, n5 = (net(main[(c, 0)], "1") for c in (2, 3, 4))
x3, x4 = cols[2] + COL_DX, cols[3] + COL_DX
y4 = 103.5                                                        # under the row-2 keys, over the standoff
y3 = 129.8                                                        # the middle column's run along the bottom edge
c20, w20 = along(L["SW20"], (COL_DX, -3.75), (COL_DX, -2.75))   # the outer thumb's column line, downward
if DUAL:
    # Middle column: down past the trackpoint's outer side, along the bottom
    # edge, and up the outer thumb's own column line.
    j3 = meet(c20, w20, (0, y3), (1, 0))
    x3o = x3 - 3.5                                                # clear of the trackpoint's link vias
    y3j = pad("SW16", "1", tht=True)[1] + 7.0                      # below the middle column's last key
    track(n3c, F, [(x3, pad("SW16", "1", tht=True)[1]), (x3, y3j), (x3o, y3j + 3.5), (x3o, y3 - 1), (x3o + 1, y3), j3, c20])
    # Index column: under the row-2 keys, then down and across to the middle thumb.
    p21 = pad("SW21", "1", tht=True)
    xd = 124.5
    track(n4, F, [(x4, pad("SW17", "1", tht=True)[1]), (x4, y4 - 1), (x4 + 1, y4), (xd - 1, y4), (xd, y4 + 1),
                  (xd, p21[1] - (p21[0] - 2.0 - xd)), (p21[0] - 2.0, p21[1]), p21])
    # Inner column: below the screen header, then down to the inner thumb.
    p18 = pad("SW18", "1", tht=True)
    p43 = pad("SW43", "1", tht=True)
    y5 = 99.5
    track(n5, F, [p18, (p18[0] + y5 - p18[1], y5), (p43[0] - 1.5, y5), (p43[0], y5 + 1.5), p43])
else:
    # The 41. Middle column: one diagonal on to the extra thumb's column line.
    c19 = L["SW19"](COL_DX, -3.75)
    d3 = c19[1] - 3.0
    track(n3c, F, [(x3, pad("SW16", "1", tht=True)[1]), (x3, d3 - (c19[0] - x3)), (c19[0], d3), c19])
    # Index column: under the row-2 keys, then down the outer thumb's column line.
    j4 = meet((118.0, y4), (1, 1), c20, w20)
    track(n4, F, [(x4, pad("SW17", "1", tht=True)[1]), (x4, y4 - 1), (x4 + 1, y4), (118.0, y4), j4, c20])
    # Inner column: across to beside the controller, down and over to the middle thumb.
    p18, p21 = pad("SW18", "1", tht=True), pad("SW21", "1", tht=True)
    xd = 124.5
    track(n5, F, [p18, (xd - 1, p18[1]), (xd, p18[1] + 1), (xd, p21[1] - (p21[0] - 2.0 - xd)), (p21[0] - 2.0, p21[1]), p21])
    # The inner thumb keeps column 0: below the screen header and up beside the
    # controller's near pins, into its pin from the inside.
    p43 = pad("SW43", "1", tht=True)
    c0 = pin_of(net("SW43", "1").GetNetname())
    track(net("SW43", "1"), F, [p43, (p43[0], 101.0), (p43[0] - 1.5, 99.5), (LEFT_PINS + 2.84, 99.5), (LEFT_PINS + 1.84, 98.5),
                                (LEFT_PINS + 1.84, c0[1] + 1), (LEFT_PINS + 0.84, c0[1]), c0])

# Screen: straight up from its header into the controller.
for name in ("SDA", "SCL"):
    hx, hy = pad("J2", "1" if name == "SDA" else "2")
    px, py = pin_of(name)
    track(net("J2", "1" if name == "SDA" else "2"), F, [(hx, hy), (hx, py + 1), (hx + 1, py), (px, py)])

# ---- the long single wires ------------------------------------------------
def edge_line(x0, x1):
    """The board-edge segment spanning x0..x1, as (point, unit direction)."""
    for d in b.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_SEGMENT:
            a, c = d.GetStart(), d.GetEnd()
            ax, ay, cx_, cy_ = (pcbnew.ToMM(v) for v in (a.x, a.y, c.x, c.y))
            if min(ax, cx_) <= x0 and max(ax, cx_) >= x1 and abs(cy_ - ay) < abs(cx_ - ax):
                if ax > cx_:
                    ax, ay, cx_, cy_ = cx_, cy_, ax, ay
                ln = math.hypot(cx_ - ax, cy_ - ay)
                return (ax, ay), ((cx_ - ax) / ln, (cy_ - ay) / ln)
    raise KeyError((x0, x1))


def offset(line, d):
    (px_, py_), (ux, uy) = line
    return (px_ - uy * d, py_ + ux * d), (ux, uy)        # d mm inside (below) the edge


top = edge_line(95, 150)
# Trackpoint data/clock and power: out of the driver eastwards on the back, up
# a clear lane between the middle and index columns on the front, then along
# the top edge, parallel to it, to the controller.
A = "A4"
lane = {"VCC": 89.0, "TP_CLK_L": 89.65, "TP_DATA_L": 90.3}
east = {"TP_DATA_L": 103.1, "TP_CLK_L": 103.75, "VCC": 104.4}
turn = {"TP_DATA_L": 102.6, "TP_CLK_L": 101.95, "VCC": 101.3}     # above the sensor links
edge_off = {"VCC": 1.0, "TP_CLK_L": 1.65, "TP_DATA_L": 2.3}
for name in ("TP_DATA_L", "TP_CLK_L", "VCC") if DUAL else ():
    p = next(q for q in fp(A).Pads() if q.GetNetname() == name)
    hx, hy = pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
    n = p.GetNet()
    track(n, B, [(hx, hy), (east[name], hy), (east[name], turn[name]), (lane[name], turn[name])])
    via(n, (lane[name], turn[name]))
    q, u = offset(top, edge_off[name])
    corner = meet((lane[name], 0), (0, 1), q, u)
    pts = [(lane[name], turn[name])] + cut((lane[name], turn[name]), corner, (corner[0] + u[0], corner[1] + u[1]))
    if name == "VCC":
        drop = meet((126.6, 0), (0, 1), q, u)
        far = meet((147.8, 0), (0, 1), q, u)
        j = pad("J1", "D")
        pts += [far, (far[0], 71.3), (j[0], 71.3)]
        track(n, F, pts)
        via(n, drop)
        pv = pin_of("VCC")
        track(n, B, [drop, (drop[0], pv[1]), pv])
    else:
        x_drop = 140.6 if name == "TP_DATA_L" else 141.4
        d = meet((x_drop, 0), (0, 1), q, u)
        pp = pin_of(name)
        pts += [d, (x_drop, pp[1] - 1), (x_drop + 1, pp[1]), pp]
        track(n, F, pts)

if not DUAL:
    # The 41: no trackpoint on the left, so power just runs along the top edge
    # between the controller and the jack.
    q, u = offset(top, edge_off["VCC"])
    drop, far = meet((126.6, 0), (0, 1), q, u), meet((147.8, 0), (0, 1), q, u)
    n = next(p for p in fp("U1").Pads() if p.GetNetname() == "VCC").GetNet()
    track(n, F, [drop, far, (far[0], 71.3), (pad("J1", "D")[0], 71.3)])
    via(n, drop)
    pv = pin_of("VCC")
    track(n, B, [drop, (drop[0], pv[1]), pv])


# Sensor to driver: nested L-shapes on the front from the sensor's link pads,
# up, out past the driver's side and down to a column of vias level with the
# driver's link pads, then straight across on the back.
def sensor_links(S, D_):
    links = [q.GetNumber() for q in fp(S).Pads() if q.GetNumber().startswith("S")]
    side = 1 if pad(D_, links[0])[0] > pcbnew.ToMM(fp(D_).GetPosition().x) else -1
    links.sort(key=lambda n: -side * pad(S, n)[0])             # nearest the driver's link side first
    side_x = side * max(side * pad(D_, n)[0] for n in links)
    for k, n in enumerate(links):
        sx, sy = pad(S, n)
        dx, dy = pad(D_, n)
        run_y = sy - 1.82 - k * 0.65                           # each a step higher than the last
        vx = side_x + side * (1.0 + k * 0.95)
        nn = net(S, n)
        track(nn, F, [(sx, sy), (sx, run_y), (vx, run_y), (vx, dy)])
        via(nn, (vx, dy))
        track(nn, B, [(vx, dy), (dx, dy)])


if DUAL:
    sensor_links("A3", "A4")

# Reset: straight across inside the controller, out between two far-side pins,
# down to the button.
pr = pin_of("reset")
r1 = pad("RSW1", "1")
far_x = pin_of("row0")[0]
# (out between the data and ground pins, so the two ground pins can be tied together)
track(net("RSW1", "1"), F, [pr, (far_x - 2.11, pr[1]), (far_x - 0.84, pr[1] - 1.27), (far_x + 0.92, pr[1] - 1.27),
                              (145.3, pr[1] - 0.27), (145.3, r1[1] - 1), (146.3, r1[1]), r1])
gnd = next(p for p in fp("U1").Pads() if p.GetNumber() == "3").GetNet()
track(gnd, F, [(far_x, 69.1), (far_x, 71.64)], 0.5)
# The trackpoint drivers' ground pads sit boxed in by their own wires: a short
# link to a via into the other side's pour.
if DUAL:
    dg = next(p for p in fp("A4").Pads() if p.GetNumber() == "1")
    dgp = (pcbnew.ToMM(dg.GetPosition().x), pcbnew.ToMM(dg.GetPosition().y))
    track(dg.GetNet(), B, [dgp, (dgp[0], dgp[1] - 2.1)], 0.5)
    via(dg.GetNet(), (dgp[0], dgp[1] - 2.1))
# Jack data: out along the outer edge, outside everything else.
pdx = pin_of("data")
jb = pad("J1", "B")
track(net("J1", "B"), F, [pdx, (151.9, pdx[1]), (152.9, pdx[1] - 1), (152.9, jb[1] + 1), (151.9, jb[1]), jb])
# Screen power: on the back, under its header and up the outer side to the jack.
j3 = pad("J2", "3")
jd = pad("J1", "D")
track(net("J2", "3"), B, [j3, (j3[0], 98.6), (144.6, 98.6), (145.6, 97.6), (145.6, 71.3), (jd[0], 71.3)])

# ==== the right half ========================================================
# Same rules; its controller faces the other way, so the rows reach their pins
# from the key side and the column bus passes under the controller to climb
# its outer side.
U = "U2"
rk = {}
for f in b.GetFootprints():
    r = f.GetReference()
    if r.startswith("SW") and f.GetOrientationDegrees() == 0 and pcbnew.ToMM(f.GetPosition().x) > 155:
        rk[r] = (pcbnew.ToMM(f.GetPosition().x), pcbnew.ToMM(f.GetPosition().y))
rcols = sorted({round(x, 2) for x, _ in rk.values()}, reverse=True)     # pinky (outer) first
rgrid = {}
for r, (x, y) in rk.items():
    rgrid.setdefault(rcols.index(round(x, 2)), []).append((y, r))
for c in rgrid:
    rgrid[c].sort()
rmain = {(c, i): rgrid[c][i][1] for c in rgrid for i in range(3)}
rdiode = {}
for r in rk:
    an = net(r, "2").GetNetname()
    rdiode[r] = an[len("Net-("):an.index("-A")]
def rpass(c, i):
    """Where row I crosses key C's diode link on the right half. The diode is on
    the key's inner side, right by the gap: if the next key in is higher, the
    row has already climbed to its level, so the link meets a straight run."""
    y = rk[rmain[(c, i)]][1] + ROW_DY
    if c + 1 < len(rcols):
        y = min(y, rk[rmain[(c + 1, i)]][1] + ROW_DY)
    return y


for (c, i), r in rmain.items():
    cx, cy = rk[r]
    d = rdiode[r]
    ax, ay = pad(d, "2")
    kx, ky = pad(d, "1")
    track(net(d, "2"), B, [(ax, ay), (cx - 3.24, ay)])
    track(net(d, "1"), B, [(cx - 7.0, ky), (cx - 7.0, rpass(c, i))])
# Columns on the front.
for c in range(len(rcols)):
    ys = rgrid[c]
    top, bot = ys[0][1], ys[-1][1]
    x = rcols[c] + COL_DX
    track(net(top, "1"), F, [(x, pad(top, "1", tht=True)[1]), (x, pad(bot, "1", tht=True)[1])])
# Rows 0..2 under the keys, inwards, then down a lane beside the controller's
# near pins and straight in.
NEAR = pin_of("row0_r")[0]
for i in range(3):
    n = net(rdiode[rmain[(0, i)]], "1")
    pts = []
    for c in range(len(rcols)):
        cx, cy = rk[rmain[(c, i)]]
        y, yp = cy + ROW_DY, rpass(c, i)
        if not pts:
            pts = [(cx - 7.0, yp)]
            continue
        x0, y0 = pts[-1]
        if y0 != y:                        # down to this key's level: a step centred on the gap
            gap = rcols[c] + 9.0
            h = abs(y - y0) / 2
            pts += [(gap + h, y0), (gap - h, y)]
        if yp != y:                        # up to the next key's level, under this one, to meet its diode link
            pts += [(cx - 7.0 + (y - yp), y)]
        pts.append((cx - 7.0, yp))
    px, py = pin_of(n.GetNetname())
    lane_x = NEAR + 1.65 + 0.65 * (2 - i)
    x, y = pts[-1]
    pts += [(lane_x, y), (lane_x, py + (1 if py < y else -1)), (lane_x - 1, py), (px, py)]
    track(n, B, pts)
# Column bus in the gap under the middle row, inwards to beside the inner keys,
# up to the front, under the controller and up its outer side into the far pins.
ncol = len(rcols)
rcy1 = [rk[rmain[(c, 1)]][1] for c in range(ncol)]
FAR = pin_of("col1_r")[0]
for c in range(ncol):
    k = (ncol - 1) - c                     # wire level: the inner column's on top, the pinky's at the bottom
    n = net(rmain[(c, 0)], "1")
    x = rcols[c] + COL_DX
    y = rcy1[c] + BUS_DY + k * BUS_PITCH
    via(n, (x, y))
    pts = [(x, y)]
    for j in range(c, ncol - 1):           # westwards: an even 45-degree step at each column boundary
        dy = rcy1[j + 1] - rcy1[j]
        x0 = rcols[j] - 9.0 + 0.85 + (k * BUS_PITCH * (math.sqrt(2) - 1) if dy > 0 else -k * BUS_PITCH * (math.sqrt(2) - 1))
        pts += [(x0, pts[-1][1]), (x0 - abs(dy), pts[-1][1] + dy)]
    vx = rcols[-1] - 5.81 + 0.65 * k
    pts.append((vx, pts[-1][1]))
    track(n, B, pts)
    via(n, (vx, pts[-1][1]))
    # Front: down to an even run under the controller, then up its outer side.
    run = 93.26 + 0.6 * k
    up = FAR - 1.33 - 0.65 * k
    px, py = pin_of(n.GetNetname())
    vy = pts[-1][1]
    track(n, F, [(vx, vy), (vx, run - 1), (vx - 1, run), (up + 0.4, run), (up, run - 0.4), (up, py + 0.6), (up + 0.6, py), (px, py)])

# Right thumbs: the middle, index and inner columns run on to the outer,
# middle and inner thumb, as on the left.
for r, c in (("SW41", 2), ("SW42", 3), ("SW44", 4)):
    for p in fp(r).Pads():
        if p.GetNumber() == "1":
            p.SetNet(net(rmain[(c, 0)], "1"))
RL = {r: local(r) for r in ("SW22", "SW34", "SW41", "SW42", "SW44")}
n3r = b.FindNet("row3_r")
s34 = RL["SW34"](-7, ROW_DY)
s22 = RL["SW22"](-7, 0)[0], s34[1]       # the pinky's link stops level with the ring key: no step
p41, u41 = along(RL["SW41"], (-7, ROW_DY), (-7, ROW_DY + 1))
low41 = meet(p41, u41, (0, UNDER), (1, 0))
track(n3r, B, [s22, s34, (s34[0] - (UNDER - s34[1]), UNDER), low41, p41])
for r in RL:
    diode_links(r, s22 if r == "SW22" else None)
q42, v42 = along(RL["SW42"], (-7, ROW_DY), (0, ROW_DY))
q41, v41 = along(RL["SW41"], (-7, ROW_DY), (-7, ROW_DY - 1))
track(n3r, B, [q42, meet(q42, v42, q41, v41)])
f42 = RL["SW42"]
s44 = RL["SW44"](-7, ROW_DY)
track(n3r, B, [f42(-7, 0.6), f42(-7.6, 0), f42(-7.6, -12.8), f42(-7, -13.4), s44])
p44, w44 = along(RL["SW44"], (-7, ROW_DY), (0, ROW_DY))
px, py = pin_of("row3_r")
up3 = px - 2.05
track(n3r, B, [s44, meet(p44, w44, (up3, 0), (0, 1)), (up3, py + 1), (up3 + 1, py), (px, py)])
# Thumb columns on the front.
n3c, n4c, n5c = (net(rmain[(c, 0)], "1") for c in (2, 3, 4))
x3 = rcols[2] + COL_DX
c41, w41 = along(RL["SW41"], (COL_DX, -3.75), (COL_DX, -2.75))
track(n3c, F, [(x3, pad("SW37", "1", tht=True)[1]), (x3, y3 - 1), (x3 - 1, y3), meet(c41, w41, (0, y3), (1, 0)), c41])
x4 = rcols[3] + COL_DX
y4r = 102.9                                  # above the sensor's links
p42 = pad("SW42", "1", tht=True)
xd = 186.3                                   # beside the standoff
track(n4c, F, [(x4, pad("SW38", "1", tht=True)[1]), (x4, y4r - 1), (x4 - 1, y4r), (xd + 1, y4r), (xd, y4r + 1),
               (xd, p42[1] - (xd - p42[0])), p42])
x5 = rcols[4] + COL_DX
y5r = 102.3
p44t = pad("SW44", "1", tht=True)
track(n5c, F, [(x5, pad("SW39", "1", tht=True)[1]), (x5, y5r - 1), (x5 - 1, y5r), (p44t[0] + 1, y5r), (p44t[0], y5r + 1), p44t])
# Screen: on the back, straight up from its header into the near pins.
for name, num in (("SDA_r", "1"), ("SCL_r", "2")):
    hx, hy = pad("J4", num)
    px, py = pin_of(name)
    track(net("J4", num), B, [(hx, hy), (hx, py + 1), (hx + 1, py), (px, py)])
sensor_links("A1", "A2")
# Trackpoint data/clock and power: west out of the driver on the back, up the
# lane between the index and middle columns, along the top edge to the controller.
topr = edge_line(160, 220)
lane = {"TP_DATA": 221.6, "TP_CLK": 222.25, "VDD": 222.9}
west = {"VDD": 209.0, "TP_CLK": 208.35, "TP_DATA": 207.7}
turn = {"TP_DATA": 101.3, "TP_CLK": 101.95, "VDD": 102.6}
edge_off = {"VDD": 1.0, "TP_CLK": 1.65, "TP_DATA": 2.3}
for name in ("TP_DATA", "TP_CLK", "VDD"):
    p = next(q for q in fp("A2").Pads() if q.GetNetname() == name)
    hx, hy = pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
    n = p.GetNet()
    track(n, B, [(hx, hy), (west[name], hy), (west[name], turn[name]), (lane[name], turn[name])])
    via(n, (lane[name], turn[name]))
    q, u = offset(topr, edge_off[name])
    corner = meet((lane[name], 0), (0, 1), q, u)
    pts = [(lane[name], turn[name])] + cut((lane[name], turn[name]), corner, (corner[0] - u[0], corner[1] - u[1]))
    if name == "VDD":
        down = meet((166.6, 0), (0, 1), q, u)
        pts += [down, (166.6, 71.6)]
        track(n, F, pts)
        track(n, F, [(166.6, 71.6), pin_of("VDD")])
        track(n, F, [(166.6, 71.6), (pad("J3", "D")[0], 71.6)])
    else:
        x_drop = 186.75 if name == "TP_DATA" else 186.1
        pp = pin_of(name)
        pts += [meet((x_drop, 0), (0, 1), q, u), (x_drop, pp[1] - 1), (x_drop - 1, pp[1]), pp]
        track(n, F, pts)
# Screen power: on the back, under its header and up the outer edge to the jack.
j3, jd = pad("J4", "3"), pad("J3", "D")
track(net("J4", "3"), B, [j3, (j3[0], 98.6), (159.7, 98.6), (158.7, 97.6), (158.7, 72.2), (159.7, 71.2), (jd[0], 71.2)])
# Reset: on the back, down beside the controller's far pins to the button.
pr, r1 = pin_of("reset_r"), pad("RSW2", "1")
track(net("RSW2", "1"), B, [pr, (166.2, pr[1]), (166.2, r1[1] - 1), (165.2, r1[1]), r1])
# Jack data: across inside the controller on the front, over its top on the back.
pdx, jb = pin_of("data_r"), pad("J3", "B")
track(net("J3", "B"), F, [pdx, (178.0, pdx[1]), (178.0, 63.4), (177.0, 62.4), (169.0, 62.4)])
via(net("J3", "B"), (169.0, 62.4))
track(net("J3", "B"), B, [(169.0, 62.4), (jb[0], 62.4), jb])

dg = next(p for p in fp("A2").Pads() if p.GetNumber() == "1")
dgp = (pcbnew.ToMM(dg.GetPosition().x), pcbnew.ToMM(dg.GetPosition().y))
track(dg.GetNet(), B, [dgp, (dgp[0] - 0.74, dgp[1] + 1.65)], 0.5)
via(dg.GetNet(), (dgp[0] - 0.74, dgp[1] + 1.65))
# The screen header's ground pin: a short link south into open pour.
g4 = pad("J4", "4")
track(net("J4", "4"), B, [g4, (g4[0], g4[1] + 2.5)], 0.5)

# ---- finish: every bend sharper than 120 degrees gets a chamfer --------------
def chamfer_bends(d=1.0):
    ends = {}
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            continue
        for end in (0, 1):
            p = t.GetStart() if end == 0 else t.GetEnd()
            ends.setdefault((t.GetNetCode(), t.GetLayer(), p.x, p.y), []).append((t, end))
    taken = {(pcbnew.ToMM(v.GetPosition().x), pcbnew.ToMM(v.GetPosition().y)) for v in b.GetTracks() if v.GetClass() == "PCB_VIA"}
    for f in b.GetFootprints():
        for q in f.Pads():
            taken.add((pcbnew.ToMM(q.GetPosition().x), pcbnew.ToMM(q.GetPosition().y)))
    for (code, layer, x, y), both in ends.items():
        if len(both) != 2 or (pcbnew.ToMM(x), pcbnew.ToMM(y)) in taken:
            continue
        (t1, e1), (t2, e2) = both
        def far(t, e):
            q = t.GetEnd() if e == 0 else t.GetStart()
            return q.x - x, q.y - y
        a, c = far(t1, e1), far(t2, e2)
        la, lc = math.hypot(*a), math.hypot(*c)
        if la == 0 or lc == 0 or (a[0] * c[0] + a[1] * c[1]) / (la * lc) < -0.5 - 1e-9:
            continue                                   # gentler than 120 degrees: already a 45-degree style bend
        dd = min(MM(d), la / 2, lc / 2)
        pa = pcbnew.VECTOR2I(int(x + a[0] / la * dd), int(y + a[1] / la * dd))
        pc = pcbnew.VECTOR2I(int(x + c[0] / lc * dd), int(y + c[1] / lc * dd))
        (t1.SetStart if e1 == 0 else t1.SetEnd)(pa)
        (t2.SetStart if e2 == 0 else t2.SetEnd)(pc)
        n = pcbnew.PCB_TRACK(b)
        n.SetStart(pa)
        n.SetEnd(pc)
        n.SetWidth(min(t1.GetWidth(), t2.GetWidth()))
        n.SetLayer(layer)
        n.SetNetCode(code)
        b.Add(n)


chamfer_bends()

b.Save(OUT)
sys.stdout.flush()
os._exit(0)
