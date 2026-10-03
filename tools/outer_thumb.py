"""Put an SK8707-01 trackpoint at a half's outer thumb key (right, or both).

Removes the key, its diode and its per-key LED (hidden under the sensor; the RGB
chain is bridged and its old link rerouted). The sensor sits flat on the front
over the key's place, its stem STEM_DROP below the key's centre, and comes up
through the plate's opening. The driver sits flat on the back, directly
beneath. Its PS/2 lines go to that half's controller pins 11/12 (GP8/GP9), its
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

# The sensor board covers the key's centre -7.45..+10.84 mm (tools/widen.py shapes
# the edge round that). Pad edge up puts the stem STEM_DROP below the key's
# centre, closer to the thumb.
SENSOR_ROT = 180.0               # pad edge up
STEM_DROP = 10.84 - 7.45
DRIVER_ROT = 0.0                 # sensor-link edge up, beside the sensor's pads
DRIVER_OFFSET = (0.0, -1.37)     # from the key's centre, on the back; clears the diagonal edge

HALVES = {
    # key, its diode and LED; controller; sensor and driver refs; ground and 3.3 V nets; net suffix
    "right": dict(key="SW40", diode="D40", led="LED52", controller="U2", sensor="TP1", driver="TP2",
                  ground="GNDA", power="VDD", suffix=""),
    "left": dict(key="SW19", diode="D19", led="LED25", controller="U1", sensor="TP3", driver="TP4",
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
    driver_nets = {"1": h["ground"], "2": "TP_DATA" + sfx, "3": "TP_CLK" + sfx, "5": h["power"]}  # 4 RST, 6-8 buttons: unused
    controller_nets = {"11": "TP_DATA" + sfx, "12": "TP_CLK" + sfx}                               # pins 11/12 = GP8/GP9
    link_nets = {f"S{i}": f"TP_S{i}{sfx}" for i in range(1, 5)}

    key = mm(one(h["key"]).GetPosition())
    stem = (key[0], key[1] + STEM_DROP)
    driver_centre = (key[0] + DRIVER_OFFSET[0], key[1] + DRIVER_OFFSET[1])

    # RGB chain: the LED's output net joins its input net, and the input net's
    # old copper (the link into the LED) goes; the router redraws the link.
    pads = {p.GetNumber(): p.GetNetname() for p in one(h["led"]).Pads()}
    chain_in, chain_out = pads["4"], pads["2"]
    for ref in (h["key"], h["diode"], h["led"]):
        board.Remove(one(ref))
    chain = board.FindNet(chain_in)
    for f in board.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() == chain_out:
                p.SetNet(chain)
    old_link = [t for t in board.GetTracks() if t.GetNetname() == chain_in]
    for t in board.GetTracks():
        if t.GetNetname() == chain_out:
            t.SetNet(chain)

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

    driver = load("SK8707-01_driver")
    driver.SetReference(h["driver"])
    driver.SetValue("SK8707-01 driver")
    driver.SetOrientationDegrees(DRIVER_ROT)
    driver.SetPosition(V(*driver_centre))
    for p in driver.Pads():
        name = driver_nets.get(p.GetNumber()) or link_nets.get(p.GetNumber())
        if name:
            p.SetNet(net(board, name))
        if p.GetNumber() == "1":
            # Ground joins by a routed track: the pour's thermal spokes can't
            # all reach it between the castellations.
            p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_NONE)
    board.Add(driver)
    driver.Flip(V(*driver_centre), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)  # needs the board's layer stack

    # The driver's underside carries exposed connector pads: no copper under it
    # on the back apart from its own castellations.
    cx, cy = driver_centre
    keepout(board, pcbnew.B_Cu, [(cx - 11.0, cy - 5.6), (cx + 11.0, cy - 5.6), (cx + 11.0, cy + 6.0), (cx - 11.0, cy + 6.0)],
            tracks=True, vias=True, fills=True)

    # Nothing but the sensor's own links under the sensor on the front.
    sx, sy = stem
    keepout(board, pcbnew.F_Cu, [(sx - 6.85, sy - 7.3), (sx + 6.85, sy - 7.3), (sx + 6.85, sy + 7.7), (sx - 6.85, sy + 7.7)],
            tracks=True, vias=True)

    # Back copper just below the driver's host pins, so they have room to get
    # out; the router puts back whatever this cuts.
    escape = pcbnew.BOX2I(V(cx - 11.5, cy + 6.0), V(23.0, 4.0))
    old = {t.m_Uuid.AsString() for t in old_link}
    doomed = old_link + [t for t in board.GetTracks()
                         if t.IsOnLayer(pcbnew.B_Cu) and t.HitTest(escape, False) and t.m_Uuid.AsString() not in old]
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
