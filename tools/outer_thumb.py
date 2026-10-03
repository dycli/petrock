"""Put an SK8707-01 trackpoint at the right half's outer thumb key.

Removes SW40, its diode D40 and its LED52 (hidden under the sensor; the RGB chain
is bridged). The sensor sits flat on the front at SW40's centre, its stem coming
up through SW40's switch-plate opening. The driver sits flat on the back,
directly beneath. Its PS/2 lines go to controller pins 11/12 (GP8/GP9).

Positions are taken relative to SW40 as found on the board, so this works on
the upstream board or on one whose right half has been shifted.
"""
import os
import sys

import pcbnew

MM = pcbnew.FromMM
LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib", "sk8707.pretty")

SENSOR_ROT = 180.0               # pad edge toward the controller
DRIVER_OFFSET = (0.0, -1.37)     # from SW40's centre, on the back, sensor-link edge up; corner clears the board edge by 0.5 mm
UPSTREAM_SW40 = (206.71, 117.52) # for the few upstream track coordinates below
DRIVER_NETS = {"1": "GNDA", "2": "TP_DATA", "3": "TP_CLK", "5": "VDD"}   # 4 RST, 6-8 buttons: unused
CONTROLLER_NETS = {"11": "TP_DATA", "12": "TP_CLK"}                      # U2 pins 11/12 = GP8/GP9
LINK_NETS = {f"S{i}": f"TP_S{i}" for i in range(1, 5)}

# RGB chain: LED52's input net takes over its output net.
CHAIN_IN, CHAIN_OUT = "Net-(LED52-DIN)", "Net-(LED49-DIN)"


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


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    index = {}
    for f in board.GetFootprints():
        index.setdefault(f.GetReference(), []).append(f)

    def one(ref):
        (f,) = index[ref]
        return f

    stem = mm(one("SW40").GetPosition())
    shift = (round(stem[0] - UPSTREAM_SW40[0], 2), round(stem[1] - UPSTREAM_SW40[1], 2))
    driver_centre = (stem[0] + DRIVER_OFFSET[0], stem[1] + DRIVER_OFFSET[1])

    for ref in ("SW40", "D40", "LED52"):
        board.Remove(one(ref))

    # Bridge the RGB chain: everything on LED52's output net joins its input net.
    # Copper that only fed LED52 is left to cleanup.py as dangling.
    chain = board.FindNet(CHAIN_IN)
    for f in board.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() == CHAIN_OUT:
                p.SetNet(chain)
    for t in board.GetTracks():
        if t.GetNetname() == CHAIN_OUT:
            t.SetNet(chain)

    u2 = one("U2")
    for p in u2.Pads():
        if p.GetNumber() in CONTROLLER_NETS:
            p.SetNet(net(board, CONTROLLER_NETS[p.GetNumber()]))

    sensor = load("SK8707-01_sensor")
    sensor.SetReference("TP1")
    sensor.SetValue("SK8707-01 sensor")
    sensor.SetOrientationDegrees(SENSOR_ROT)
    sensor.SetPosition(V(*stem))
    for p in sensor.Pads():
        if p.GetNumber() in LINK_NETS:
            p.SetNet(net(board, LINK_NETS[p.GetNumber()]))
    board.Add(sensor)

    driver = load("SK8707-01_driver")
    driver.SetReference("TP2")
    driver.SetValue("SK8707-01 driver")
    driver.SetPosition(V(*driver_centre))
    for p in driver.Pads():
        name = DRIVER_NETS.get(p.GetNumber()) or LINK_NETS.get(p.GetNumber())
        if name:
            p.SetNet(net(board, name))
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

    # Last: removing tracks invalidates other SWIG handles.
    # Copper that only fed LED52's input pad. Left in place, KiCad later
    # re-nets it to ground and it becomes an orphan island.
    def up(p):
        return (round(p[0] + shift[0], 2), round(p[1] + shift[1], 2))
    dead = {(up(a), up(b)) for a, b in (((191.81, 121.98), (196.69, 121.98)), ((196.69, 121.98), (196.73, 121.94)),
                                       ((196.73, 121.94), (197.04, 121.94)), ((197.04, 121.94), (197.51, 121.47)),
                                       ((197.51, 121.47), (203.99, 121.47)))}
    for t in list(board.GetTracks()):
        if t.GetNetname() != CHAIN_IN:
            continue
        ends = (mm(t.GetStart()), mm(t.GetEnd()))
        if t.GetClass() == "PCB_VIA" and ends[0] == up((196.73, 121.94)) or ends in dead or ends[::-1] in dead:
            board.Remove(t)

    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    # pcbnew's SWIG objects crash Python's final garbage collection.
    sys.stdout.flush()
    os._exit(0)
