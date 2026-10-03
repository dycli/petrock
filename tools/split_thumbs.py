"""Split each half's inner 1.5u thumb key into two 1u keys at the same angle,
after moving the rest of the thumb cluster onto the index-aligned arc.

The 1.5u key becomes a 1u key on the thumb arc (tools/thumbs.py), turned like
the other thumb keys; a new 1u key goes one row above it. Each key gets a diode and a
per-key LED placed as on the neighbouring 1u thumb key (the template). The new
key uses its row's spare column (col2) and its LED is inserted in the RGB chain
right after the moved key's LED.

Works on any frame: positions come from the parts on the board.
"""
import math
import os
import sys

import pcbnew

import thumbs

MM = pcbnew.FromMM
EDGE_CLEAR = 0.3              # copper to board edge: JLC's minimum (the outer column's sockets sit at 0.33)

HALVES = {
    # old key, its LED and diode; template 1u key, LED, diode; new refs; new key's column; chain/power/ground nets
    "right": dict(half="right", key="SW42", led="LED54", diode="D42", tkey="SW41", tled="LED53", tdiode="D41",
                  new_key="SW44", new_led="LED56", new_diode="D46", col="col2_r", row="row3_r",
                  power="Net-(D44-K)", ground="GNDA",
                  cluster=("SW40", "D40", "LED52", "SW41", "D41", "LED53")),
    "left": dict(half="left", key="SW21", led="LED27", diode="D21", tkey="SW20", tled="LED26", tdiode="D20",
                 new_key="SW43", new_led="LED55", new_diode="D45", col="col2", row="row3",
                 power="Net-(D43-K)", ground="GND",
                 cluster=("SW19", "D19", "LED25", "SW20", "D20", "LED26")),
}


def V(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


def pos(f):
    p = f.GetPosition()
    return pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)


def rot(x, y, deg):
    """KiCad footprint rotation (CCW on screen, y down)."""
    a = math.radians(deg)
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


def local_offset(key, part):
    """Part position in the key's own frame, and its rotation relative to the key."""
    kx, ky = pos(key)
    px, py = pos(part)
    return rot(px - kx, py - ky, -key.GetOrientationDegrees()), part.GetOrientationDegrees() - key.GetOrientationDegrees()


def place_like(part, key_xy, key_deg, offset):
    (lx, ly), drot = offset
    dx, dy = rot(lx, ly, key_deg)
    part.SetOrientationDegrees(key_deg + drot)
    part.SetPosition(V(key_xy[0] + dx, key_xy[1] + dy))


def fresh_copy(template):
    """Copy a footprint with new IDs for it and everything in it. A plain copy keeps
    the template's pad IDs, and KiCad's connectivity then mixes up the two parts."""
    f = pcbnew.FOOTPRINT(template)
    f.ResetUuid()
    for item in list(f.Pads()) + list(f.GraphicalItems()) + list(f.GetFields()):
        item.ResetUuid()
    return f


def clear_spot(board, part, key_xy, key_deg, offset, outline, ignore):
    """Place part at the template offset, or the first mirrored variant of it whose
    pads clear every other footprint's pads by 0.3 mm and stay on the board."""
    (lx, ly), drot = offset
    others = [p for f in board.GetFootprints() if f.GetReference() not in ignore for p in f.Pads()]
    for cand in ((lx, ly), (lx, -ly), (-lx, ly), (-lx, -ly), (ly, lx), (-ly, lx), (ly, -lx), (-ly, -lx)):
        place_like(part, key_xy, key_deg, (cand, drot))
        ok = True
        for p in part.Pads():
            shape = p.GetEffectiveShape(pcbnew.B_Cu if part.IsFlipped() else pcbnew.F_Cu)
            if any(o.IsOnLayer(pcbnew.B_Cu if part.IsFlipped() else pcbnew.F_Cu) and
                   o.GetEffectiveShape(pcbnew.B_Cu if part.IsFlipped() else pcbnew.F_Cu).Collide(shape, MM(0.3))
                   for o in others):
                ok = False
                break
            if not outline.Contains(p.GetPosition()):
                ok = False
                break
        if ok:
            return
    raise RuntimeError(f"no clear spot for {part.GetReference()}")


def pad_corners(p):
    """Corners of the pad's rectangle, from its centre, size and angle. (KiCad's own
    shape is stale right after the footprint turns, so it's computed here.)"""
    layer = pcbnew.B_Cu if p.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu
    size = p.GetSize(layer)
    w, h = pcbnew.ToMM(size.x), pcbnew.ToMM(size.y)
    cx, cy = pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
    out = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        dx, dy = rot(sx * w / 2, sy * h / 2, p.GetOrientationDegrees())
        out.append(V(cx + dx, cy + dy))
    return out


def net(board, name):
    n = board.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
    return n


def pad(f, num):
    (p,) = [p for p in f.Pads() if p.GetNumber() == num and p.GetNetname()] or \
           [p for p in f.Pads() if p.GetNumber() == num][:1]
    return p


def split(board, index, h):
    one = lambda ref: index[ref][0]
    # The outer and middle keys, with their diodes and LEDs, move onto the
    # index-aligned arc first (tools/thumbs.py); the split keys are placed on it.
    sx, sy = thumbs.shift(h["half"])
    for ref in h["cluster"]:
        one(ref).Move(V(sx, sy))
    old, led, diode = one(h["key"]), one(h["led"]), one(h["diode"])
    tkey, tled, tdiode = one(h["tkey"]), one(h["tled"]), one(h["tdiode"])
    # Arc positions (tools/thumbs.py), moved by however far this half has been shifted.
    cx, cy = pos(old)
    up_x, up_y = thumbs.OLD_INNER[h["half"]]
    sx, sy = cx - up_x, cy - up_y
    (lx, ly), (tx, ty), deg = thumbs.inner_keys(h["half"])
    lower, upper = (lx + sx, ly + sy), (tx + sx, ty + sy)

    led_off, diode_off = local_offset(tkey, tled), local_offset(tkey, tdiode)
    col_net, anode_net = old.Pads()[0], None
    nets = {p.GetNumber(): p.GetNetname() for p in old.Pads() if p.GetNetname()}

    def new_key(ref, at, pad_nets):
        k = fresh_copy(tkey)
        k.SetReference(ref)
        k.SetOrientationDegrees(deg)
        k.SetPosition(V(*at))
        for p in k.Pads():
            if p.GetNumber() in pad_nets:
                p.SetNet(net(board, pad_nets[p.GetNumber()]))
            elif p.GetNetname():
                p.SetNetCode(0)
        board.Add(k)
        return k

    full = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(full, False)
    edge = pcbnew.SHAPE_POLY_SET()                 # outer contours only, not the LED windows
    for i in range(full.OutlineCount()):
        edge.AddOutline(full.Outline(i))
    edge.Deflate(MM(EDGE_CLEAR), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))

    def fit_edge(k):
        """Choc switches mount either way round; turn the key 180 degrees if its
        hot-swap pads would otherwise sit closer than EDGE_CLEAR to the board edge."""
        for turn in (0, 180):
            k.SetOrientationDegrees(deg + turn)
            pads = [p for p in k.Pads() if p.GetNetname()]
            if all(all(edge.Contains(c) for c in pad_corners(p)) for p in pads):
                return
        bad = [(p.GetNumber(), pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)) for p in k.Pads() if p.GetNetname()
               for c in pad_corners(p) if not edge.Contains(c)][:4]
        raise RuntimeError(f"{k.GetReference()}: socket pads too close to the edge either way {bad}")

    k_lower = new_key(h["key"], lower, nets)                         # same matrix position as before
    fit_edge(k_lower)
    new_anode = f"Net-({h['new_diode']}-A)"
    k_upper = new_key(h["new_key"], upper, {"1": h["col"], "2": new_anode})
    fit_edge(k_upper)
    # The LED pokes up into the switch's light window, and diodes sit by the
    # socket, so both follow each key's final orientation.
    deg_lower, deg_upper = k_lower.GetOrientationDegrees(), k_upper.GetOrientationDegrees()
    board.Remove(old)

    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline, False)
    outline.Deflate(MM(1.5), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
    d = fresh_copy(tdiode)
    d.SetReference(h["new_diode"])
    for p in d.Pads():
        p.SetNet(net(board, h["row"] if p.GetNumber() == "1" else new_anode))
    board.Add(d)
    # Both keys are in place now, so each diode is checked against both.
    skip = {h["diode"], h["new_diode"], h["led"]}
    clear_spot(board, d, upper, deg_upper, diode_off, outline, skip)
    clear_spot(board, diode, lower, deg_lower, diode_off, outline, skip | {h["new_diode"]})

    # LEDs: pad 4 is data in, pad 2 data out, 1 power, 3 ground.
    place_like(led, lower, deg_lower, led_off)
    old_out = pad(led, "2").GetNetname()
    link = f"Net-({h['led']}-DOUT)"
    pad(led, "2").SetNet(net(board, link))
    l = fresh_copy(tled)
    l.SetReference(h["new_led"])
    for p in l.Pads():
        p.SetNet(net(board, {"1": h["power"], "2": old_out, "3": h["ground"], "4": link}[p.GetNumber()]))
    board.Add(l)
    place_like(l, upper, deg_upper, led_off)


def main(src, dst, halves):
    board = pcbnew.LoadBoard(src)
    index = {}
    for f in board.GetFootprints():
        index.setdefault(f.GetReference(), []).append(f)
    for h in halves:
        split(board, index, HALVES[h])
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:] or ["left", "right"])
    sys.stdout.flush()
    os._exit(0)
