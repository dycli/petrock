# Corne Choc with an outer-thumb trackpoint (v2)

Based on holykeebs' Corne Choc PCB and plate from
[idank/keyboards](https://github.com/idank/keyboards) (`corne/choc`, commit
f149b9b), licensed CC-BY-SA-4.0. This derivative uses the same licence.

## Changes from upstream

v1 (tag `v1`) keeps the stock outline and only adds the trackpoint. v2 adds:

- Both halves 6.2 mm wider along the inner edge; the TRRS jacks face the top
  edge in that strip, beside each controller.
- The inner 1.5u thumb key on each half becomes two 1u keys at the same angle:
  the old key moved 4.5 mm down its axis, a new key above it on its row's spare
  column (col2). Each gets a diode and a per-key LED (inserted in the RGB chain
  after the moved key's LED). The right lower key is turned 180 degrees so its
  hot-swap pads clear the board edge; its LED turns with it.
- The angled inner edge runs straight up along both inner thumb keys to the
  widened edge, and it and the short bottom edge under the lower key sit
  0.95 mm from the keycaps, like the outer column.
- Peaked top edges: straight from each top corner to the middle-finger column.
- The trackpoint from v1: Sprintek SK8707-01-004 at the right outer thumb key,
  sensor on the front, driver on the back, PS/2 on controller pins 11/12
  (GP8/GP9). LED52 under it is removed and the RGB chain bridged.
- Switch plate regenerated (one design, flipped for the left half) and a new
  FR4 bottom plate for the wider outline.

## Build

`tools/build.sh` regenerates the boards from upstream: outline and part edits,
cleanup, routing (`tools/maze.py`, a small two-layer grid router, driven by
`tools/autoconnect.py` from DRC's missing connections), pruning, DRC with a
diff against upstream's own report, then the plates and `printout.pdf`. `tools/fab.sh` writes Gerber and drill zips to
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
- **Firmware:** override `PS2_DATA_PIN GP8` / `PS2_CLOCK_PIN GP9`; keymap
  gains the two new thumb keys (row 3, col 2) and loses the right outer thumb;
  RGB layout gains LED55/LED56 and loses LED52.
- **Standoff length** for the plate/PCB/bottom sandwich.
- **Schematic:** still upstream's.
