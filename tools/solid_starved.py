"""Connect surface-mount pads that DRC reports as starved of thermal spokes
solidly to their pour. They are reflow-soldered at assembly, so they don't need
thermal relief; hand-soldered through-hole pads are left alone.

usage: solid_starved.py BOARD REPORT.json   (edits BOARD in place)
"""
import json
import os
import re
import sys

import pcbnew


def main(path, report):
    starved = set()
    for v in json.load(open(report))["violations"]:
        if v["type"] == "starved_thermal":
            for i in v["items"]:
                m = re.match(r"Pad (\S+) \[[^\]]*\] of (\S+) on", i["description"])
                if m:
                    starved.add((m.group(2), m.group(1)))
    board = pcbnew.LoadBoard(path)
    n = 0
    for f in board.GetFootprints():
        for p in f.Pads():
            if (f.GetReference(), p.GetNumber()) in starved and p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
                p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
                n += 1
    board.Save(path)
    print(n)


if __name__ == "__main__":
    main(*sys.argv[1:])
    sys.stdout.flush()
    os._exit(0)
