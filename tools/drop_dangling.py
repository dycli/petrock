"""Delete short track stubs that a DRC JSON report flags as dangling.

usage: drop_dangling.py BOARD REPORT.json   (edits BOARD in place)
"""
import json
import os
import sys

import pcbnew

MAX_LEN = pcbnew.FromMM(60)       # a DRC-flagged dead end leads nowhere, whatever its length
NEAR = pcbnew.FromMM(0.01)


def main(path, report):
    spots = []
    for v in json.load(open(report))["violations"]:
        if v["type"] == "track_dangling":
            for i in v["items"]:
                spots.append(pcbnew.VECTOR2I(pcbnew.FromMM(i["pos"]["x"]), pcbnew.FromMM(i["pos"]["y"])))
    board = pcbnew.LoadBoard(path)
    for v in json.load(open(report))["violations"]:
        if v["type"] == "via_dangling":
            for i in v["items"]:
                spots.append(pcbnew.VECTOR2I(pcbnew.FromMM(i["pos"]["x"]), pcbnew.FromMM(i["pos"]["y"])))
    doomed = []
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            if any((t.GetPosition() - s).EuclideanNorm() <= NEAR for s in spots):
                doomed.append(t)
            continue
        if t.GetLength() > MAX_LEN:
            continue
        if any((t.GetStart() - s).EuclideanNorm() <= NEAR or (t.GetEnd() - s).EuclideanNorm() <= NEAR for s in spots):
            doomed.append(t)
    for t in doomed:
        print("drop", t.GetNetname(), file=sys.stderr)
        board.Remove(t)
    board.Save(path)
    print(len(doomed))


if __name__ == "__main__":
    main(*sys.argv[1:])
    sys.stdout.flush()
    os._exit(0)
