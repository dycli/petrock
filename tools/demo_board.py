"""Make a render-only copy of the board: black mask, real 3D models where they
exist (sockets, LEDs, diodes, controller, jacks, reset buttons), switches and
stand-in keycaps on top, the trackpoint's sensor, nub and driver.

usage: demo_board.py IN OUT MARBASTLIB_DIR KBD_DIR PACKAGES3D_DIR STANDIN_DIR [bare]
       "bare" leaves out the switches and keycaps, to show the board itself.
"""
import os
import sys

import pcbnew

MM = pcbnew.FromMM


def model(path, z=0.0, rot=(0, 0, 0), offset=(0.0, 0.0)):
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = path
    m.m_Offset = pcbnew.VECTOR3D(offset[0], offset[1], z)
    m.m_Rotation = pcbnew.VECTOR3D(*rot)
    m.m_Scale = pcbnew.VECTOR3D(1, 1, 1)
    m.m_Show = True
    return m


def main(src, dst, marbast, kbd, pkg3d, standin, bare=""):
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
        for m in models:
            for a, b in subst.items():
                if m.m_Filename.startswith(a):
                    m.m_Filename = b + m.m_Filename[len(a):]
            f.Models().push_back(m)
        if "SW_choc" in f.GetFPIDAsString():
            keys.append((f.GetPosition(), f.GetOrientationDegrees()))
        elif f.GetReference() == "TP1":
            tp = f
        elif f.GetReference() == "TP2":
            f.Models().push_back(model(os.path.join(standin, "driver.wrl")))
    if tp is not None:
        tp.Models().push_back(model(os.path.join(standin, "sensor.wrl")))
        tp.Models().push_back(model(os.path.join(standin, "nub.wrl")))
    # Switch + keycap on the top side for every key (the key footprints sit on the
    # back, where the hot-swap sockets are).
    choc = os.path.join(kbd, "kicad-packages3D", "kbd.3dshapes", "kailh_choc.step")
    for pos, deg in ([] if bare else keys):
        v = pcbnew.FOOTPRINT(board)
        v.SetPosition(pos)
        v.SetOrientationDegrees(deg)
        v.Models().push_back(model(choc, z=0.0))
        v.Models().push_back(model(os.path.join(standin, "keycap.wrl")))
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
