# Corne Choc with a right-thumb trackpoint

Based on holykeebs' Corne Choc PCB and plate from
[idank/keyboards](https://github.com/idank/keyboards) (`corne/choc`, commit
f149b9b), licensed CC-BY-SA-4.0. This derivative is under the same licence.

## Changes from upstream

- The right 1.5u thumb switch (SW42) and its diode are gone. TP1, a Pro Micro
  hole pattern, takes their place for the holykeebs trackpoint module. Pins
  5/6/21/23 carry GP2 (PS/2 data), GP3 (PS/2 clock), 3.3 V and GND, the same
  pins holykeebs' firmware uses. Pins 1/12/13/24 are unwired, for support only.
- The right OLED header is removed, because its pins now drive the trackpoint.
- Both halves are 6.2 mm wider along the inner edge. The TRRS jacks turn to
  face the top edge in that strip, beside each controller.
- The inner mounting hole of each half moves outward to clear the module.
- `plate-right` replaces the thumb switch opening with a cutout for the module;
  `plate-left` is upstream's plate, unchanged. `bottom` is a new FR4 bottom
  plate for the wider outline, with M2 holes at the standoff positions.

## Build

`tools/build.sh` regenerates every board from upstream and runs DRC.
`tools/fab.sh` writes Gerber and drill zips to `fab/`. Both expect KiCad 10.

## Open items

- The schematic still shows the upstream circuit, not these changes.
- The module's outline, nub position and stack height come from photos, not
  measurements. Check them against a real module before ordering.
