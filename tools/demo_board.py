"""Make a render-only copy of the board: black mask, real 3D models where they
exist (sockets, LEDs, diodes, controller, jacks, reset buttons), switches and
KLP Lame keycaps on top, the trackpoint's sensor, nub and driver.

usage: demo_board.py IN OUT MARBASTLIB_DIR KBD_DIR PACKAGES3D_DIR STANDIN_DIR KLP_DIR [bare] [nooled]
       "bare" leaves out the switches and keycaps, to show the board itself;
       "nooled" leaves out the OLED modules and their headers.
"""
import os
import sys

import pcbnew

MM = pcbnew.FromMM
# KLP Lame (choc stem, choc size) keycaps: thumb caps on the thumb keys, homing
# caps on F and J. KLP_Z puts the cap's top about 10 mm above the PCB.
KLP_Z = 4.33
THUMBS = {"SW19", "SW20", "SW21", "SW43", "SW41", "SW42", "SW44"}
HOMING = {"SW11", "SW32"}


def model(path, z=0.0, rot=(0, 0, 0), offset=(0.0, 0.0)):
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = path
    m.m_Offset = pcbnew.VECTOR3D(offset[0], offset[1], z)
    m.m_Rotation = pcbnew.VECTOR3D(*rot)
    m.m_Scale = pcbnew.VECTOR3D(1, 1, 1)
    m.m_Show = True
    return m


def keycap(ref):
    kind = "Thumb" if ref in THUMBS else "Normal_Homing" if ref in HOMING else "Normal"
    return f"Choc_Stem_Choc_Size_{kind}.step"


def main(src, dst, marbast, kbd, pkg3d, standin, klp, *opts):
    bare = "bare" in opts
    board = pcbnew.LoadBoard(src)
    subst = {
        "${KICAD7_3RD_PARTY}/3dmodels/com_github_ebastler_marbastlib": os.path.join(marbast, "3dmodels"),
        "${KIPRJMOD}/kbd/kicad-packages3D/kbd.3dshapes": os.path.join(kbd, "kicad-packages3D", "kbd.3dshapes"),
        "/Users/foostan/src/github.com/foostan/kbd/kicad-packages3D/kbd.3dshapes": os.path.join(kbd, "kicad-packages3D", "kbd.3dshapes"),
        "${KICAD8_3DMODEL_DIR}": pkg3d,
        "${KIGITHUB3D}": pkg3d,
    }
    keys, tp = [], None
    for f in board.GetFootprints():
        # Models() hands out copies, so rebuild the list with the paths resolved.
        models = list(f.Models())
        f.Models().clear()
        if "nooled" in opts and f.GetReference() in ("J2", "J4"):
            continue
        for m in models:
            for a, b in subst.items():
                if m.m_Filename.startswith(a):
                    m.m_Filename = b + m.m_Filename[len(a):]
            f.Models().push_back(m)
        if "SW_choc" in f.GetFPIDAsString():
            keys.append((f.GetReference(), f.GetPosition(), f.GetOrientationDegrees()))
        elif f.GetReference() == "TP1":
            tp = f
        elif f.GetReference() == "TP2":
            f.Models().push_back(model(os.path.join(standin, "driver.wrl")))
    if tp is not None:
        # The board reaches 10.84 mm from the stem on its pad side and 7.45 mm on
        # the other (tools/make_footprints.py); 3D y points the other way.
        tp.Models().push_back(model(os.path.join(standin, "sensor.wrl"), offset=(0.0, -(10.84 - 7.45) / 2)))
        tp.Models().push_back(model(os.path.join(standin, "nub.wrl")))
    # Switch + keycap on the top side for every key (the key footprints sit on the
    # back, where the hot-swap sockets are).
    choc = os.path.join(kbd, "kicad-packages3D", "kbd.3dshapes", "kailh_choc.step")
    for ref, pos, deg in ([] if bare else keys):
        v = pcbnew.FOOTPRINT(board)
        v.SetPosition(pos)
        v.SetOrientationDegrees(deg)
        v.Models().push_back(model(choc, z=0.0))
        v.Models().push_back(model(os.path.join(klp, keycap(ref)), z=KLP_Z))
        v.Reference().SetVisible(False)
        v.Value().SetVisible(False)
        board.Add(v)
    board.Save(dst)
    colour_stackup(dst)


def colour_stackup(path):
    """Black solder mask and white silkscreen, like holykeebs' boards. (The
    stackup isn't exposed to Python, so this edits the saved file.)"""
    import re
    text = open(path).read()
    for layer, colour in (("F.Mask", "Black"), ("B.Mask", "Black"), ("F.SilkS", "White"), ("B.SilkS", "White")):
        pat = re.compile(r'(\(layer "' + re.escape(layer) + r'"\s*\(type "[^"]*"\))(\s*\(color "[^"]*"\))?')
        text = pat.sub(lambda m: m.group(1) + f' (color "{colour}")', text, count=1)
    open(path, "w").write(text)


if __name__ == "__main__":
    main(*sys.argv[1:])
    sys.stdout.flush()
    os._exit(0)
