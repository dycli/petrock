"""Vias for the trackpoint's sensor-to-driver links.

The driver lies across under the sensor (tools/outer_thumb.py), its link pads
down the side away from the controller, in the opposite order to the sensor's
link pads along the sensor's top edge: the links have to cross. Each runs on the
front from the sensor pad out past the driver's side to its via, then on the
back straight across to its driver pad. The vias stand in a row of columns
beside the sensor, the link whose sensor pad is nearest that side in the
innermost column, so the front runs nest and the back stubs pass under them.

A via whose spot is taken (the extra thumb key's socket, say) slides along its
column to the nearest clear spot; the back stub then runs across at a slant.

Adds the vias and prints "pad x y" per link for tools/build.sh to route to.

usage: tp_links.py BOARD SENSOR DRIVER
"""
import os
import sys

import pcbnew

MM = pcbnew.FromMM
VIA_D, VIA_DRILL = 0.6, 0.4          # tools/maze.py
CLEAR = 0.4                          # via to the sensor's pads
PITCH = 0.95                         # between the via columns
COPPER_CLEAR = 0.35                  # via to other nets' copper and to holes
SLIDE_STEP, SLIDE_MAX = 0.25, 8.0


def main(path, sensor_ref, driver_ref):
    board = pcbnew.LoadBoard(path)
    fp = {f.GetReference(): f for f in board.GetFootprints()}
    sensor, driver = fp[sensor_ref], fp[driver_ref]
    links = {p.GetNumber(): p for p in driver.Pads() if p.GetNumber().startswith("S")}
    side = 1 if pcbnew.ToMM(links["S1"].GetPosition().x) > pcbnew.ToMM(driver.GetPosition().x) else -1
    edge = max(side * pcbnew.ToMM(p.GetBoundingBox().GetRight() if side > 0 else p.GetBoundingBox().GetLeft())
               for p in sensor.Pads())
    x0 = side * (edge + CLEAR + VIA_D / 2)
    spads = {p.GetNumber(): p for p in sensor.Pads() if p.GetNumber().startswith("S")}
    order = sorted(spads, key=lambda n: -side * pcbnew.ToMM(spads[n].GetPosition().x))   # nearest the side first
    # Read everything before adding to the board: that leaves pad handles stale.
    plan = [(n, x0 + side * rank * PITCH, pcbnew.ToMM(links[n].GetPosition().y), links[n].GetNetname())
            for rank, n in enumerate(order)]
    # Other nets' copper and every hole, and the rule areas that forbid vias.
    shapes = []
    for f in board.GetFootprints():
        for p in f.Pads():
            for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                if p.IsOnLayer(layer) or p.GetDrillSizeX() > 0:
                    shapes.append((p.GetNetname(), p.GetEffectiveShape(layer)))
    for t in board.GetTracks():
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            if t.IsOnLayer(layer):
                shapes.append((t.GetNetname(), t.GetEffectiveShape(layer)))
    no_vias = [z.Outline() for z in board.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
    chosen = []

    def clear(x, y, name):
        c = pcbnew.VECTOR2I(MM(x), MM(y))
        disc = pcbnew.SHAPE_CIRCLE(c, MM(VIA_D / 2))
        if any(n != name and sh.Collide(disc, MM(COPPER_CLEAR)) for n, sh in shapes):
            return False
        if any(z.Collide(c, MM(VIA_D / 2 + 0.1)) for z in no_vias):
            return False
        return all((x - cx) ** 2 + (y - cy) ** 2 >= (VIA_D + COPPER_CLEAR) ** 2 for cx, cy in chosen)

    def slide(x, y, name):
        k = 0.0
        while k <= SLIDE_MAX:
            for dy in ((k,) if k == 0 else (k, -k)):
                if clear(x, y + dy, name):
                    return y + dy
            k += SLIDE_STEP
        raise SystemExit(f"{name}: no room for its via near {x:.2f}, {y:.2f}")

    nets = {name: board.FindNet(name) for _, _, _, name in plan}
    for n, x, y, name in plan:
        y = slide(x, y, name)
        chosen.append((x, y))
        v = pcbnew.PCB_VIA(board)
        board.Add(v)
        v.SetNet(nets[name])
        v.SetIsFree(True)                 # it touches nothing yet: else saving drops its net
        v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        v.SetWidth(MM(VIA_D))
        v.SetDrill(MM(VIA_DRILL))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        print(n, round(x, 3), round(y, 3))
    board.Save(path)


if __name__ == "__main__":
    main(*sys.argv[1:4])
    sys.stdout.flush()
    os._exit(0)
