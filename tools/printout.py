"""1:1 printable layout: board outline, keycaps, trackpoint nub, controller and
jack, both halves stacked on one portrait letter page inside normal printer
margins, with scale bars to check the print.

usage: printout.py BOARD OUT.svg
       Print with scaling off (lp -o print-scaling=none) for true size.
"""
import math
import os
import sys

import pcbnew

PAGE_W, PAGE_H = 215.9, 279.4        # US letter, portrait, mm
CAP_W, CAP_H, CAP_R = 17.5, 16.5, 1.0  # choc-spacing keycap
NUB_D = 7.0


def mm(v):
    return pcbnew.ToMM(v.x), pcbnew.ToMM(v.y)


def rect_points(cx, cy, w, h, deg):
    a = math.radians(deg)
    pts = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x, y = sx * w / 2, sy * h / 2
        pts.append((cx + x * math.cos(a) + y * math.sin(a), cy - x * math.sin(a) + y * math.cos(a)))
    return pts


def half_svg(pts, parts, ox, oy):
    """SVG elements for one half, translated by (ox, oy)."""
    xs = [p[0] for p in pts]
    x0, x1 = min(xs), max(xs)
    T = lambda p: (p[0] + ox, p[1] + oy)
    out = ['<polygon points="' + " ".join(f"{T(p)[0]:.3f},{T(p)[1]:.3f}" for p in pts) +
           '" fill="#f4f4f4" stroke="black" stroke-width="0.3"/>']
    for ref, fpid, (x, y), deg in parts:
        if not (x0 - 1 <= x <= x1 + 1):
            continue
        if "SW_choc" in fpid:
            cx, cy = T((x, y))
            out.append(f'<rect x="{cx - CAP_W / 2:.3f}" y="{cy - CAP_H / 2:.3f}" width="{CAP_W}" height="{CAP_H}" '
                       f'rx="{CAP_R}" fill="white" stroke="#333" stroke-width="0.35" '
                       f'transform="rotate({-deg:.2f} {cx:.3f} {cy:.3f})"/>')
        elif ref == "A1":
            cx, cy = T((x, y))
            out.append(f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{NUB_D / 2}" fill="#d22" stroke="black" stroke-width="0.3"/>')
            out.append(f'<text x="{cx:.2f}" y="{cy + NUB_D / 2 + 4:.2f}" font-size="3" text-anchor="middle">trackpoint</text>')
        elif "ProMicro" in fpid:
            p = [T(q) for q in rect_points(x, y - 1.78, 17.8, 33.0, deg)]
            out.append('<polygon points="' + " ".join(f"{a:.3f},{b:.3f}" for a, b in p) +
                       '" fill="none" stroke="#888" stroke-width="0.3" stroke-dasharray="1.5,1"/>')
            cx, cy = T((x, y))
            out.append(f'<text x="{cx:.2f}" y="{cy:.2f}" font-size="3" fill="#666" text-anchor="middle">controller</text>')
        elif ref in ("J1", "J3"):
            p = [T(q) for q in rect_points(x, y + 6.4, 5.95, 13.3, deg)]
            out.append('<polygon points="' + " ".join(f"{a:.3f},{b:.3f}" for a, b in p) +
                       '" fill="none" stroke="#888" stroke-width="0.3" stroke-dasharray="1.5,1"/>')
    return out


def main(board_path, out_path):
    board = pcbnew.LoadBoard(board_path)
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline, False)
    halves = []
    for i in range(outline.OutlineCount()):
        o = outline.Outline(i)
        halves.append([mm(o.CPoint(k)) for k in range(o.PointCount())])
    halves.sort(key=lambda pts: min(p[0] for p in pts))
    parts = [(f.GetReference(), f.GetFPIDAsString(), mm(f.GetPosition()), f.GetOrientationDegrees())
             for f in board.GetFootprints()]
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}mm" height="{PAGE_H}mm" '
           f'viewBox="0 0 {PAGE_W} {PAGE_H}" font-family="sans-serif">',
           f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="white"/>',
           '<text x="20" y="22" font-size="5">Corne Choc v2.1 — actual size</text>',
           '<text x="20" y="28" font-size="3.2" fill="#555">Print at 100% / "Actual size". Check the 100 mm bar; '
           'keycaps drawn 17.5 x 16.5 mm; red dot = trackpoint nub.</text>']
    top = 40.0
    for name, pts in zip(("left", "right"), halves):
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        ox = (PAGE_W - (max(xs) - min(xs))) / 2 - min(xs)
        oy = top - min(ys)
        svg.append(f'<text x="20" y="{top - 2:.1f}" font-size="3.5">{name} half</text>')
        svg += half_svg(pts, parts, ox, oy)
        top += max(ys) - min(ys) + 14
    bx, by = 20, PAGE_H - 28
    svg.append(f'<line x1="{bx}" y1="{by}" x2="{bx + 100}" y2="{by}" stroke="black" stroke-width="0.5"/>')
    for t in range(0, 101, 10):
        svg.append(f'<line x1="{bx + t}" y1="{by - (2 if t % 50 else 3.5)}" x2="{bx + t}" y2="{by}" stroke="black" stroke-width="0.3"/>')
    svg.append(f'<text x="{bx}" y="{by + 5}" font-size="3.5">100 mm</text>')
    ix = bx + 110
    svg.append(f'<line x1="{ix}" y1="{by}" x2="{ix + 76.2}" y2="{by}" stroke="black" stroke-width="0.5"/>')
    for t in range(4):
        svg.append(f'<line x1="{ix + t * 25.4}" y1="{by - 3}" x2="{ix + t * 25.4}" y2="{by}" stroke="black" stroke-width="0.3"/>')
    svg.append(f'<text x="{ix}" y="{by + 5}" font-size="3.5">3 inches</text>')
    svg.append("</svg>")
    with open(out_path, "w") as f:
        f.write("\n".join(svg))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    os._exit(0)
