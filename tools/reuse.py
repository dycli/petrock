"""How much of upstream's track length survives unchanged on a built board.

usage: reuse.py UPSTREAM BOARD
"""
import os
import sys

import pcbnew

import trim
import widen


def tracks(board, shifted):
    dx = pcbnew.FromMM(widen.RIGHT_DX) if shifted else 0
    split = pcbnew.FromMM(widen.SPLIT_X)
    return {trim.geometry(t, dx if shifted and t.GetBoundingBox().Centre().x > split else 0): t.GetLength()
            for t in board.GetTracks() if t.GetClass() != "PCB_VIA"}


up = tracks(pcbnew.LoadBoard(sys.argv[1]), True)
out = tracks(pcbnew.LoadBoard(sys.argv[2]), False)
kept = sum(L for g, L in up.items() if g in out)
total = sum(up.values())
new = sum(L for g, L in out.items() if g not in up)
print(f"stock track kept unchanged: {100 * kept / total:.0f}% ({pcbnew.ToMM(kept):.0f} of {pcbnew.ToMM(total):.0f} mm); "
      f"moved or new: {pcbnew.ToMM(new):.0f} mm")
sys.stdout.flush()
os._exit(0)
