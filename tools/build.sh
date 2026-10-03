#!/usr/bin/env bash
# Rebuild the edited board from the upstream file, route it and run DRC.
set -euo pipefail
cd "$(dirname "$0")/.."
B=build
mkdir -p $B
git show 59d1639:"pcb/corne choc.kicad_pcb" > $B/upstream.kicad_pcb
python3 tools/make_footprints.py
refill() { bin/kcli pcb drc --refill-zones --save-board -o /dev/null "$1" >/dev/null 2>&1 || true; }

bin/kpy tools/outer_thumb.py $B/upstream.kicad_pcb $B/s1.kicad_pcb
refill $B/s1.kicad_pcb
bin/kpy tools/cleanup.py $B/s1.kicad_pcb $B/s2.kicad_pcb >$B/cleanup.log
bin/kpy tools/route_links.py $B/s2.kicad_pcb $B/s3.kicad_pcb
# Route everything the edit opened with the grid router; "any" means the nearest
# same-net copper that isn't already connected to the start.
cp $B/s3.kicad_pcb $B/r.kicad_pcb
route() { bin/kpy tools/maze.py $B/r.kicad_pcb $B/r.kicad_pcb "$@"; }
route VDD 0.3 TP2:5 J4:3                   # driver 3.3 V (about 2 mA) from the OLED header's VDD pin
route TP_CLK 0.25 TP2:3 U2:12                 # driver pin 3 -> U2 pin 12 (GP9)
route TP_DATA 0.25 TP2:2 U2:11               # driver pin 2 -> U2 pin 11 (GP8)
route 'Net-(LED52-DIN)' 0.25 LED49:4 any                 # RGB chain across the removed LED
route 'Net-(LED32-DOUT)' 0.25 LED32:2 178.67,107.78,F   # RGB chain, cut by the driver
route 'Net-(LED50-DOUT)' 0.25 LED50:2 any                # RGB chain, cut by the driver
route 'Net-(D44-K)' 0.5 189.28,120.6,B 217.51,103.8,FB          # LED power, around the driver
route col4_r 0.25 193.66,114.35,B 204.16,92.16,F         # column 4 to the middle thumb key
route GNDA 0.5 TP2:1 any                               # driver ground
route GNDA 0.5 LED50:3 any                               # LED50 ground, cut off from the pour by the new traces
refill $B/r.kicad_pcb
cp $B/r.kicad_pcb $B/out.kicad_pcb
while [ "$(bin/kpy tools/prune.py $B/out.kicad_pcb $B/out.kicad_pcb GNDA VDD col3_r col4_r row3_r \
  'Net-(LED52-DIN)' 'Net-(LED32-DOUT)' 'Net-(LED50-DOUT)' 'Net-(D44-K)' TP_DATA TP_CLK | tail -1)" != 0 ]; do :; done
bin/kcli pcb drc --refill-zones --save-board --format json -o $B/drc.json $B/out.kicad_pcb >/dev/null 2>&1 || true
bin/kpy tools/drop_dangling.py $B/out.kicad_pcb $B/drc.json      # stubs KiCad only reveals on save
bin/kcli pcb drc --refill-zones --save-board -o $B/drc.rpt $B/out.kicad_pcb >/dev/null 2>&1 || true
bin/kcli pcb drc --format json -o $B/drc.json $B/out.kicad_pcb >/dev/null 2>&1 || true
bin/kcli pcb drc --refill-zones --save-board --format json -o $B/drc_up.json $B/upstream.kicad_pcb >/dev/null 2>&1 || true
python3 tools/drcdiff.py $B/drc_up.json $B/drc.json
cp $B/out.kicad_pcb "pcb/corne choc.kicad_pcb"
