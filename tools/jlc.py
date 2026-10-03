"""JLCPCB assembly files: BOM and placement (CPL) for the SMD parts JLC solders
(all on the back): key diodes, per-key and underglow LEDs, hot-swap sockets.
Everything else (controllers, jacks, reset buttons, OLED headers, trackpoint)
is hand-fitted.

usage: jlc.py BOARD OUT_DIR
"""
import csv
import os
import sys
from collections import defaultdict

import pcbnew

# LCSC part per footprint. The board's own LCSC fields where they're good;
# the diodes have none, and the underglow LED's (C2761796) is nearly out of stock.
PARTS = {
    "kbd:D3_SMD_v2": ("1N4148W", "SOD-123", "C81598"),
    "holykeebs:SW_choc_v1_HS_CPG135001S30_1u": ("Kailh CPG135001S30 choc hot-swap socket", "CPG135001S30", "C5333465"),
    "PCM_marbastlib-various:LED_6028R": ("SK6812MINI-E", "SK6812MINI-E", "C5149201"),
    "LED_SMD:LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm": ("WS2812B-B/W", "SMD5050-4P", "C114586"),
}


def main(path, out):
    board = pcbnew.LoadBoard(path)
    os.makedirs(out, exist_ok=True)
    groups = defaultdict(list)
    rows = []
    for f in board.GetFootprints():
        part = PARTS.get(f.GetFPIDAsString())
        if part is None or not f.GetReference():
            continue
        groups[part].append(f.GetReference())
        p = f.GetPosition()
        rows.append((f.GetReference(), f"{pcbnew.ToMM(p.x):.3f}mm", f"{-pcbnew.ToMM(p.y):.3f}mm",
                     "Bottom" if f.IsFlipped() else "Top", f"{f.GetOrientationDegrees() % 360:.1f}"))
    with open(os.path.join(out, "bom.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC"])
        for (comment, footprint, lcsc), refs in sorted(groups.items()):
            w.writerow([comment, ",".join(sorted(refs, key=lambda r: (r.rstrip("0123456789"), int(r[len(r.rstrip("0123456789")):])))), footprint, lcsc])
    with open(os.path.join(out, "cpl.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        w.writerows(sorted(rows))
    for (comment, _, lcsc), refs in sorted(groups.items()):
        print(f"{len(refs):3d} x {comment} ({lcsc})")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
