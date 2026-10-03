# Corne Choc with an outer-thumb trackpoint

Based on holykeebs' Corne Choc PCB and plate from
[idank/keyboards](https://github.com/idank/keyboards) (`corne/choc`, commit
f149b9b), licensed CC-BY-SA-4.0. This derivative uses the same licence.

## Change from upstream

The right half's outer thumb key becomes a Sprintek SK8707-01-004 trackpoint
(detached sensor + driver, the part holykeebs sells). Nothing else moves: the
outline, jacks, mounting holes, OLED headers and switch plate are stock, so
holykeebs' plate and case still fit.

- SW40 (outer thumb switch), its diode D40 and its LED52 are removed. The LED
  would sit hidden under the sensor; the RGB chain is bridged around it, so the
  firmware's LED list loses one entry.
- TP1, the sensor, sits flat on the front at SW40's centre. Its stem comes up
  through SW40's switch-plate opening, about 5 mm below the keycap tops.
- TP2, the driver, sits flat on the back directly underneath. The two are
  linked through four vias.
- PS/2 data and clock go to controller pins 11 and 12 (GP8 and GP9 on
  holykeebs' RP2040 controllers); 3.3 V comes from the right OLED header's VDD.
  The driver's reset and button pins are unused.

## Build

`tools/build.sh` regenerates the board from upstream: edit, cleanup, routing
(`tools/maze.py`, a small two-layer grid router), pruning, then DRC with a diff
against upstream's own report. `tools/fab.sh` writes Gerber and drill zips to
`fab/`. Both need KiCad 10.

Footprints come from `tools/make_footprints.py`, generated from Sprintek
datasheet DS0048 v1.04 (`ref/`, not committed).

## Open items

- **Driver footprint:** Sprintek doesn't draw the detached driver on its own.
  Its footprint comes from the integrated-module drawing, checked against
  holykeebs' top-view photo (`ref/sk8707-01-004-top.png`): 23 x 14.5 mm,
  sensor-link pads at 2.5 mm pitch in the same order as the sensor's, pin 1 at
  the left. The host-pin pitch measures 1.73-1.76 mm in the photo against
  1.80 mm in the drawing, so those pads are widened to cover either. A caliper
  check on a real part is still worthwhile before ordering.
- **Under-board height:** check that the driver (about 2 mm) clears holykeebs'
  case or bottom plate.
- **Firmware:** override `PS2_DATA_PIN GP8` / `PS2_CLOCK_PIN GP9`, remove the
  outer thumb key from the keymap, and drop LED52 from the RGB layout.
- **Schematic:** still upstream's.
