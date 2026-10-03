"""Simple VRML stand-in models for the demo renders: a Choc keycap, the
trackpoint nub, and the SK8707 sensor and driver boards."""
import math
import os
import sys

OUT = sys.argv[1]


def box(path, w, d, h, rgb, z0=0.0):
    # VRML units here are 0.1 inch (KiCad's WRL convention); 1 mm = 1/2.54.
    s = 1 / 2.54
    c = " ".join(f"{v:.3f}" for v in rgb)
    with open(path, "w") as f:
        f.write(f"""#VRML V2.0 utf8
Transform {{ translation 0 0 {(z0 + h / 2) * s:.4f} children [
  Shape {{ appearance Appearance {{ material Material {{ diffuseColor {c} specularColor 0.2 0.2 0.2 shininess 0.3 }} }}
          geometry Box {{ size {w * s:.4f} {d * s:.4f} {h * s:.4f} }} }} ] }}
""")


def cylinder(path, r, h, rgb, z0=0.0, n=32):
    """A prism as an IndexedFaceSet (KiCad's VRML reader skips Cylinder nodes)."""
    s = 1 / 2.54
    c = " ".join(f"{v:.3f}" for v in rgb)
    pts = [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    coords = [f"{x * s:.4f} {y * s:.4f} {z0 * s:.4f}" for x, y in pts] + \
             [f"{x * s:.4f} {y * s:.4f} {(z0 + h) * s:.4f}" for x, y in pts]
    faces = [" ".join(str(k) for k in range(n - 1, -1, -1)) + " -1",          # bottom
             " ".join(str(n + k) for k in range(n)) + " -1"]                 # top
    faces += [f"{k} {(k + 1) % n} {n + (k + 1) % n} {n + k} -1" for k in range(n)]
    with open(path, "w") as f:
        f.write(f"""#VRML V2.0 utf8
Shape {{ appearance Appearance {{ material Material {{ diffuseColor {c} specularColor 0.1 0.1 0.1 }} }}
  geometry IndexedFaceSet {{ coord Coordinate {{ point [ {", ".join(coords)} ] }}
    coordIndex [ {" ".join(faces)} ] }} }}
""")


os.makedirs(OUT, exist_ok=True)
box(f"{OUT}/keycap.wrl", 17.5, 16.5, 2.4, (0.93, 0.93, 0.91), z0=8.2)     # sits on the switch stem
box(f"{OUT}/sensor.wrl", 13.2, 18.29, 0.8, (0.12, 0.25, 0.65))           # blue Sprintek sensor board
cylinder(f"{OUT}/nub.wrl", 3.5, 2.6, (0.80, 0.08, 0.08), z0=0.8 + 2.4 - 0.6)  # red cap over the stem
box(f"{OUT}/driver.wrl", 23.0, 14.5, 1.0, (0.12, 0.25, 0.65))            # blue driver board
