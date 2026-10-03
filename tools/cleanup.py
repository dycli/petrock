"""Remove copper orphaned or blocked by the trackpoint edit.

Deletes tracks of nets that no longer exist, tracks that collide with the new
pads (TP1, J1, J3), then repeatedly removes dangling track ends.
"""
import os
import sys

import pcbnew

GONE_NETS = {"Net-(D42-A)"}
# Only nets whose pads were removed or moved can have new dangling ends.
AFFECTED_NETS = {"Net-(D42-A)", "data", "data_r", "VCC", "VDD", "SDA_r", "SCL_r", "row3_r", "col5_r", "GND", "GNDA"}
NEW_PARTS = {"TP1", "J1", "J3"}
CLEARANCE = pcbnew.FromMM(0.2)


def collides(track, pad):
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        if track.IsOnLayer(layer) and pad.IsOnLayer(layer):
            if pad.GetEffectiveShape(layer).Collide(track.GetEffectiveShape(layer), CLEARANCE):
                return True
    return False


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


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    pads = [p for f in board.GetFootprints() for p in f.Pads()]
    new_pads = [p for f in board.GetFootprints() if f.GetReference() in NEW_PARTS for p in f.Pads()]
    doomed = set()
    for t in board.GetTracks():
        if t.GetNetname() in GONE_NETS:
            doomed.add(t.m_Uuid.AsString())
        elif any(p.GetNetCode() != t.GetNetCode() and collides(t, p) for p in new_pads):
            doomed.add(t.m_Uuid.AsString())
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
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
