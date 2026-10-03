"""Delete orphaned copper on the given nets.

Removes track/via groups that reach no pad, then trims segments with a free end
(an end touching no pad, via, zone island or other copper). Stubs that only
overlap other copper, which DRC still calls dangling, are left to drop_dangling.py.

usage: prune.py IN OUT NET [NET...]   (prints how many items it removed)
"""
import os
import sys

import pcbnew

EPS = pcbnew.FromMM(0.005)
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)


def seg_dist(p, a, b):
    ax, ay, bx, by, px, py = a.x, a.y, b.x, b.y, p.x, p.y
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return ((ax + t * dx - px) ** 2 + (ay + t * dy - py) ** 2) ** 0.5


def islands(board, net):
    out = []
    for z in board.Zones():
        if z.GetNetname() == net and not z.GetIsRuleArea():
            for l in LAYERS:
                if z.IsOnLayer(l):
                    fp = z.GetFilledPolysList(l)
                    for i in range(fp.OutlineCount()):
                        o = pcbnew.SHAPE_POLY_SET()
                        o.AddOutline(fp.Outline(i))
                        for h in range(fp.HoleCount(i)):
                            o.AddHole(fp.Hole(i, h))
                        out.append((l, o))
    return out


def touches(t, pt, pads, tracks, isl):
    for p in pads:
        if any(t.IsOnLayer(l) and p.IsOnLayer(l) for l in LAYERS) and p.HitTest(pt):
            return True
    for o in tracks:
        if o is t:
            continue
        if o.GetClass() == "PCB_VIA":
            if (o.GetPosition() - pt).EuclideanNorm() <= o.GetWidth(pcbnew.F_Cu) / 2:
                return True
        elif (t.GetClass() == "PCB_VIA" or o.GetLayer() == t.GetLayer()) and o.HitTest(pt, 0):
            return True       # overlapping copper connects, as in KiCad's own connectivity
    return any(t.IsOnLayer(l) and o.Contains(pt) for l, o in isl)


def padless_groups(board, net, pads, isl):
    """Tracks/vias whose connected group (through copper and zone islands) reaches no pad."""
    tracks = [t for t in board.GetTracks() if t.GetNetname() == net]
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def join(a, b):
        parent[find(a)] = find(b)

    def island_ids(t, pt):
        return [("I", i) for i, (l, o) in enumerate(isl) if t.IsOnLayer(l) and o.Contains(pt)]

    for i, p in enumerate(pads):
        find(("P", i))
        for j, (l, o) in enumerate(isl):
            if p.IsOnLayer(l) and o.Contains(p.GetPosition()):
                join(("P", i), ("I", j))
    for t in tracks:
        k = ("T", t.m_Uuid.AsString())
        find(k)
        ends = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
        for e in ends:
            for i in island_ids(t, e):
                join(k, i)
            for j, p in enumerate(pads):
                if any(t.IsOnLayer(l) and p.IsOnLayer(l) for l in LAYERS) and p.HitTest(e):
                    join(k, ("P", j))
            for o in tracks:
                if o is not t and o.HitTest(e, 0) and (o.GetClass() == "PCB_VIA" or t.GetClass() == "PCB_VIA" or o.GetLayer() == t.GetLayer()):
                    join(k, ("T", o.m_Uuid.AsString()))
    with_pads = {find(("P", i)) for i in range(len(pads))}
    return [t for t in tracks if find(("T", t.m_Uuid.AsString())) not in with_pads]


def dead_items(board, net):
    """Orphan groups first; otherwise segments and vias with a free end."""
    pads = [p for f in board.GetFootprints() for p in f.Pads() if p.GetNetname() == net]
    isl = islands(board, net)
    orphans = padless_groups(board, net, pads, isl)
    if orphans:
        return orphans
    tracks = [t for t in board.GetTracks() if t.GetNetname() == net]
    dead = []
    for t in tracks:
        if t.GetClass() == "PCB_VIA":
            sides = sum(1 for l in LAYERS if any(
                o.GetClass() != "PCB_VIA" and o.GetLayer() == l and
                seg_dist(t.GetPosition(), o.GetStart(), o.GetEnd()) <= t.GetWidth(pcbnew.F_Cu) / 2 for o in tracks)
                or any(p.IsOnLayer(l) and p.HitTest(t.GetPosition()) for p in pads)
                or any(ll == l and o.Contains(t.GetPosition()) for ll, o in isl))
            if sides < 2:
                dead.append(t)
        elif not all(touches(t, e, pads, tracks, isl) for e in (t.GetStart(), t.GetEnd())):
            dead.append(t)
    return dead


def main(src, dst, nets):
    """One pass. Removing items invalidates other SWIG handles (and later loads),
    so callers loop this script until it prints 0."""
    board = pcbnew.LoadBoard(src)
    dead = []
    for net in nets:
        dead += dead_items(board, net)
    for t in dead:
        board.Remove(t)
    board.Save(dst)
    print(len(dead))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
    sys.stdout.flush()
    os._exit(0)
