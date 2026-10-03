#!/usr/bin/env bash
# Rebuild the edited board from the upstream file and run DRC.
set -euo pipefail
cd "$(dirname "$0")/.."
B=build
git show 59d1639:"pcb/corne choc.kicad_pcb" > $B/upstream.kicad_pcb
bin/kpy tools/thumb_trackpoint.py $B/upstream.kicad_pcb $B/s1.kicad_pcb
bin/kcli pcb drc --refill-zones --save-board -o /dev/null $B/s1.kicad_pcb >/dev/null 2>&1 || true
bin/kpy tools/cleanup.py $B/s1.kicad_pcb $B/s2.kicad_pcb >$B/cleanup.log
bin/kpy tools/route_new.py $B/s2.kicad_pcb $B/out.kicad_pcb
bin/kcli pcb drc --refill-zones --save-board --schematic-parity -o $B/drc.rpt $B/out.kicad_pcb >/dev/null 2>&1 || true
grep -oE '^\[[a-z_]+\]' $B/drc.rpt | sort | uniq -c

# Right switch plate (left half uses the upstream plate, flipped) and bottom plate.
git show 59d1639:"pcb/corne choc plate.kicad_pcb" > $B/plate_up.kicad_pcb
bin/kpy tools/plate_right.py $B/plate_up.kicad_pcb $B/plate_right.kicad_pcb
bin/kcli pcb drc --refill-zones --save-board -o $B/plate_drc.rpt $B/plate_right.kicad_pcb >/dev/null 2>&1 || true
echo "right plate:"; grep -oE '^\[[a-z_]+\]' $B/plate_drc.rpt | sort | uniq -c
bin/kpy tools/bottom_plate.py $B/out.kicad_pcb $B/bottom.kicad_pcb
bin/kcli pcb drc -o $B/bottom_drc.rpt $B/bottom.kicad_pcb >/dev/null 2>&1 || true
echo "bottom plate:"; grep -oE '^\[[a-z_]+\]' $B/bottom_drc.rpt | sort | uniq -c

cp $B/out.kicad_pcb "pcb/corne choc.kicad_pcb"
cp $B/plate_right.kicad_pcb pcb/plate-right.kicad_pcb
cp $B/bottom.kicad_pcb pcb/bottom.kicad_pcb
