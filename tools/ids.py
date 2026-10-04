"""Print the ids of every track and via on a board (for $KEEP_IDS).

usage: ids.py BOARD
"""
import os
import sys

import pcbnew

for t in pcbnew.LoadBoard(sys.argv[1]).GetTracks():
    print(t.m_Uuid.AsString())
sys.stdout.flush()
os._exit(0)
