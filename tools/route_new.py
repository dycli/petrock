"""Hand-routed copper for the trackpoint edit.

Right-half coordinates are in the upstream frame; RIGHT_DX is added here.
"""
import os
import sys

import pcbnew

from thumb_trackpoint import RIGHT_DX

MM = pcbnew.FromMM
SIGNAL, POWER = 0.25, 0.5

# Each route: net, width, and a list of (x, y, layer) points. A layer change
# between consecutive points drops a via at the first point of the new layer.
F, B = pcbnew.F_Cu, pcbnew.B_Cu
R = RIGHT_DX
ROUTES = [
    # Right half: controller 3.3 V straight to the jack's sleeve-side pad.
    ("VDD", POWER, [(R + 152.02, 67.51, F), (R + 154.6, 68.58, F)]),
    # Trackpoint PS/2 data (GP2): down beside the controller, under col5_r on
    # the back, then down the module's inner side to pin 5.
    ("SDA_r", SIGNAL, [(R + 169.82, 71.12, F), (R + 167.6, 73.34, F), (R + 167.6, 86.4, F), (R + 167.6, 86.4, B),
                       (R + 167.6, 89.1, B), (R + 167.6, 89.1, F), (R + 167.6, 97.0, F), (R + 166.0, 98.6, F),
                       (R + 166.0, 113.1, F), (R + 168.32, 115.41, F)]),
    # Trackpoint PS/2 clock (GP3): parallel lane, then round the outside of pin 5 to pin 6.
    ("SCL_r", SIGNAL, [(R + 169.82, 73.66, F), (R + 168.4, 75.08, F), (R + 168.4, 85.6, F), (R + 168.4, 85.6, B),
                       (R + 168.4, 89.9, B), (R + 168.4, 89.9, F), (R + 168.4, 95.0, F), (R + 171.3, 97.9, F),
                       (R + 171.3, 114.6, F), (R + 169.59, 117.61, F)]),
    # Trackpoint 3.3 V: from the old OLED feed's via, under col5_r, to pin 21.
    ("VDD", POWER, [(R + 163.54, 86.34, B), (R + 163.54, 90.5, B), (R + 163.54, 90.5, F), (R + 163.54, 100.0, F),
                    (R + 157.0, 106.5, F), (R + 157.0, 113.5, F), (R + 153.87, 120.82, F)]),
    # Left half: controller data (pin 2) to the jack's tip pad.
    ("data", SIGNAL, [(144.71, 63.5, F), (148.2, 63.5, F), (151.19, 60.51, F), (151.49, 60.51, F)]),
    # Left half: OLED header VCC across to the new strip, up to the jack. Ground
    # is poured on the back only, so this stays on the front except for a short
    # hop under row3.
    ("VCC", POWER, [(138.43, 93.97, F), (138.43, 96.5, F), (141.4, 96.5, F), (141.4, 96.5, B),
                    (143.4, 96.5, B), (143.4, 96.5, F), (149.6, 96.5, F), (149.6, 71.0, F),
                    (151.49, 67.51, F)]),
]

# Dead-end copper left behind by the removed OLED header (right half).
STUBS = [("GNDA", (R + 166.08, 93.97), (R + 163.22, 96.83)), ("GNDA", (R + 163.22, 96.83), (R + 159.06, 96.83))]


def V(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    r = lambda v: (round(pcbnew.ToMM(v.x), 2), round(pcbnew.ToMM(v.y), 2))
    for net, a, b in STUBS:
        hits = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() == net
                and {r(t.GetStart()), r(t.GetEnd())} == {(round(a[0], 2), a[1]), (round(b[0], 2), b[1])}]
        if len(hits) != 1:
            raise LookupError((net, a, b, len(hits)))
        board.Remove(hits[0])

    for net, width, pts in ROUTES:
        n = board.FindNet(net)
        for (x0, y0, l0), (x1, y1, l1) in zip(pts, pts[1:]):
            if l0 != l1:
                via = pcbnew.PCB_VIA(board)
                via.SetPosition(V(x1, y1))
                via.SetWidth(MM(0.6))
                via.SetDrill(MM(0.4))
                via.SetLayerPair(F, B)
                via.SetNet(n)
                board.Add(via)
                continue
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(V(x0, y0))
            t.SetEnd(V(x1, y1))
            t.SetLayer(l0)
            t.SetWidth(MM(width))
            t.SetNet(n)
            board.Add(t)
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
