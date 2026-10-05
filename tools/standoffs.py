"""Move the two standoffs that sat between the two pinky columns: the lower one
to the nearest clear spot to TARGET, under the ring column's fourth key, and the
upper one to the nearest clear spot to TOP_TARGET, up in the outer top corner,
so both ends of the board stay supported (five per half, as stock); and move any standoff
the logo (tools/logo.py) would cover to the nearest clear spot outside it. Each
move is mirrored on the two halves.

usage: standoffs.py IN OUT
"""
import math
import os
import sys

import pcbnew

import logo
import stagger
import widen

MM = pcbnew.FromMM
TARGET = (65.5, 126.0)      # left half, upstream frame: under the ring column's fourth key
TOP_TARGET = (53.5, 73.0)   # where the pinky and ring columns meet, between their top two rows
GAP = 0.5                   # its pad to any other pad
EDGE = 3.0                  # its centre inside the board edge
REACH, STEP = 12.0, 0.25
LOGO_CLEAR = 0.5            # its pad to the logo


def body(f):
    c = f.GetCourtyard(pcbnew.B_CrtYd)
    if c.OutlineCount():
        return c
    bb = f.GetBoundingBox(False)
    p = pcbnew.SHAPE_POLY_SET()
    p.NewOutline()
    for x, y in ((bb.GetLeft(), bb.GetTop()), (bb.GetRight(), bb.GetTop()), (bb.GetRight(), bb.GetBottom()), (bb.GetLeft(), bb.GetBottom())):
        p.Append(x, y)
    return p


def clear(board, f, outline):
    (pad,) = list(f.Pads())
    hole = pad.GetEffectiveShape(pcbnew.B_Cu)
    for o in board.GetFootprints():
        if o.m_Uuid == f.m_Uuid:
            continue
        for p in o.Pads():
            for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                if (p.IsOnLayer(layer) or p.GetDrillSizeX() > 0) and p.GetEffectiveShape(layer).Collide(hole, MM(GAP)):
                    return False
        if o.IsFlipped() and body(o).Collide(pad.GetPosition(), pad.GetBoundingBox().GetWidth() // 2):
            return False
    return outline.Contains(f.GetPosition())


def off_logo(f, mark):
    """f's pad is LOGO_CLEAR off the logo (both halves' copies are given)."""
    (pad,) = list(f.Pads())
    c = pad.GetPosition()
    r = pad.GetBoundingBox().GetWidth() // 2 + MM(LOGO_CLEAR)
    return not any(m.Collide(c, r) for m in mark)


def move(board, pair, target, outline, mark):
    left, right = pair
    mirror = lambda v: widen.MIRROR_X - v + widen.RIGHT_DX
    n = int(REACH / STEP)
    for _, i, j in sorted((math.hypot(i, j), i, j) for i in range(-n, n + 1) for j in range(-n, n + 1) if math.hypot(i, j) * STEP <= REACH):
        px, py = target[0] + i * STEP, target[1] + j * STEP
        left.SetPosition(pcbnew.VECTOR2I(MM(px), MM(py)))
        right.SetPosition(pcbnew.VECTOR2I(MM(mirror(px)), MM(py)))
        if all(clear(board, f, outline) and off_logo(f, mark) for f in (left, right)):
            return px, py
    raise SystemExit(f"no room for a standoff near {target}")


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline, False)
    outline.Deflate(MM(EDGE), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
    mark = []
    for pts in (logo.placed(), [(widen.MIRROR_X - x + widen.RIGHT_DX, y) for x, y in logo.placed()]):
        poly = pcbnew.SHAPE_POLY_SET()
        poly.NewOutline()
        for x, y in pts:
            poly.Append(MM(x), MM(y))
        mark.append(poly)
    spacers = [f for f in board.GetFootprints() if f.GetFPIDAsString() == "holykeebs:M2_SPACER"]
    x = lambda f: pcbnew.ToMM(f.GetPosition().x)
    y = lambda f: pcbnew.ToMM(f.GetPosition().y)
    mirror = lambda v: widen.MIRROR_X - v + widen.RIGHT_DX
    twin = lambda f: min(spacers, key=lambda o: math.hypot(x(o) - mirror(x(f)), y(o) - y(f)))
    # The two standoffs that sat between the pinky columns: the lower one under the
    # ring column's fourth key, the upper one up in the outer top corner.
    upper, lower = sorted(sorted(spacers, key=x)[:2], key=y)
    for f, target, name in ((lower, TARGET, "pinky-end"), (upper, TOP_TARGET, "outer-top")):
        px, py = move(board, (f, twin(f)), target, outline, mark)
        print(f"{name} standoff: {px:.2f}, {py:.2f}")
    moved = {upper.m_Uuid.AsString(), lower.m_Uuid.AsString()}
    for f in [f for f in spacers if x(f) < widen.SPLIT_X and f.m_Uuid.AsString() not in moved]:
        if not off_logo(f, mark):
            was = (x(f), y(f))
            px, py = move(board, (f, twin(f)), was, outline, mark)
            print(f"standoff under the logo: {was[0]:.2f}, {was[1]:.2f} -> {px:.2f}, {py:.2f}")
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
