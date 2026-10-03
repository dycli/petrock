"""Export a board to Specctra DSN (existing copper locked) or import a routed session."""
import os
import sys

import pcbnew


def export(src, dsn):
    board = pcbnew.LoadBoard(src)
    for t in board.GetTracks():
        t.SetLocked(True)
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        raise SystemExit("DSN export failed")


def import_session(src, ses, dst):
    board = pcbnew.LoadBoard(src)
    if not pcbnew.ImportSpecctraSES(board, ses):
        raise SystemExit("SES import failed")
    for t in board.GetTracks():
        t.SetLocked(False)
    board.Save(dst)


if __name__ == "__main__":
    {"export": export, "import": import_session}[sys.argv[1]](*sys.argv[2:])
    sys.stdout.flush()
    os._exit(0)
