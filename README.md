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
  front, nub centred on where the key was, driver on the back, PS/2 clock and
  data on controller pins 1/2, 3.3 V from the OLED header
  (`tools/outer_thumb.py`, footprints from `tools/make_footprints.py`).
- **Pins for wireless.** Pins 1/2 are a nice!nano's high-frequency D1/D0, which
  the ZMK PS/2 driver recommends (lower-frequency pins can disturb Bluetooth);
  the TRRS data line moves from pin 2 to pin 11 to free them (`tools/pins.py`).
- **Outline.** Drawn from the keys (`tools/outline.py`): a flat top 1.15 mm
  above the middle column, 7.5-degree slopes to either side, a straight outer
  side, one 7.5-degree bottom edge, and the inner side widened for the upper
  thumb key (`tools/widen.py`). Keycaps sit 1.15 mm from the edge wherever it
  follows them.
- **Controller corner.** Across the strip between the inner index keycaps
  and the inner edge, the controller (a nice!nano's 17.78 mm board) and the
  jack's 6 mm body sit with three even 1.63 mm gaps; each drops until its square
  top corner is 1.15 mm inside the inner slope, like the keycaps. The USB-C and
  the jack's barrel overhang. The reset button sits under the jack
  (`tools/inner_strip.py`).
- The holykeebs and Corne logos are removed; the board and the switch plates
  carry the Petrock logo with a 7 mm dot in its notch (`tools/logo.py`), and the
  jack, reset button and OLED header have no printed outlines
  (`tools/quiet_silk.py`).
- Five standoffs per half, as stock, placed by geometry (`tools/standoffs.py`):
  four where four keys meet, each at the four keys' centre, forming a 54 x 34 mm
  rectangle (pinky and ring columns, and index and inner index columns, each
  between their top two rows and below their third); and one at the thumbs,
  equally far from its three keycap corners. A key diode may move a fraction to
  make room, if it stays clear. The switch plate has a screw hole over each
  (`tools/plate.py`), as stock.
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

Then `tools/plates.sh` makes the plates (order the switch plates at 1.2 mm,
which choc switches clip into; the main board and bottom plate at 1.6 mm; the
main board in ENIG, for flat gold pads under the trackpoint driver's
castellations; the plates have no exposed copper, so the cheapest finish)
and the 1:1 printout (print it with
scaling off, e.g. `lp -o print-scaling=none`). `tools/fab.sh [single|dual]`
writes Gerber and drill zips and JLC's assembly BOM and placement (diodes and
hot-swap sockets) to `fab/`; `tools/demo.sh` renders `demo/`. All need KiCad 10.

Outputs: `pcb/petrock-41*.kicad_pcb` and `pcb/bottom.kicad_pcb`;
`pcb/dual/petrock-40*.kicad_pcb` and `pcb/dual/bottom.kicad_pcb`.

## Assembly

The stack, per standoff: a top screw through the switch plate's 2.1 mm hole
into a spacer that passes through the main board's 3.1 mm hole down to the
bottom plate, where a bottom screw holds it. The switch plate and bottom plate
clamp the spacers; the main board hangs from the switches (clipped into the
plate, pins in the hot-swap sockets), 1.0 mm under the plate.

- 10 round M2 x 5 mm female-female spacers, 3.0 mm across (knurled brass ones
  are common; hex ones don't pass the 3.1 mm holes). 5 mm, not holykeebs' 4 mm:
  it leaves 2.4 mm under the main board for the sockets (1.85 mm) and the
  trackpoint drivers (about 2.1 mm).
- Top screws (they sit on the plate, beside the switches): the four where four
  keys meet sit between switch housings (15 mm square on an 18 x 17 mm grid),
  so their heads must be about 3.0 mm across or less: M2 low small-head socket
  screws (e.g. MISUMI's; check the listed head diameter), or M1.6 socket caps
  (3.0 mm heads) with M1.6 spacers at those four. The thumb one and the 10
  underneath: ordinary low M2 x 3 mm screws (e.g. ISO 7380, holykeebs').
- Order: spacers up through the main board, bottom plate on; switch plate on
  and its screws in; then the switches, which draw the main board up as they seat.
- Rubber feet: near the standoffs, and two along the bottom edge (by the outer
  corner and under the trackpoint), which has no standoff.

## Firmware

- Matrix (each half, right with `_r` nets): pinky fourth key row 3 col 1; ring
  fourth key row 3 col 2; upper inner thumb row 3 col 0; rows 0-2 of col 0
  are empty. The trackpoint replaces the outer thumb key (row 3 col 3).
- Wired (QMK, RP2040 Pro Micro): split serial on pin 11 (`SOFT_SERIAL_PIN GP8`,
  PIO driver); PS/2 `PS2_CLOCK_PIN GP0`, `PS2_DATA_PIN GP1` (PIO driver).
- Wireless (ZMK, nice!nano): PS/2 clock D1 (P0.06), data D0 (P0.08), e.g. with
  infused-kim's PS/2 mouse driver; the trackpoint's driver board resets itself,
  so no reset pin. It draws power from the controller's VCC pin, which ZMK's
  external-power control switches off in sleep. The battery solders to the
  nice!nano's B+/B- pads (no switch on the board). The jack isn't used.
- The sensor's pad edge faces the controller (if the axes come out turned,
  rotate them in firmware). No RGB.

## Open items

- **Driver footprint:** Sprintek doesn't draw the detached driver on its own.
  Its outline and sensor-link pads follow the integrated-module drawing. Its
  host pins disagree between the drawing (1.80 mm pitch) and holykeebs'
  product photos (1.72 mm), so their pads fit both: 1.758 mm pitch about the
  row's shared middle, every pin within 0.21 mm of its pad's centre either
  way. Check a real driver against the footprint before ordering boards.
- **Under-board height:** check that the driver (about 2 mm) clears the
  bottom plate.
- **Standoff length** for the plate/PCB/bottom sandwich (M2 3 mm both sides
  expected for the 1.6 mm FR4 bottom).
- **Schematic:** still the Corne Choc's.
