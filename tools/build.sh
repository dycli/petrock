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
