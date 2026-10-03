"""For each ground net, print one pad from every group of copper (pads, tracks,
vias, zone islands) that isn't connected to the net's largest group.

usage: islands.py BOARD NET...   prints "NET X,Y,LAYERS" lines
"""
import os
import sys

import pcbnew

LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)


def groups(board, net):
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def join(a, b):
        parent[find(a)] = find(b)

    isl = []
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
                        isl.append((l, o))
    pads = [p for f in board.GetFootprints() for p in f.Pads() if p.GetNetname() == net]
    tracks = [t for t in board.GetTracks() if t.GetNetname() == net]
    for i, p in enumerate(pads):
        find(("P", i))
        for j, (l, o) in enumerate(isl):
            if p.IsOnLayer(l) and o.Contains(p.GetPosition()):
                join(("P", i), ("I", j))
        for k, t in enumerate(tracks):
            if any(t.IsOnLayer(l) and p.IsOnLayer(l) for l in LAYERS) and \
                    p.GetEffectiveShape(pcbnew.B_Cu if p.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu).Collide(
                        t.GetEffectiveShape(t.GetLayer() if t.GetClass() != "PCB_VIA" else pcbnew.F_Cu), 0):
                join(("P", i), ("T", k))
    for k, t in enumerate(tracks):
        find(("T", k))
        ends = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
        for e in ends:
            for j, (l, o) in enumerate(isl):
                if t.IsOnLayer(l) and o.Contains(e):
                    join(("T", k), ("I", j))
            for m, o in enumerate(tracks):
                if m != k and o.HitTest(e, 0) and (o.GetClass() == "PCB_VIA" or t.GetClass() == "PCB_VIA" or o.GetLayer() == t.GetLayer()):
                    join(("T", k), ("T", m))
    comp = {}
    for i in range(len(pads)):
        comp.setdefault(find(("P", i)), []).append(pads[i])
    return sorted(comp.values(), key=len, reverse=True)


def main(path, nets):
    board = pcbnew.LoadBoard(path)
    for net in nets:
        for g in groups(board, net)[1:]:
            p = g[0]
            pos = p.GetPosition()
            layers = "".join(c for c, l in (("F", pcbnew.F_Cu), ("B", pcbnew.B_Cu)) if p.IsOnLayer(l))
            print(f"{net} {pcbnew.ToMM(pos.x):.4f},{pcbnew.ToMM(pos.y):.4f},{layers}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
    sys.stdout.flush()
    os._exit(0)
