"""Right-hand switch plate: replace the inner thumb switch opening with a cutout
for the trackpoint module. The upstream plate (one file, flipped for the left
half) stays as is for the left side."""
import os
import sys

import pcbnew

import thumb_trackpoint as tt

MM = pcbnew.FromMM
PLATE_DX = -4.0      # upstream plate frame = upstream PCB right-half frame + PLATE_DX
CLEARANCE = 0.5      # gap between module and plate on every side
SLIVER = 1.0


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    sw = [f for f in board.GetFootprints() if f.GetReference() == "SW21"]
    assert len(sw) == 1
    board.Remove(sw[0])

    ox, oy = tt.module_origin()
    ox += PLATE_DX - tt.RIGHT_DX
    x0, y0, x1, y1 = tt.MODULE_BOX
    m = CLEARANCE
    cut = pcbnew.SHAPE_POLY_SET()
    cut.NewOutline()
    for x, y in ((x0 - m, y0 - m), (x1 + m, y0 - m), (x1 + m, y1 + m), (x0 - m, y1 + m)):
        dx, dy = tt.rot(x, y, tt.MODULE_ROT)
        cut.Append(MM(ox + dx), MM(oy + dy))

    # Outer contour only; switch openings belong to their footprints.
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline, False)
    plate = pcbnew.SHAPE_POLY_SET()
    plate.AddOutline(outline.Outline(0))
    plate.BooleanSubtract(cut)
    # Opening by SLIVER mm drops the strips the notch leaves along the edges and
    # rounds the notch's corners for the router bit.
    plate.Deflate(MM(SLIVER), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
    plate.Inflate(MM(SLIVER), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
    if plate.OutlineCount() != 1:
        raise SystemExit(f"plate split into {plate.OutlineCount()} pieces")

    for d in [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]:
        board.Remove(d)
    shape = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_POLY)
    shape.SetPolyShape(plate)
    shape.SetLayer(pcbnew.Edge_Cuts)
    shape.SetWidth(MM(0.05))
    shape.SetFilled(False)
    board.Add(shape)
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
