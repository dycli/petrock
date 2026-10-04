"""Simple VRML stand-in models for the demo renders: the trackpoint nub, the
SK8707 sensor and driver boards (coloured from Sprintek's parts,
ref/sk8707-01-004-top.png), and the RP2040 Pro Micro controller (the stock
models come in one flat colour)."""
import math
import os
import sys

OUT = sys.argv[1]


NAVY = (0.03, 0.12, 0.26)       # the boards' dark navy solder mask
OLIVE = (0.27, 0.27, 0.17)      # the sensor's disc round the stem
GOLD = (0.82, 0.73, 0.45)       # pads and the mounting holes' rings
STEM = (0.86, 0.85, 0.78)       # the white stem
BLACK_MASK = (0.06, 0.06, 0.06) # an RP2040 Pro Micro's black board
STEEL = (0.75, 0.75, 0.77)      # the USB-C shell
HEADER = (0.05, 0.05, 0.05)     # header plastic
S = 1 / 2.54                    # VRML units here are 0.1 inch (KiCad's WRL convention)


def box(path, w, d, h, rgb, z0=0.0):
    s = S
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


def material(rgb, spec=0.2):
    c = " ".join(f"{v:.3f}" for v in rgb)
    return f"appearance Appearance {{ material Material {{ diffuseColor {c} specularColor {spec} {spec} {spec} shininess 0.3 }} }}"


def box_shape(cx, cy, w, d, z0, h, rgb):
    """A box centred at (cx, cy) in the part's footprint frame (y down)."""
    return (f"Transform {{ translation {cx * S:.4f} {-cy * S:.4f} {(z0 + h / 2) * S:.4f} children [\n"
            f"  Shape {{ {material(rgb)} geometry Box {{ size {w * S:.4f} {d * S:.4f} {h * S:.4f} }} }} ] }}\n")


def disc_shape(cx, cy, r, z0, h, rgb, n=40):
    """A prism (KiCad's VRML reader skips Cylinder nodes), footprint frame."""
    pts = [(cx + r * math.cos(2 * math.pi * k / n), -cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    coords = [f"{x * S:.4f} {y * S:.4f} {z0 * S:.4f}" for x, y in pts] + \
             [f"{x * S:.4f} {y * S:.4f} {(z0 + h) * S:.4f}" for x, y in pts]
    faces = [" ".join(str(k) for k in range(n - 1, -1, -1)) + " -1", " ".join(str(n + k) for k in range(n)) + " -1"]
    faces += [f"{k} {(k + 1) % n} {n + (k + 1) % n} {n + k} -1" for k in range(n)]
    return (f"Shape {{ {material(rgb, 0.1)}\n  geometry IndexedFaceSet {{ coord Coordinate {{ point [ {', '.join(coords)} ] }}\n"
            f"    coordIndex [ {' '.join(faces)} ] }} }}\n")


def sensor(path):
    """The SK8707-01 sensor board as it sits pad edge down in its footprint
    (tools/make_footprints.py): stem at the origin, the board 7.45 mm above it
    and 10.84 mm below, mounting holes at +-4.75 mm, the edge pads along the
    bottom."""
    t, top = 0.8, 0.8
    parts = [box_shape(0, (10.84 - 7.45) / 2, 13.2, 18.29, 0, t, NAVY),
             disc_shape(0, 0, 5.05, top, 0.02, OLIVE)]
    for x in (-4.75, 4.75):
        for y in (-4.75, 4.75):
            parts += [disc_shape(x, y, 1.4, top, 0.03, GOLD), disc_shape(x, y, 0.8, top, 0.04, (0.02, 0.02, 0.02))]
    for x, w in ((-3.75, 1.6), (-1.25, 1.6), (1.25, 2.0), (3.75, 2.0)):      # sensor links
        parts.append(box_shape(x, 10.64, w, 2.0, top, 0.03, GOLD))
    for x in (-6.5, 6.5):                                                  # corner tabs
        parts.append(box_shape(x, 9.34, 1.6, 3.2, top, 0.03, GOLD))
    parts.append(box_shape(0, 0, 2.4, 2.4, top, 2.0, STEM))                # the stem, under the cap
    with open(path, "w") as f:
        f.write("#VRML V2.0 utf8\n" + "".join(parts))


def controller(path):
    """An RP2040 Pro Micro as a Corne mounts it, face down on 2.5 mm sockets, in
    its footprint's frame (holykeebs ProMicro): seen from above, the board's back
    (black, gold pin rings), the USB-C shell sticking out at the top end. Pins
    1-12 at x = +7.61, 13-24 at -7.61, 2.54 mm apart from y = -14.48."""
    z0, t = 2.5, 1.6
    parts = [box_shape(0, -1.04, 17.9, 31.7, z0, t, BLACK_MASK),          # the board
             box_shape(0, -16.9, 8.9, 3.2, z0 - 3.2 + t, 3.2, STEEL)]    # USB-C, on the face-down side, at the top end
    for x in (-7.61, 7.61):
        parts.append(box_shape(x, -0.51, 2.5, 30.5, 0, z0, HEADER))      # the socket strips
        for i in range(12):
            y = -14.48 + 2.54 * i
            parts += [disc_shape(x, y, 0.85, z0 + t, 0.03, GOLD), disc_shape(x, y, 0.5, z0 + t, 0.04, (0.02, 0.02, 0.02))]
    with open(path, "w") as f:
        f.write("#VRML V2.0 utf8\n" + "".join(parts))


os.makedirs(OUT, exist_ok=True)
sensor(f"{OUT}/sensor.wrl")
controller(f"{OUT}/controller.wrl")
cylinder(f"{OUT}/nub.wrl", 3.5, 2.6, (0.80, 0.08, 0.08), z0=0.8 + 2.4 - 0.6)  # red cap over the stem
box(f"{OUT}/driver.wrl", 23.0, 14.5, 1.0, NAVY)                          # driver board
