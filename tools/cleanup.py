"""Remove copper orphaned or blocked by an edit.

usage: cleanup.py IN OUT REF,REF,...   (the footprints that were added or moved)


Deletes tracks of nets that no longer exist, tracks that collide with the new
pads (TP1, TP2) or sit in a no-track rule area, then repeatedly removes
dangling track ends on the nets the edit touched.
"""
import os
import sys

import pcbnew

GONE_NETS = {"Net-(D40-A)"}
CLEARANCE = pcbnew.FromMM(0.2)
EDGE_CLEAR = pcbnew.FromMM(0.5)


def collides(track, pad):
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        if track.IsOnLayer(layer) and pad.IsOnLayer(layer):
            if pad.GetEffectiveShape(layer).Collide(track.GetEffectiveShape(layer), CLEARANCE):
                return True
    return False


def in_area(zone, track):
    s, e = track.GetStart(), track.GetEnd()
    pts = [pcbnew.VECTOR2I(int(s.x + (e.x - s.x) * k / 8), int(s.y + (e.y - s.y) * k / 8)) for k in range(9)]
    return any(zone.Outline().Contains(p) for p in pts)


def share_layer(a, b):
    return any(a.IsOnLayer(l) and b.IsOnLayer(l) for l in (pcbnew.F_Cu, pcbnew.B_Cu))


def connected_end(board, track, point, pads, others):
    for p in pads:
        if p.GetNetCode() == track.GetNetCode() and share_layer(p, track):
            if p.HitTest(point):
                return True
    for o in others:
        if o is track or o.GetNetCode() != track.GetNetCode():
            continue
        if o.GetClass() == "PCB_VIA":
            if (o.GetPosition() - point).EuclideanNorm() <= o.GetWidth(pcbnew.F_Cu) // 2 and share_layer(o, track):
                return True
        elif o.GetLayer() == track.GetLayer() or track.GetClass() == "PCB_VIA":
            if o.HitTest(point, 0):
                return True
    for z in board.Zones():
        if z.GetNetCode() == track.GetNetCode():
            for layer in z.GetLayerSet().Seq():
                if track.IsOnLayer(layer) and z.HitTestFilledArea(layer, point):
                    return True
    return False


def main(src, dst, parts):
    """parts: references of footprints that were added or moved."""
    board = pcbnew.LoadBoard(src)
    NEW_PARTS = set(parts.split(","))
    pads = [p for f in board.GetFootprints() for p in f.Pads()]
    new_pads = [p for f in board.GetFootprints() if f.GetReference() in NEW_PARTS for p in f.Pads()]
    # Nets that can have new dangling ends: those of the changed parts, nets that
    # disappeared, and (below) nets whose copper is cut for colliding.
    AFFECTED_NETS = {p.GetNetname() for p in new_pads if p.GetNetname()} | GONE_NETS
    doomed = set()
    banned = [z for z in board.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowTracks()]
    # Copper must stay EDGE_CLEAR from edges the edit created (listed by
    # widen.py/top_edge.py in $NEW_EDGES); upstream's own edges are left alone.
    edges = []
    if os.environ.get("NEW_EDGES"):
        for line in open(os.environ["NEW_EDGES"]):
            x0, y0, x1, y1 = map(float, line.split())
            edges.append(pcbnew.SEG(pcbnew.VECTOR2I(pcbnew.FromMM(x0), pcbnew.FromMM(y0)),
                                    pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1))))

    def near_edge(t):
        if t.GetClass() == "PCB_VIA":
            return False
        seg = pcbnew.SEG(t.GetStart(), t.GetEnd())
        limit = EDGE_CLEAR + t.GetWidth() // 2
        return any(e.Distance(seg) < limit for e in edges)

    for t in board.GetTracks():
        if t.GetNetname() in GONE_NETS:
            doomed.add(t.m_Uuid.AsString())
        elif any(p.GetNetCode() != t.GetNetCode() and collides(t, p) for p in new_pads) or \
                any(any(t.IsOnLayer(l) for l in z.GetLayerSet().Seq()) and in_area(z, t) for z in banned) or \
                near_edge(t):
            doomed.add(t.m_Uuid.AsString())
            AFFECTED_NETS.add(t.GetNetname())
    removed = 0
    while True:
        tracks = [t for t in board.GetTracks() if t.m_Uuid.AsString() not in doomed]
        dangling = set()
        for t in tracks:
            if t.GetClass() == "PCB_VIA" or t.GetNetname() not in AFFECTED_NETS:
                continue
            for pt in (t.GetStart(), t.GetEnd()):
                if not connected_end(board, t, pt, pads, tracks):
                    dangling.add(t.m_Uuid.AsString())
                    break
        for t in tracks:
            if t.GetClass() == "PCB_VIA" and t.GetNetname() in AFFECTED_NETS:
                hits = sum(1 for o in tracks if o is not t and o.GetClass() != "PCB_VIA" and o.GetNetCode() == t.GetNetCode()
                           and t.GetPosition() in (o.GetStart(), o.GetEnd()))
                on_pad = any(p.GetNetCode() == t.GetNetCode() and p.HitTest(t.GetPosition()) for p in pads)
                if hits + on_pad < 2 and not any(z.GetNetCode() == t.GetNetCode() for z in board.Zones()):
                    dangling.add(t.m_Uuid.AsString())
        if not dangling - doomed:
            break
        doomed |= dangling
    for t in list(board.GetTracks()):
        if t.m_Uuid.AsString() in doomed:
            print("remove", t.GetClass(), t.GetNetname(), t.GetLayerName(),
                  [round(pcbnew.ToMM(v), 2) for v in (t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y)])
            board.Remove(t)
            removed += 1
    print(f"removed {removed}", file=sys.stderr)
    if os.environ.get("AFFECTED_OUT"):
        with open(os.environ["AFFECTED_OUT"], "a") as f:
            f.writelines(n + "\n" for n in sorted(AFFECTED_NETS))
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.stdout.flush()
    os._exit(0)
