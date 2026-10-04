# Petrock

A split 41- or 40-key choc keyboard with a trackpoint in place of an outer
thumb key: **Petrock-41** has one, at the right thumb; **Petrock-40** has one on
each half.

Based on holykeebs' Corne Choc PCB and plate from
[idank/keyboards](https://github.com/idank/keyboards) (`corne/choc`, commit
f149b9b), licensed CC-BY-SA-4.0. This derivative uses the same licence.

## Changes from the Corne Choc

The board is built from the stock file with as few changes to its copper as
the layout allows: parts move with their tracks, only copper that ends up off
the board or in a new clash is cut, and only what is then open is routed
(see Build). About 60% of the stock copper stays, in place or carried along.

- **No lighting.** Every per-key and underglow LED, the LED supply diodes and
  the LED wiring are gone (`tools/no_leds.py`). An RGB version may follow.
- **Exact stagger.** Rows exactly 17 mm apart, each column's top key a whole
  number of 2.37 mm steps below the middle finger's (`tools/stagger.py`;
  stock is off by up to 0.02 mm).
- **Five columns.** The outer pinky column goes. The pinky column moves up to
  one step below the ring column and gains a fourth key (the old outer top
  key); the ring column gains one too (the old outer bottom key). Each joins
  the column wire it lands on, in the thumb row (row 3).
- **Thumb cluster.** Each thumb key turns 15 degrees from its neighbour about a
  hinge where their facing corners sit 0.5 mm apart, starting from the bottom
  inner-index key (`tools/thumbs.py`). The 1.5u inner key becomes two 1u keys;
  the new upper one takes the thumb row's last free column (col 0).
- **Trackpoint.** Sprintek SK8707-01-004 at the outer thumb key: sensor on the
  front, nub centred on where the key was, driver on the back, PS/2 on
  controller pins 11/12 (GP8/GP9), 3.3 V from the OLED header
  (`tools/outer_thumb.py`, footprints from `tools/make_footprints.py`).
- **Outline.** Drawn from the keys (`tools/outline.py`): a flat top 1.15 mm
  above the middle column, 7.5-degree slopes to either side, a straight outer
  side, one 7.5-degree bottom edge, and the inner side widened for the upper
  thumb key (`tools/widen.py`). Keycaps sit 1.15 mm from the edge wherever it
  follows them.
- **Controller corner.** The controller and OLED header drop 3.35 mm under the
  inner slope; the TRRS jack faces the top edge beside them, with the reset
  button below it (`tools/inner_strip.py`).
- The holykeebs and Corne logos and the OLED-cover holes are removed; the
  switch plates carry the thumb-cluster logo (`tools/logo.py`).
- Plates regenerated (`tools/plate.py`): the right one (both, on Petrock-40)
  has an opening for the trackpoint sensor; a new FR4 bottom plate fits the
  outline.

## Build

`tools/build.sh [single|dual]` regenerates a board from the stock file:

1. **Place:** strip the lighting, then move every part to the layout, dragging
   its copper (`tools/parts.py drag`).
2. **Fit:** nudge copper the new edge crowds back inside it (`tools/edge_fit.py`).
3. **Trim:** cut copper off the board or in a clash the stock board didn't
   already have (`tools/trim.py`; stock already breaks DRC in places, e.g. by
   its LED windows).
4. **Route:** the trackpoint links (`tools/tp_links.py`), then everything open
   (`tools/autoconnect.py` driving `tools/maze.py`), never ripping up stock
   copper; strip dead ends; diff DRC against the stock board's
   (`tools/drcdiff.py`) and report how much stock copper is unchanged
   (`tools/reuse.py`).

Then `tools/plates.sh` makes the plates and the 1:1 printout (print it with
scaling off, e.g. `lp -o print-scaling=none`). `tools/fab.sh [single|dual]`
writes Gerber and drill zips and JLC's assembly BOM and placement (diodes and
hot-swap sockets) to `fab/`; `tools/demo.sh` renders `demo/`. All need KiCad 10.

Outputs: `pcb/petrock-41*.kicad_pcb` and `pcb/bottom.kicad_pcb`;
`pcb/dual/petrock-40*.kicad_pcb` and `pcb/dual/bottom.kicad_pcb`.

## Firmware

- Matrix (each half, right with `_r` nets): pinky fourth key row 3 col 1; ring
  fourth key row 3 col 2; upper inner thumb row 3 col 0; rows 0-2 of col 0
  are empty. The trackpoint replaces the outer thumb key (row 3 col 3).
- PS/2: `PS2_DATA_PIN GP8`, `PS2_CLOCK_PIN GP9`; the sensor's pad edge faces
  the controller (if the axes come out turned, `PS2_MOUSE_ROTATE` fixes it).
- No RGB.

## Open items

- **Driver footprint:** Sprintek doesn't draw the detached driver on its own;
  it comes from the integrated-module drawing, checked against holykeebs'
  top-view photo (`ref/`, not committed): 23 x 14.5 mm, host pins at 1.80 mm
  pitch with 1.0 mm pads for hand soldering.
- **Under-board height:** check that the driver (about 2 mm) clears the
  bottom plate.
- **Standoff length** for the plate/PCB/bottom sandwich (M2 3 mm both sides
  expected for the 1.6 mm FR4 bottom).
- **Schematic:** still the Corne Choc's.
