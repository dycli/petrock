"""Delete short track stubs that a DRC JSON report flags as dangling.

A dangling via (copper on one layer only) that still joins two or more track
ends on that layer is swapped for short tracks from its centre to those ends,
so removing it doesn't open a gap.

usage: drop_dangling.py BOARD REPORT.json   (edits BOARD in place)
"""
import json
import os
import re
import sys

import pcbnew

MAX_LEN = pcbnew.FromMM(60)       # a DRC-flagged dead end leads nowhere, whatever its length
NEAR = pcbnew.FromMM(0.01)


def main(path, report):
    # Each flagged track by net, layer and length, at the spot DRC reports.
    flagged = []
    for v in json.load(open(report))["violations"]:
        if v["type"] == "track_dangling":
            for i in v["items"]:
                m = re.match(r"Track \[(.*)\] on (\S+), length ([\d.eE+-]+) mm", i["description"])
                if m:
                    flagged.append((m.group(1), m.group(2), float(m.group(3)),
                                    pcbnew.VECTOR2I(pcbnew.FromMM(i["pos"]["x"]), pcbnew.FromMM(i["pos"]["y"]))))
    board = pcbnew.LoadBoard(path)
    via_spots = []
    for v in json.load(open(report))["violations"]:
        if v["type"] == "via_dangling":
            for i in v["items"]:
                via_spots.append(pcbnew.VECTOR2I(pcbnew.FromMM(i["pos"]["x"]), pcbnew.FromMM(i["pos"]["y"])))
    tracks = [t for t in board.GetTracks() if t.GetClass() != "PCB_VIA"]
    doomed, bridges = [], []
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            if any((t.GetPosition() - s).EuclideanNorm() <= NEAR for s in via_spots):
                doomed.append(t)
                c, r = t.GetPosition(), t.GetWidth(pcbnew.F_Cu) // 2
                for o in tracks:
                    if o.GetNetCode() != t.GetNetCode():
                        continue
                    for e in (o.GetStart(), o.GetEnd()):
                        if (e - c).EuclideanNorm() <= r and e != c:
                            bridges.append((t.GetNetCode(), o.GetLayer(), o.GetWidth(), c, e))
            continue
        if t.GetLength() > MAX_LEN:
            continue
        # Several tracks can meet at the reported spot: the flagged one is the
        # one with that net, layer and length.
        for net, layer, length, spot in flagged:
            if (t.GetNetname() == net and t.GetLayerName() == layer and abs(pcbnew.ToMM(t.GetLength()) - length) < 0.001
                    and min((t.GetStart() - spot).EuclideanNorm(), (t.GetEnd() - spot).EuclideanNorm()) <= NEAR):
                doomed.append(t)
                break
    for net, layer, width, a, b in bridges:
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(a)
        t.SetEnd(b)
        t.SetLayer(layer)
        t.SetWidth(width)
        board.Add(t)
        t.SetNetCode(net)
    for t in doomed:
        print("drop", t.GetNetname(), file=sys.stderr)
        board.Remove(t)
    board.Save(path)
    print(len(doomed))


if __name__ == "__main__":
    main(*sys.argv[1:])
    sys.stdout.flush()
    os._exit(0)
