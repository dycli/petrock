"""Put an SK8707-01 trackpoint at a half's outer thumb key (right, or both).

Removes the key and its diode. The sensor sits flat on the front
over the key's place, the board centred on the key (its stem STEM_DROP below
the key's centre), and comes up through the plate's opening. The driver sits
flat on the back beneath it, turned across so it is narrower than a key, its
host pins facing the controller. Its PS/2 lines go to that half's controller pins 11/12 (GP8/GP9), its
power to the OLED header's 3.3 V pin. Both halves use the same placement: the
outline round the outer thumb is mirrored, and the parts are symmetric enough.

Positions are taken relative to the key as found on the board.

usage: outer_thumb.py IN OUT [right|left]   (one half per run: pcbnew can't
       load a second board cleanly in a process that has removed parts)
"""
import os
import sys

import pcbnew

MM = pcbnew.FromMM
LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib", "sk8707.pretty")

# The sensor board reaches SENSOR_ABOVE above its stem and SENSOR_BELOW below it,
# pad edge up; STEM_DROP centres it on the key.
SENSOR_ROT = 180.0               # pad edge up
SENSOR_HALF_W, SENSOR_ABOVE, SENSOR_BELOW = 6.6, 10.84, 7.45
STEM_DROP = (SENSOR_ABOVE - SENSOR_BELOW) / 2
# The driver board (23 x 14.5 mm), long side up-down; its centre this far from
# the key's centre (x toward the controller).
DRIVER_HALF_L, DRIVER_HALF_W = 11.5, 7.25
DRIVER_OFFSET = (0.0, -0.25)

HALVES = {
    # key and its diode; controller; sensor and driver refs; ground and 3.3 V nets; net suffix
    "right": dict(key="SW40", diode="D40", controller="U2", sensor="TP1", driver="TP2",
                  ground="GNDA", power="VDD", suffix=""),
    "left": dict(key="SW19", diode="D19", controller="U1", sensor="TP3", driver="TP4",
                 ground="GND", power="VCC", suffix="_L"),
}


def V(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


def mm(v):
    return (round(pcbnew.ToMM(v.x), 2), round(pcbnew.ToMM(v.y), 2))


def net(board, name):
    n = board.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
    return n


def load(name):
    fp = pcbnew.FootprintLoad(LIB, name)
    if fp is None:
        raise LookupError(name)
    return fp


def keepout(board, layer, corners, **no):
    """Rule area on one copper layer forbidding the given item kinds."""
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetLayer(layer)
    z.SetDoNotAllowTracks(no.get("tracks", False))
    z.SetDoNotAllowVias(no.get("vias", False))
    z.SetDoNotAllowZoneFills(no.get("fills", False))
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    o = z.Outline()
    o.NewOutline()
    for x, y in corners:
        o.Append(MM(x), MM(y))
    board.Add(z)


def place(board, h):
    index = {}
    for f in board.GetFootprints():
        index.setdefault(f.GetReference(), []).append(f)

    def one(ref):
        (f,) = index[ref]
        return f

    sfx = h["suffix"]
    # 4 (reset: the driver resets itself) and 6-8 (buttons) unused.
    driver_nets = {"1": h["ground"], "2": "TP_DATA" + sfx, "3": "TP_CLK" + sfx, "5": h["power"]}
    controller_nets = {"11": "TP_DATA" + sfx, "12": "TP_CLK" + sfx}       # pins 11/12 = GP8/GP9
    link_nets = {f"S{i}": f"TP_S{i}{sfx}" for i in range(1, 5)}

    p = one(h["key"]).GetPosition()
    key = (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))           # unrounded: the sensor centring is exact
    stem = (key[0], key[1] + STEM_DROP)
    inward = 1 if pcbnew.ToMM(one(h["controller"]).GetPosition().x) > key[0] else -1
    driver_centre = (key[0] + inward * DRIVER_OFFSET[0], key[1] + DRIVER_OFFSET[1])

    for ref in (h["key"], h["diode"]):
        board.Remove(one(ref))

    for p in one(h["controller"]).Pads():
        if p.GetNumber() in controller_nets:
            p.SetNet(net(board, controller_nets[p.GetNumber()]))

    sensor = load("SK8707-01_sensor")
    sensor.SetReference(h["sensor"])
    sensor.SetValue("SK8707-01 sensor")
    sensor.SetOrientationDegrees(SENSOR_ROT)
    sensor.SetPosition(V(*stem))
    for p in sensor.Pads():
        if p.GetNumber() in link_nets:
            p.SetNet(net(board, link_nets[p.GetNumber()]))
    board.Add(sensor)

    cx, cy = driver_centre
    for turn in (90.0, 270.0):
        driver = load("SK8707-01_driver")
        driver.SetReference(h["driver"])
        driver.SetValue("SK8707-01 driver")
        driver.SetOrientationDegrees(turn)
        driver.SetPosition(V(*driver_centre))
        board.Add(driver)
        driver.Flip(V(*driver_centre), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)  # needs the board's layer stack
        host_x = sum(pcbnew.ToMM(p.GetPosition().x) for p in driver.Pads() if p.GetNumber() in set("12345678")) / 8
        if (host_x - cx) * inward > 0:
            break
        board.Remove(driver)
    for p in driver.Pads():
        name = driver_nets.get(p.GetNumber()) or link_nets.get(p.GetNumber())
        if name:
            p.SetNet(net(board, name))
        if p.GetNumber() == "1":
            # Ground joins by a routed track: the pour's thermal spokes can't
            # all reach it between the castellations.
            p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_NONE)

    # The driver's underside carries exposed connector pads: no copper under it
    # on the back apart from its own castellations (5.6 mm in from the link
    # side, 6.0 from the host side, 11 mm either way along).
    near, far = (-5.6, 6.0) if inward > 0 else (-6.0, 5.6)
    keepout(board, pcbnew.B_Cu, [(cx + near, cy - 11.0), (cx + far, cy - 11.0), (cx + far, cy + 11.0), (cx + near, cy + 11.0)],
            tracks=True, vias=True, fills=True)

    # Nothing but the sensor's own links under the sensor on the front.
    sx, sy = stem
    keepout(board, pcbnew.F_Cu, [(sx - 6.85, sy - 7.3), (sx + 6.85, sy - 7.3), (sx + 6.85, sy + 7.7), (sx - 6.85, sy + 7.7)],
            tracks=True, vias=True)

    # Back copper just beyond the driver's host pins, so they have room to get
    # out; the router puts back whatever this cuts.
    escape = pcbnew.BOX2I(V(cx + 6.0 if inward > 0 else cx - 10.0, cy - 11.5), V(4.0, 23.0))
    doomed = [t for t in board.GetTracks() if t.IsOnLayer(pcbnew.B_Cu) and t.HitTest(escape, False)]
    for t in doomed:          # last: removing tracks invalidates other handles
        board.Remove(t)


def main(src, dst, half):
    board = pcbnew.LoadBoard(src)
    place(board, HALVES[half])
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "right")
    # pcbnew's SWIG objects crash Python's final garbage collection.
    sys.stdout.flush()
    os._exit(0)
