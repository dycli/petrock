"""Put the main block's keys on an exact column stagger (upstream is off by up to
0.02 mm here and there): rows exactly ROW_PITCH apart, each column's top key a
whole number of STEPs below the middle finger's. Each key moves with its diode
and their copper (tools/parts.py drag). Runs on the upstream board,
before tools/widen.py.

Then the pinky becomes one column of four: the inner pinky column moves up
(PINKY: its top key one STEP below the ring column's), dragging its column
copper along; the outer pinky column's top key becomes its fourth key and the
outer bottom key becomes a fourth key under the ring column. Each of those two
joins the column it lands in, on the thumb row (row3), which has those columns
free; the outer home key goes. So does the upper of the two standoffs between
the pinky columns. The moved references go to $MOVED_OUT.

usage: stagger.py IN OUT
"""
import os
import sys

import pcbnew

import parts
import thumbs

MM = pcbnew.FromMM
MIDDLE_TOP = 61.19          # upstream middle-finger column's top key
# 18 x tan(7.5 deg) = 2.3698, rounded: the top edge's 7.5-degree slopes then run
# parallel to the columns' top corners to within 0.0002 mm (tools/top_edge.py).
STEP = 2.37
UPSTREAM_PINKY = 8.92       # pinky columns' top keys below the middle column's, upstream
PINKY = 2 * STEP            # here
PINKY_X = 54.0              # left half, upstream frame: the pinky columns lie outside this
INNER_PINKY_X = 44.5
INNER_INDEX_X = 116.5       # the inner index column, beside the controller
RING_X = 62.5
PINKY_STANDOFF_Y = 90.0     # upstream: the lower pinky standoff is below this, the upper above
# Left half, upstream frame: column x and its top key's drop below the middle
# column (the inner pinky column's before the drop).
COLUMNS = {44.5: PINKY, 62.5: STEP, 80.5: 0.0, 98.5: STEP, 116.5: 2 * STEP}
# The outer pinky column, top to bottom.
OUTER_COLUMN = {"left": ("SW1", "SW7", "SW13"), "right": ("SW22", "SW28", "SW34")}
OUTER_X = 26.5
# The standoffs between the two pinky columns go: with one column there is no
# room for them.
MIRROR_X = 299.31           # tools/widen.py
ROWS = 3


def targets():
    """{(x, row): y} for every main-block key, both halves (upstream frame)."""
    out = {}
    for x, drop in COLUMNS.items():
        for r in range(ROWS):
            y = MIDDLE_TOP + drop + r * thumbs.ROW_PITCH
            out[(x, r)] = y
            out[(round(MIRROR_X - x, 4), r)] = y
    return out


def set_net(board, part, number, name):
    """Every pad numbered so (a switch has a through-hole and a socket pad 1)."""
    for pad in part.Pads():
        if pad.GetNumber() == number:
            pad.SetNet(board.FindNet(name))


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    fps = list(board.GetFootprints())
    keys = [f for f in fps if "SW_choc" in f.GetFPIDAsString()]
    by_ref = {f.GetReference(): f for f in fps}
    want = targets()
    moved = []
    for col in sorted({x for x, _ in want}):
        column = sorted((k for k in keys if abs(pcbnew.ToMM(k.GetPosition().x) - col) < 0.01),
                        key=lambda k: k.GetPosition().y)
        if col in (INNER_PINKY_X, round(MIRROR_X - INNER_PINKY_X, 4)):
            # The whole pinky column moves, its copper with it.
            dy = want[(col, 0)] - pcbnew.ToMM(column[0].GetPosition().y)
            group = [part for k in column[:ROWS] for part in (k, *parts.key_parts(board, k))]
            x0, x1 = (OUTER_X + 9, PINKY_X) if col < MIRROR_X / 2 else (MIRROR_X - PINKY_X, MIRROR_X - OUTER_X - 9)
            # Only copper among the column's keys: the top wiring that turns down
            # into the column stays, and its drop into the column shortens.
            y0 = pcbnew.ToMM(column[0].GetPosition().y) - thumbs.ROW_PITCH / 2
            parts.drag(board, group, parts.shift(0, dy), inside=lambda p: x0 < p[0] < x1 and p[1] > y0)
            moved += [part.GetReference() for part in group]
            continue
        for r, k in enumerate(column[:ROWS]):
            if pcbnew.ToMM(k.GetPosition().y) > 106:      # not a thumb key
                continue
            dy = want[(col, r)] - pcbnew.ToMM(k.GetPosition().y)
            if abs(dy) < 1e-6:
                continue
            group = [k, *parts.key_parts(board, k)]
            parts.drag(board, group, parts.shift(0, dy))
            moved += [part.GetReference() for part in group]
    doomed = []
    for half, (top, home, bottom) in OUTER_COLUMN.items():
        side = (lambda x: x) if half == "left" else (lambda x: MIRROR_X - x)
        sfx = "" if half == "left" else "_r"
        # The top key becomes the pinky column's fourth, the bottom one the ring
        # column's; each on its new column and the thumb row.
        for ref, x, col in ((top, INNER_PINKY_X, "col1"), (bottom, RING_X, "col2")):
            k = by_ref[ref]
            y = MIDDLE_TOP + COLUMNS[x] + ROWS * thumbs.ROW_PITCH
            d = pcbnew.VECTOR2I(MM(side(x) - pcbnew.ToMM(k.GetPosition().x)), MM(y - pcbnew.ToMM(k.GetPosition().y)))
            (diode,) = parts.key_parts(board, k)
            for part in (k, diode):
                part.Move(d)
                moved.append(part.GetReference())
            set_net(board, k, "1", col + sfx)
            set_net(board, diode, "1", "row3" + sfx)
        doomed += parts.remove_key(board, by_ref[home])
    # Of the two standoffs between the pinky columns, the upper one goes; the lower
    # one moves later (tools/standoffs.py).
    doomed += [f for f in fps if f.GetFPIDAsString() == "holykeebs:M2_SPACER"
               and not PINKY_X <= pcbnew.ToMM(f.GetPosition().x) <= MIRROR_X - PINKY_X
               and pcbnew.ToMM(f.GetPosition().y) < PINKY_STANDOFF_Y]
    for item in doomed:           # last: removing leaves other handles stale
        board.Remove(item)
    if os.environ.get("MOVED_OUT"):
        with open(os.environ["MOVED_OUT"], "a") as out:
            out.writelines(r + "\n" for r in moved if r)
    board.Save(dst)


def main_keys():
    """Left half, upstream frame: (centre, orientation) of every main-block key:
    four in the pinky and ring columns, three in each other column."""
    return [((x, MIDDLE_TOP + drop + r * thumbs.ROW_PITCH), 0.0)
            for x, drop in COLUMNS.items() for r in range(ROWS + (x in (INNER_PINKY_X, RING_X)))]


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
