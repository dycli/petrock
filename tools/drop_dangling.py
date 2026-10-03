"""Delete short track stubs that a DRC JSON report flags as dangling.

usage: drop_dangling.py BOARD REPORT.json   (edits BOARD in place)
"""
import json
import os
import sys

import pcbnew

MAX_LEN = pcbnew.FromMM(1.5)
NEAR = pcbnew.FromMM(0.01)


def main(path, report):
    spots = []
    for v in json.load(open(report))["violations"]:
        if v["type"] == "track_dangling":
            for i in v["items"]:
                spots.append(pcbnew.VECTOR2I(pcbnew.FromMM(i["pos"]["x"]), pcbnew.FromMM(i["pos"]["y"])))
    board = pcbnew.LoadBoard(path)
    doomed = []
    for t in board.GetTracks():
        if t.GetClass() != "PCB_TRACK" or t.GetLength() > MAX_LEN:
            continue
        if any((t.GetStart() - s).EuclideanNorm() <= NEAR or (t.GetEnd() - s).EuclideanNorm() <= NEAR for s in spots):
            doomed.append(t)
    for t in doomed:
        print("drop", t.GetNetname(), round(pcbnew.ToMM(t.GetLength()), 3), file=sys.stderr)
        board.Remove(t)
    board.Save(path)


if __name__ == "__main__":
    main(*sys.argv[1:])
    sys.stdout.flush()
    os._exit(0)
