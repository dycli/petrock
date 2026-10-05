"""Free the nice!nano's high-frequency pins 1 and 2 (D1/D0) for the trackpoint
(tools/outer_thumb.py): each controller's TRRS data line moves from pin 2 to
pin 11 (D8; wired QMK on an RP2040 runs split serial on any pin, and a wireless
build doesn't use the jack). The stock copper to pin 2 is cut by tools/trim.py
and the line rerouted.

usage: pins.py IN OUT
"""
import os
import sys

import pcbnew

SERIAL_FROM, SERIAL_TO = "2", "11"


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    for f in board.GetFootprints():
        if f.GetFPIDAsString() != "holykeebs:ProMicro_1mm_holes":
            continue
        pads = {p.GetNumber(): p for p in f.Pads()}
        pads[SERIAL_TO].SetNet(pads[SERIAL_FROM].GetNet())
        pads[SERIAL_FROM].SetNetCode(0)
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
