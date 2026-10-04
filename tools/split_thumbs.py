"""Split each half's inner 1.5u thumb key into two 1u keys at the same angle,
after moving the rest of the thumb cluster onto the index-aligned arc.

The 1.5u key becomes a 1u key on the thumb arc (tools/thumbs.py), turned like
the other thumb keys; a new 1u key goes one row above it. Each key gets a diode
placed as on the neighbouring 1u thumb key (the template). The new key takes
the thumb row's last free column (col0; the pinky and ring columns' fourth keys
took col1 and col2).

Works on any frame: positions come from the parts on the board.
"""
import math
import os
import sys

import pcbnew

import parts
import thumbs

MM = pcbnew.FromMM
EDGE_CLEAR = 0.3              # copper to board edge: JLC's minimum (the outer column's sockets sit at 0.33)
DIODE_GAP = 0.45              # a crowded key diode moves until this clear (solder mask stays between pads)

HALVES = {
    # old key and its diode; template 1u key and diode; new refs; new key's column and row
    "right": dict(half="right", key="SW42", diode="D42", tkey="SW41", tdiode="D41",
                  new_key="SW44", new_diode="D46", col="col0_r", row="row3_r",
                  cluster={"outer": ("SW40", "D40"), "middle": ("SW41", "D41")}),
    "left": dict(half="left", key="SW21", diode="D21", tkey="SW20", tdiode="D20",
                 new_key="SW43", new_diode="D45", col="col0", row="row3",
                 cluster={"outer": ("SW19", "D19"), "middle": ("SW20", "D20")}),
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


def is_clear(part, others, outline, gap=0.3):
    """Every pad of part clears the others' pads by gap mm and sits on the board."""
    layer = pcbnew.B_Cu if part.IsFlipped() else pcbnew.F_Cu
    for p in part.Pads():
        shape = p.GetEffectiveShape(layer)
        if any(o.IsOnLayer(layer) and o.GetEffectiveShape(layer).Collide(shape, MM(gap)) for o in others):
            return False
        if not outline.Contains(p.GetPosition()):
            return False
    return True


def clear_spot(board, part, key_xy, key_deg, offset, outline, ignore, gap=0.3):
    """Place part at the template offset, or the first mirrored variant of it whose
    pads clear every other footprint's pads by gap mm and stay on the board."""
    (lx, ly), drot = offset
    others = [p for f in board.GetFootprints() if f.GetReference() not in ignore for p in f.Pads()]
    for cand in ((lx, ly), (lx, -ly), (-lx, ly), (-lx, -ly), (ly, lx), (-ly, lx), (ly, -lx), (-ly, -lx)):
        place_like(part, key_xy, key_deg, (cand, drot))
        if is_clear(part, others, outline, gap):
            return
    raise RuntimeError(f"no clear spot for {part.GetReference()}")


def free_diodes(board):
    """Re-place, about its own key, any key diode that the moved keys now crowd."""
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline, False)
    outline.Deflate(MM(1.5), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
    fps = list(board.GetFootprints())
    by_ref = {f.GetReference(): f for f in fps}
    for key in [f for f in fps if "SW_choc" in f.GetFPIDAsString()]:
        anode = [p.GetNetname() for p in key.Pads() if p.GetNumber() == "2" and p.GetNetname()]
        diode = by_ref.get(anode[0].split("(")[1].split("-")[0]) if anode and "(" in anode[0] else None
        if diode is None:
            continue
        others = [p for f in board.GetFootprints() if f.GetReference() != diode.GetReference() for p in f.Pads()]
        if not is_clear(diode, others, outline, DIODE_GAP):
            print("moving", diode.GetReference(), "clear of its neighbours")
            clear_spot(board, diode, pos(key), key.GetOrientationDegrees(), local_offset(key, diode), outline,
                       {diode.GetReference()}, DIODE_GAP)


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


def split(board, index, h):
    one = lambda ref: index[ref][0]
    # The outer and middle keys, with their diodes, move onto the
    # index-aligned arc first (tools/thumbs.py); the split keys are placed on it.
    for role, (sx, sy) in thumbs.moves(h["half"]).items():
        parts.drag(board, [one(ref) for ref in h["cluster"][role]], parts.shift(sx, sy))
    old, diode = one(h["key"]), one(h["diode"])
    tkey, tdiode = one(h["tkey"]), one(h["tdiode"])
    # Arc positions (tools/thumbs.py), moved by however far this half has been shifted.
    cx, cy = pos(old)
    up_x, up_y = thumbs.OLD_INNER[h["half"]]
    sx, sy = cx - up_x, cy - up_y
    (lx, ly), (tx, ty), deg = thumbs.inner_keys(h["half"])
    lower, upper = (lx + sx, ly + sy), (tx + sx, ty + sy)

    diode_off = local_offset(tkey, tdiode)
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
    edge = pcbnew.SHAPE_POLY_SET()                 # outer contours only
    for i in range(full.OutlineCount()):
        edge.AddOutline(full.Outline(i))
    edge.Deflate(MM(EDGE_CLEAR), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))

    def fit_edge(k, base=deg):
        """Choc switches mount either way round; turn the key 180 degrees if its
        hot-swap pads would otherwise sit closer than EDGE_CLEAR to the board edge."""
        for turn in (0, 180):
            k.SetOrientationDegrees(base + turn)
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
    # Diodes sit by the socket, so they follow each key's final orientation.
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
    skip = {h["diode"], h["new_diode"]}
    clear_spot(board, d, upper, deg_upper, diode_off, outline, skip)
    clear_spot(board, diode, lower, deg_lower, diode_off, outline, skip | {h["new_diode"]})


def main(src, dst, halves):
    board = pcbnew.LoadBoard(src)
    index = {}
    for f in board.GetFootprints():
        index.setdefault(f.GetReference(), []).append(f)
    for h in halves:
        split(board, index, HALVES[h])
    free_diodes(board)
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:] or ["left", "right"])
    sys.stdout.flush()
    os._exit(0)
