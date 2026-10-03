"""Bottom plate for the widened PCB: the board outline plus M2 holes at the
standoff positions (the same standoffs the switch plate uses)."""
import os
import sys

import pcbnew

MM = pcbnew.FromMM
HOLE = 2.2


def main(src, dst):
    pcb = pcbnew.LoadBoard(src)
    plate = pcbnew.CreateEmptyBoard()
    for d in pcb.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            plate.Add(d.Duplicate())
    for f in pcb.GetFootprints():
        if f.GetFPIDAsString() != "holykeebs:M2_SPACER":
            continue
        hole = pcbnew.FOOTPRINT(plate)
        hole.SetReference(f"H{len(list(plate.GetFootprints())) + 1}")
        hole.Reference().SetVisible(False)
        hole.Value().SetVisible(False)
        pad = pcbnew.PAD(hole)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
        pad.SetShape(pcbnew.F_Cu, pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetSize(pcbnew.F_Cu, pcbnew.VECTOR2I(MM(HOLE), MM(HOLE)))
        pad.SetDrillSize(pcbnew.VECTOR2I(MM(HOLE), MM(HOLE)))
        pad.SetLayerSet(pad.UnplatedHoleMask())
        hole.Add(pad)
        hole.SetPosition(f.GetPosition())
        plate.Add(hole)
    plate.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
