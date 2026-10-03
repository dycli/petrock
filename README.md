# Corne Choc with an outer-thumb trackpoint (v2.1)

Based on holykeebs' Corne Choc PCB and plate from
[idank/keyboards](https://github.com/idank/keyboards) (`corne/choc`, commit
f149b9b), licensed CC-BY-SA-4.0. This derivative uses the same licence.

## Changes from upstream

v1 (tag `v1`) keeps the stock outline and only adds the trackpoint. v2 adds:

- Both halves 6.2 mm wider along the inner edge; the TRRS jacks face the top
  edge in that strip, beside each controller.
- The inner 1.5u thumb key on each half becomes two 1u keys. The thumb keys
  sit on one arc (`tools/thumbs.py`): outer key level, middle key turned 15
  degrees, lower inner key turned and moved by the same step again (30
  degrees), so their corners line up. A new key sits one row above the lower
  inner key, on its row's spare column (col2). Each gets a diode and a per-key
  LED (inserted in the RGB chain after the moved key's LED). Every switch faces
  the same way, so all per-key LEDs sit on the same side.
- Keycaps sit 1.15 mm from the edge wherever it follows them, which leaves
  every hot-swap socket pad 0.33 mm from the edge (stock: 0.95 mm, and 0.13 mm
  on the right outer column). The outer side edges move out to that gap. The
  edge round the thumbs is redrawn from the keys, the same on both halves:
  beside and under the inner keys at that gap, rounding the bottom tip about
  the keycap's corner; under the middle and outer keys one level line below the
  middle keycap's lowest point, which leaves the trackpoint room.
- Peaked top edges: straight from each top corner to the middle-finger column.
- The trackpoint from v1: Sprintek SK8707-01-004 at the right outer thumb key,
  sensor on the front with its stem 3.4 mm below the old key centre (the
  board's long end above it), driver on the back, PS/2 on controller pins 11/12
  (GP8/GP9). LED52 under it is removed and the RGB chain bridged.
- The underglow LED beside the trackpoint driver (LED32) and its left twin
  (LED5) move to open board between the bottom row's LEDs, mirrored, so
  the driver's hand-soldered pads have room.
- The holykeebs and Corne logos are removed, and so are the mounting holes for
  holykeebs' OLED cover (the switch plate covers them; the cover isn't used).
- Switch plates regenerated: the left one is the right-half design flipped;
  the right one also has an opening round the trackpoint sensor, which stands
  taller than the gap under the plate. A new FR4 bottom plate fits the wider
  outline.

## Build

`tools/build.sh` regenerates the boards from upstream: outline and part edits,
cleanup, routing (`tools/maze.py`, a small two-layer grid router, driven by
`tools/autoconnect.py` from DRC's missing connections), pruning, DRC with a
diff against upstream's own report, then the plates and `printout.pdf` (plus `printout-scaled.pdf`, drawn
1.111x for a printer that shrinks to 90%). `tools/fab.sh` writes Gerber and drill zips to
`fab/`. Both need KiCad 10.

Footprints come from `tools/make_footprints.py`, generated from Sprintek
datasheet DS0048 v1.04 (`ref/`, not committed).

## Open items

- **Driver footprint:** Sprintek doesn't draw the detached driver on its own.
  Its footprint comes from the integrated-module drawing, checked against
  holykeebs' top-view photo (`ref/sk8707-01-004-top.png`): 23 x 14.5 mm,
  sensor-link pads at 2.5 mm pitch in the same order as the sensor's, pin 1 at
  the left. The host pins follow the drawing's 1.80 mm pitch, with 1.0 mm pads
  (0.8 mm between them, for hand soldering); holykeebs' photo measured 1.73-1.76
  mm, most likely photo scale.
- **Under-board height:** check that the driver (about 2 mm) clears holykeebs'
  case or bottom plate.
- **Firmware:** override `PS2_DATA_PIN GP8` / `PS2_CLOCK_PIN GP9`; the
  sensor's pad edge faces the controller, as on v2 (if the axes come out
  turned, `PS2_MOUSE_ROTATE` fixes it); keymap
  gains the two new thumb keys (row 3, col 2) and loses the right outer thumb;
  RGB layout gains LED55/LED56 and loses LED52.
- **Standoff length** for the plate/PCB/bottom sandwich.
- **Schematic:** still upstream's.
