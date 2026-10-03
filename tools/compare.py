"""Before/after drawing: upstream outline and keys (grey, dashed) under v2's
outline and keys. The upstream right half is shifted like tools/widen.py does."""
import math
import os
import sys

import pcbnew

RIGHT_DX = 12.4
CAP_W, CAP_H = 17.5, 16.5


def outline_and_keys(path, shift_right):
    b = pcbnew.LoadBoard(path)
    o = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(o, False)
    polys = []
    for i in range(o.OutlineCount()):
        ol = o.Outline(i)
        pts = [(pcbnew.ToMM(ol.CPoint(k).x), pcbnew.ToMM(ol.CPoint(k).y)) for k in range(ol.PointCount())]
        if shift_right and min(p[0] for p in pts) > 149.6:
            pts = [(x + RIGHT_DX, y) for x, y in pts]
        polys.append(pts)
    keys, nub = [], None
    for f in b.GetFootprints():
        x, y = pcbnew.ToMM(f.GetPosition().x), pcbnew.ToMM(f.GetPosition().y)
        if shift_right and x > 149.6:
            x += RIGHT_DX
        if "SW_choc" in f.GetFPIDAsString():
            keys.append((x, y, f.GetOrientationDegrees()))
        elif f.GetReference() == "TP1":
            nub = (x, y)
    return polys, keys, nub


def svg(before, after, out):
    allx = [p[0] for poly in after[0] + before[0] for p in poly]
    ally = [p[1] for poly in after[0] + before[0] for p in poly]
    x0, y0, x1, y1 = min(allx) - 8, min(ally) - 22, max(allx) + 8, max(ally) + 8
    s = 8  # px per mm
    w, h = (x1 - x0) * s, (y1 - y0) * s
    T = lambda x, y: ((x - x0) * s, (y - y0) * s)
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" font-family="sans-serif">',
             f'<rect width="{w:.0f}" height="{h:.0f}" fill="white"/>']

    def poly(pts, style):
        lines.append('<polygon points="' + " ".join("%.1f,%.1f" % T(*p) for p in pts) + f'" {style}/>')

    def keys(ks, style):
        for x, y, deg in ks:
            cx, cy = T(x, y)
            lines.append(f'<rect x="{cx - CAP_W * s / 2:.1f}" y="{cy - CAP_H * s / 2:.1f}" width="{CAP_W * s:.1f}" '
                         f'height="{CAP_H * s:.1f}" rx="{s:.1f}" transform="rotate({-deg:.1f} {cx:.1f} {cy:.1f})" {style}/>')
    for p in after[0]:
        poly(p, 'fill="#20201e" stroke="none"')
    keys(after[1], 'fill="#f2f2ee" stroke="#555" stroke-width="1.5"')
    if after[2]:
        cx, cy = T(*after[2])
        lines.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{3.5 * s:.1f}" fill="#d22"/>')
    for p in before[0]:
        poly(p, 'fill="none" stroke="#e8a33a" stroke-width="3" stroke-dasharray="14,8"')
    keys(before[1], 'fill="none" stroke="#e8a33a" stroke-width="2" stroke-dasharray="8,6"')
    lines.append(f'<text x="{4 * s}" y="{9 * s}" font-size="{5 * s}">Corne Choc: holykeebs original (orange, dashed) vs v2</text>')
    lines.append(f'<text x="{4 * s}" y="{15 * s}" font-size="{3.2 * s}" fill="#555">'
                 'Wider inner edge with jacks at the top, split inner thumb keys, peaked top edge, trackpoint (red) at the right outer thumb.</text>')
    lines.append("</svg>")
    open(out, "w").write("\n".join(lines))


if __name__ == "__main__":
    before = outline_and_keys(sys.argv[1], True)
    after = outline_and_keys(sys.argv[2], False)
    svg(before, after, sys.argv[3])
    sys.stdout.flush()
    os._exit(0)
