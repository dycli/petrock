"""Generate KiCad footprints for the Sprintek SK8707-01 (detached) sensor and driver.

Dimensions from Sprintek DS0048 v1.04 (ref/SK8707-01.pdf), page 6. Both are
drawn in the part's own top view as it sits on the host: the sensor with its
pad edge down and the stem at the origin; the driver with its host pins down and
its origin at the board centre.

The detached driver's sensor-side edge is not dimensioned (about 12 mm above
the host-pin edge, from the integrated drawing and holykeebs' photos), so its
sensor pads run 2.5 mm deep to cover +-0.5 mm of that uncertainty.
"""
import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent / "lib" / "sk8707.pretty"


def rect(layer, x0, y0, x1, y1, w=0.1):
    return f'\t(fp_rect (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f}) (stroke (width {w}) (type solid)) (fill none) (layer "{layer}"))\n'


def text(kind, value, y, layer, hide=False):
    h = " hide" if hide else ""
    return (f'\t(property "{kind}" "{value}" (at 0 {y:.2f} 0) (layer "{layer}"){h}\n'
            f'\t\t(effects (font (size 1 1) (thickness 0.15))))\n')


def smd(num, x, y, w, h, shape="rect"):
    return (f'\t(pad "{num}" smd {shape} (at {x:.3f} {y:.3f}) (size {w:.3f} {h:.3f}) '
            f'(layers "F.Cu" "F.Paste" "F.Mask"))\n')


def footprint(name, descr, body):
    return (f'(footprint "{name}"\n\t(version 20241229)\n\t(generator "make_footprints")\n'
            f'\t(layer "F.Cu")\n\t(descr "{descr}")\n\t(attr smd)\n{body})\n')


SENSOR_PADS = [(-3.75, 1.6), (-1.25, 1.6), (1.25, 2.0), (3.75, 2.0)]  # x, width


def sensor():
    edge, far, half = 10.84, -7.45, 6.6
    b = text("Reference", "TP?", far - 1.2, "F.SilkS") + text("Value", "SK8707-01 sensor", far - 2.4, "F.Fab")
    b += rect("F.Fab", -half, far, half, edge)
    b += rect("F.CrtYd", -half - 0.25, far - 0.25, half + 0.25, edge + 1.0, 0.05)
    b += rect("F.SilkS", -half - 0.15, far - 0.15, half + 0.15, edge - 3.6, 0.12)
    b += f'\t(fp_circle (center 0 0) (end 1.2 0) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))\n'
    for i, (x, w) in enumerate(SENSOR_PADS, 1):
        b += smd(f"S{i}", x, edge - 0.2, w, 2.0)
    for x in (-half + 0.1, half - 0.1):          # corner castellations, mechanical
        b += smd("MP", x, edge - 1.5, 1.6, 3.2)
    for x in (-4.75, 4.75):                        # pads under the four plated holes
        for y in (-4.75, 4.75):
            b += f'\t(pad "MH" smd circle (at {x} {y}) (size 2.8 2.8) (layers "F.Cu" "F.Mask"))\n'
    return footprint("SK8707-01_sensor", "Sprintek SK8707-01 detached sensor, castellated, stem at origin", b)


def driver():
    w, h = 23.0, 12.0
    top, bot = -h / 2, h / 2
    b = text("Reference", "TP?", top - 2.0, "F.SilkS") + text("Value", "SK8707-01 driver", 0, "F.Fab")
    b += rect("F.Fab", -w / 2, top, w / 2, bot)
    b += rect("F.CrtYd", -w / 2 - 0.25, top - 1.35, w / 2 + 0.25, bot + 1.05, 0.05)
    b += rect("F.SilkS", -w / 2 + 0.6, top + 1.5, w / 2 - 0.6, bot - 1.4, 0.12)
    for i in range(8):                              # host castellations, pin 1 = GND
        b += smd(str(i + 1), -w / 2 + 3.08 + 1.8 * i, bot - 0.2, 1.0, 2.0)
    for i, (x, pw) in enumerate(SENSOR_PADS, 1):    # sensor link, same x as the sensor's pads
        b += smd(f"S{i}", x, top + 0.15, pw, 2.5)
    for x in (-6.5, 6.5):
        b += smd("MP", x, top + 0.15, 1.6, 2.5)
    return footprint("SK8707-01_driver", "Sprintek SK8707-01 detached driver, castellated; pins 1 GND 2 DATA 3 CLK 4 RST 5 VCC 6 L 7 M 8 R", b)


OUT.mkdir(parents=True, exist_ok=True)
(OUT / "SK8707-01_sensor.kicad_mod").write_text(sensor())
(OUT / "SK8707-01_driver.kicad_mod").write_text(driver())
