"""Rip up what blocks a connection the router can't make: plan the route as if
other nets' tracks weren't there (tools/maze.py with MAZE_IGNORE_TRACKS), and
remove every other-net track or via that planned route would clash with, so
the connection can be routed and the removed ones rerouted around it
(tools/autoconnect.py). Nets in KEEP are never ripped up, nor is any track or
via whose id is listed in the file $KEEP_IDS (the stock copper that survived).

usage: ripup.py BOARD NET WIDTH START GOAL   (edits BOARD in place; prints how many items it removed)
"""
import os
import subprocess
import sys
import tempfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
KPY = os.path.join(os.path.dirname(HERE), "bin", "kpy")
CLEAR = pcbnew.FromMM(0.3)
KEEP = ("TP_S",)          # the trackpoint links: routed by their own plan (tools/tp_links.py)


def main(path, net, width, start, goal):
    with tempfile.TemporaryDirectory() as tmp:
        plan = os.path.join(tmp, "plan.kicad_pcb")
        env = dict(os.environ, MAZE_IGNORE_TRACKS="1")
        r = subprocess.run([KPY, os.path.join(HERE, "maze.py"), path, plan, net, width, start, goal],
                           capture_output=True, text=True, env=env)
        if r.returncode or not os.path.exists(plan):
            print(0)
            return
        planned = pcbnew.LoadBoard(plan)
        have = {t.m_Uuid.AsString() for t in pcbnew.LoadBoard(path).GetTracks()}
        route = [t for t in planned.GetTracks() if t.m_Uuid.AsString() not in have and t.GetNetname() == net]
        shapes = [(t, {l: t.GetEffectiveShape(l) for l in (pcbnew.F_Cu, pcbnew.B_Cu) if t.IsOnLayer(l)}) for t in route]
        board = pcbnew.LoadBoard(path)
        keep = set(open(os.environ["KEEP_IDS"]).read().split()) if os.environ.get("KEEP_IDS") else set()
        doomed = []
        for t in board.GetTracks():
            if t.GetNetname() == net or t.GetNetname().startswith(KEEP) or t.m_Uuid.AsString() in keep:
                continue
            for _, sh in shapes:
                if any(t.IsOnLayer(l) and t.GetEffectiveShape(l).Collide(s, CLEAR) for l, s in sh.items()):
                    doomed.append(t)
                    break
        for t in doomed:
            print("rip", t.GetNetname(), file=sys.stderr)
            board.Remove(t)
        board.Save(path)
        print(len(doomed))


if __name__ == "__main__":
    main(*sys.argv[1:6])
    sys.stdout.flush()
    os._exit(0)
