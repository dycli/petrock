"""Hand-route the four sensor-to-driver links: from each sensor pad on the front,
a via just inside the sensor's pad edge, then straight down to the matching
driver pad on the back (they share x by construction)."""
import os
import sys

import pcbnew

MM = pcbnew.FromMM
VIA_Y = 108.55
WIDTH = 0.25


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    pads = {}
    for f in board.GetFootprints():
        if f.GetReference() in ("TP1", "TP2"):
            for p in f.Pads():
                if p.GetNumber().startswith("S"):
                    pads[(f.GetReference(), p.GetNumber())] = p
    for i in range(1, 5):
        s, d = pads[("TP1", f"S{i}")], pads[("TP2", f"S{i}")]
        x = s.GetPosition().x
        assert x == d.GetPosition().x, f"S{i} pads not aligned"
        via_at = pcbnew.VECTOR2I(x, MM(VIA_Y))
        for layer, a, b in ((pcbnew.F_Cu, s.GetPosition(), via_at), (pcbnew.B_Cu, via_at, d.GetPosition())):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(a); t.SetEnd(b); t.SetLayer(layer); t.SetWidth(MM(WIDTH)); t.SetNet(s.GetNet())
            board.Add(t)
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(via_at); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.4))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(s.GetNet())
        board.Add(v)
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
