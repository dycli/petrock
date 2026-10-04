"""Take the lighting off the board: every per-key and underglow LED, the LED
supply diodes (D43, D44) and the copper of the nets only they used (the LED
supply and data chain, and each controller's LED pin). Ground and supply copper
that served only LEDs is left as dead ends for the build's final strip.

usage: no_leds.py IN OUT
"""
import os
import sys

import pcbnew

LED_FOOTPRINTS = ("PCM_marbastlib-various:LED_6028R", "LED_SMD:LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm")
SUPPLY_DIODES = ("D43", "D44")


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    doomed = [f for f in board.GetFootprints()
              if f.GetFPIDAsString() in LED_FOOTPRINTS or f.GetReference() in SUPPLY_DIODES]
    keep = set()                     # nets some other part still uses
    for f in board.GetFootprints():
        if f in doomed:
            continue
        for p in f.Pads():
            if not (f.GetReference().startswith("U") and p.GetNumber() == "1"):    # the controllers' LED pin
                keep.add(p.GetNetname())
    gone = {p.GetNetname() for f in doomed for p in f.Pads()} - keep
    for f in board.GetFootprints():
        if f.GetReference().startswith("U"):
            for p in f.Pads():
                if p.GetNetname() in gone:
                    p.SetNetCode(0)
    doomed += [t for t in board.GetTracks() if t.GetNetname() in gone]
    print(len(doomed), "items;", len(gone), "nets:", " ".join(sorted(gone)[:6]), "...")
    for item in doomed:              # last: removing leaves other handles stale
        board.Remove(item)
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
