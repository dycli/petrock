"""Cut the copper the edits left off the board or clashing, and nothing else.

Copper wholly or partly off the new outline goes. Then, from a DRC JSON report
of the edited board: a track or via in a clearance, short, crossing, hole or
edge violation goes, unless upstream's own report has the same clash between
the same items (e.g. the LED windows' edge clearance: KiCad keeps item ids
through moves). Where it clashes with a stock track (one exactly where upstream
had it), only the moved one goes, so stock copper survives wherever it can.

usage: trim.py BOARD REPORT.json UPSTREAM UPSTREAM_REPORT.json
       (edits BOARD in place; prints the count removed)
"""
import json
import os
import re
import sys

import pcbnew

import widen

TYPES = {"clearance", "shorting_items", "tracks_crossing", "hole_clearance",
         "copper_edge_clearance", "items_not_allowed", "hole_to_hole"}


def geometry(t, dx=0):
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition()
        return ("via", p.x + dx, p.y)
    s, e = t.GetStart(), t.GetEnd()
    return (t.GetLayer(), s.x + dx, s.y, e.x + dx, e.y)


def clash(v):
    """A violation's identity: its type and items; an edge clash with a
    footprint's own cutout (an LED window) by the track and the footprint, since
    DRC may name a different piece of the same window."""
    ids = frozenset(i["uuid"] for i in v["items"])
    if v["type"] == "copper_edge_clearance":
        m = [re.search(r" of (\S+) on Edge\.Cuts", i["description"]) for i in v["items"]]
        refs = [x.group(1) for x in m if x]
        if refs:
            return (v["type"], frozenset(i["uuid"] for i, x in zip(v["items"], m) if not x) | frozenset(refs))
    return (v["type"], ids)


def main(path, report, upstream, up_report):
    up = pcbnew.LoadBoard(upstream)
    dx = pcbnew.FromMM(widen.RIGHT_DX)
    split = pcbnew.FromMM(widen.SPLIT_X)
    stock = {geometry(t, dx if t.GetBoundingBox().Centre().x > split else 0) for t in up.GetTracks()}
    known = {clash(v) for v in json.load(open(up_report))["violations"]}
    board = pcbnew.LoadBoard(path)
    by_uuid = {t.m_Uuid.AsString(): t for t in board.GetTracks()}
    doomed = set()
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline, False)
    for t in board.GetTracks():
        ends = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
        if not all(outline.Contains(p) for p in ends):
            doomed.add(t.m_Uuid.AsString())
    for v in json.load(open(report))["violations"]:
        if v["type"] not in TYPES:
            continue
        copper = [by_uuid[i["uuid"]] for i in v["items"] if i["uuid"] in by_uuid]
        if clash(v) in known:
            continue
        moved = [t for t in copper if geometry(t) not in stock]
        # A stock track goes only if nothing moved is to blame (e.g. the new edge).
        for t in moved or copper:
            doomed.add(t.m_Uuid.AsString())
    for u in doomed:
        board.Remove(by_uuid[u])
    board.Save(path)
    print(len(doomed))


if __name__ == "__main__":
    main(*sys.argv[1:5])
    sys.stdout.flush()
    os._exit(0)
