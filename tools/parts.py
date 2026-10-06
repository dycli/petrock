"""Helpers for moving and removing keys with the parts that belong to them."""
import pcbnew


def key_parts(board, key):
    """A key switch's diode (on its second pin's net), as a list."""
    by_ref = {f.GetReference(): f for f in board.GetFootprints()}
    anode = [p.GetNetname() for p in key.Pads() if p.GetNumber() == "2" and p.GetNetname()][0]
    return [by_ref[anode.split("(")[1].split("-")[0]]]


def remove_key(board, key):
    """The key and its diode, to remove (call board.Remove on them last: removing
    items leaves other handles stale)."""
    return [key, *key_parts(board, key)]


def drag(board, footprints, move, turn=0.0, inside=None):
    """Move footprints the way dragging them in KiCad does, keeping their copper:
    move maps a point (mm) to its new place, turn is the change in orientation.
    Track ends and vias inside (a test on points, mm) move with them, as does a
    track end on one of the footprints' pads; a track crossing out stretches;
    other copper stays.
    (The build clears all copper after placing and routes afresh, tools/route.py.)"""
    mm = lambda v: (pcbnew.ToMM(v.x), pcbnew.ToMM(v.y))
    V = lambda p: pcbnew.VECTOR2I(pcbnew.FromMM(p[0]), pcbnew.FromMM(p[1]))
    pads = [p for f in footprints for p in f.Pads()]

    def on_pad(point, item):
        return any(p.HitTest(point) and any(p.IsOnLayer(l) and item.IsOnLayer(l) for l in (pcbnew.F_Cu, pcbnew.B_Cu))
                   for p in pads)

    within = (lambda p: inside(mm(p))) if inside else (lambda p: False)
    plan = []
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            if within(t.GetPosition()) or on_pad(t.GetPosition(), t):
                plan.append((t, None, move(mm(t.GetPosition()))))
            continue
        s, e = t.GetStart(), t.GetEnd()
        ns = move(mm(s)) if within(s) or on_pad(s, t) else None
        ne = move(mm(e)) if within(e) or on_pad(e, t) else None
        if ns or ne:
            plan.append((t, ns, ne))
    for f in footprints:
        f.SetPosition(V(move(mm(f.GetPosition()))))
        if turn:
            f.SetOrientationDegrees(f.GetOrientationDegrees() + turn)
    for t, ns, ne in plan:
        if ns is None and t.GetClass() == "PCB_VIA":
            t.SetPosition(V(ne))
            continue
        if ns:
            t.SetStart(V(ns))
        if ne:
            t.SetEnd(V(ne))
    return len(plan)


def shift(dx, dy):
    return lambda p: (p[0] + dx, p[1] + dy)
