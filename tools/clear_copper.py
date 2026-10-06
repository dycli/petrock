"""Remove every track and via, leaving parts, pours and rule areas: the board
is then routed afresh (tools/route.py). Runs alone: pcbnew's Python crashes if a
process carries on working after removing tracks.

usage: clear_copper.py BOARD   (edits BOARD in place)
"""
import os
import sys

import pcbnew

board = pcbnew.LoadBoard(sys.argv[1])
for t in list(board.GetTracks()):
    board.Remove(t)
board.Save(sys.argv[1])
sys.stdout.flush()
os._exit(0)
