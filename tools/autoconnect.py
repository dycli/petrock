"""Route every connection DRC reports as missing until none are left or no
progress is made. Each DRC pass routes one missing connection per net (a
second one on the same net may already be closed by the first).

usage: autoconnect.py BOARD   (edits BOARD in place)
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KCLI = os.path.join(ROOT, "bin", "kcli")
KPY = os.path.join(ROOT, "bin", "kpy")
WIDTH = {"GND": 0.5, "GNDA": 0.5, "Net-(D43-K)": 0.5, "Net-(D44-K)": 0.5, "VCC": 0.3, "VDD": 0.3}


def missing(board, refill=False):
    """DRC's missing connections. Between passes the ground pour isn't refilled
    (the slow part); the final pass refills so ground connections are exact."""
    with tempfile.NamedTemporaryFile(suffix=".json") as rep:
        extra = ["--refill-zones", "--save-board"] if refill else []
        subprocess.run([KCLI, "pcb", "drc", *extra, "--format", "json", "-o", rep.name, board],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return json.load(open(rep.name)).get("unconnected_items", [])


def end(item):
    """X,Y,LAYERS for one side of an unconnected pair, or None for zones."""
    d = item["description"]
    if d.startswith("Zone"):
        return None
    layers = "B" if "on B.Cu" in d else "F" if "on F.Cu" in d and not d.startswith("Via") else "FB"
    if d.startswith("PTH") or d.startswith("Via"):
        layers = "FB"
    return f"{item['pos']['x']:.4f},{item['pos']['y']:.4f},{layers}"


def main(board):
    failed = set()
    tried = set()      # a pair still open after being routed once won't close by retrying
    refill = False
    while True:
        todo = []
        for v in missing(board, refill):
            a, b = v["items"]
            m = re.search(r"\[([^\]]*)\]", a["description"])
            ea, eb = end(a), end(b)
            if ea is None and eb is not None:
                ea, eb = eb, "any"          # a pad or track cut off from its zone
            elif eb is None and ea is not None:
                eb = "any"
            if m and ea and eb and (m.group(1), ea, eb) not in failed | tried:
                todo.append((m.group(1), ea, eb))
        if not todo:
            # Only zone-to-zone gaps (or nothing) left: reconnect cut-off ground groups.
            r = subprocess.run([KPY, os.path.join(HERE, "islands.py"), board, "GND", "GNDA"],
                               capture_output=True, text=True)
            for line in r.stdout.splitlines():
                if line.startswith(("GND ", "GNDA ")):
                    net, start = line.split()
                    if (net, start, "any") not in failed | tried:
                        todo.append((net, start, "any"))
        if not todo:
            if not refill:          # confirm against a fresh pour before stopping
                refill = True
                continue
            break
        refill = False
        seen = set()
        for net, ea, eb in todo:
            if net in seen:
                continue
            seen.add(net)
            tried.add((net, ea, eb))
            width = WIDTH.get(net, 0.25)
            r = subprocess.run([KPY, os.path.join(HERE, "maze.py"), board, board, net, str(width), ea, eb],
                               capture_output=True, text=True)
            out = (r.stdout + r.stderr).strip().splitlines()
            print(out[-1] if out else f"{net}: ?", file=sys.stderr, flush=True)
            if "no route" in r.stdout + r.stderr or r.returncode:
                failed.add((net, ea, eb))
    left = [v for v in missing(board)]
    print(f"{len(left)} unconnected left", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1])
