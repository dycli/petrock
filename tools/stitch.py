"""Front pours become ground (GND left, GNDA right) and both sides are stitched
with vias on a grid wherever both pours have room for one.

usage: stitch.py BOARD [STEP_MM]   (edits BOARD in place; prints vias added)
"""
import math
import os
import sys

import pcbnew

path = sys.argv[1]
step = pcbnew.FromMM(float(sys.argv[2]) if len(sys.argv) > 2 else 5)
VIA, DRILL = pcbnew.FromMM(0.6), pcbnew.FromMM(0.4)
R = VIA // 2 + pcbnew.FromMM(0.3)      # via radius + the pour's clearance to it
MID = pcbnew.FromMM(155)               # between the halves
RING = [pcbnew.VECTOR2I(0, 0)] + [pcbnew.VECTOR2I(int(R * math.cos(a * math.pi / 8)), int(R * math.sin(a * math.pi / 8)))
                                  for a in range(16)]   # the via and its clearance must lie in the pour

b = pcbnew.LoadBoard(path)
nets = {True: b.FindNet("GND"), False: b.FindNet("GNDA")}
pours = [z for z in b.Zones() if not z.GetIsRuleArea()]
for z in pours:
    if not z.GetNetname():
        z.SetNet(nets[z.GetBoundingBox().GetX() < MID])
    # Keep cut-off pieces for now, so they get stitched too; the floating rest
    # goes when the pour is refilled with islands removed.
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_NEVER)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())


def room(zones, layer, p):
    for z in zones:
        polys = z.GetFilledPolysList(layer)
        if all(polys.Contains(p + d) for d in RING):
            return True
    return False


added = 0
box = b.GetBoardEdgesBoundingBox()
for left in (True, False):
    code = nets[left].GetNetCode()
    mine = [z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetCode() == code]
    front = [z for z in mine if z.IsOnLayer(pcbnew.F_Cu)]
    back = [z for z in mine if z.IsOnLayer(pcbnew.B_Cu)]
    x = box.GetX() + step // 2
    while x < box.GetRight():
        y = box.GetY() + step // 2
        while y < box.GetBottom():
            p = pcbnew.VECTOR2I(int(x), int(y))
            if (x < MID) == left and room(front, pcbnew.F_Cu, p) and room(back, pcbnew.B_Cu, p):
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(p)
                v.SetWidth(VIA)
                v.SetDrill(DRILL)
                v.SetNet(nets[left])
                b.Add(v)
                added += 1
            y += step
        x += step
for z in pours:
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(path)
print(added)
sys.stdout.flush()
os._exit(0)
