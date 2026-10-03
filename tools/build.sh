#!/usr/bin/env bash
# Rebuild the edited board from the upstream file, route it and run DRC.
#   v2: widened inner edges, jacks at the top, split inner thumb keys on both
#       halves, SK8707-01 trackpoint at the right outer thumb key.
set -euo pipefail
cd "$(dirname "$0")/.."
B=build
mkdir -p $B
git show 59d1639:"pcb/corne choc.kicad_pcb" > $B/upstream.kicad_pcb
python3 tools/make_footprints.py
refill() { bin/kcli pcb drc --refill-zones --save-board -o /dev/null "$1" >/dev/null 2>&1 || true; }

export NEW_EDGES=$B/new_edges.txt
rm -f $NEW_EDGES
bin/kpy tools/widen.py $B/upstream.kicad_pcb $B/s1.kicad_pcb
bin/kpy tools/top_edge.py $B/s1.kicad_pcb $B/s1.kicad_pcb
bin/kpy tools/split_thumbs.py $B/s1.kicad_pcb $B/s1.kicad_pcb
bin/kpy tools/outer_thumb.py $B/s1.kicad_pcb $B/s1.kicad_pcb
refill $B/s1.kicad_pcb
rm -f $B/affected.txt
AFFECTED_OUT=$B/affected.txt bin/kpy tools/cleanup.py $B/s1.kicad_pcb $B/s2.kicad_pcb \
  J1,J3,TP1,TP2,SW21,SW42,SW43,SW44,D21,D42,D45,D46,LED27,LED54,LED55,LED56 >$B/cleanup.log
bin/kpy tools/route_links.py $B/s2.kicad_pcb $B/s3.kicad_pcb

cp $B/s3.kicad_pcb $B/r.kicad_pcb
route() { bin/kpy tools/maze.py $B/r.kicad_pcb $B/r.kicad_pcb "$@"; }
# Long or awkward runs first, while the board is emptiest.
route VDD 0.3 TP2:5 J4:3                       # trackpoint 3.3 V (about 2 mA) from the OLED header
route TP_CLK 0.25 TP2:3 U2:12                  # trackpoint clock -> U2 pin 12 (GP9)
route TP_DATA 0.25 TP2:2 U2:11                 # trackpoint data  -> U2 pin 11 (GP8)
route data_r 0.25 J3:B U2:2                    # right TRRS data
route data 0.25 J1:B U1:2                      # left TRRS data
route VDD 0.3 J3:D U2:21                       # right TRRS power
route VCC 0.3 J1:D U1:21                       # left TRRS power
# Everything else DRC still reports missing.
bin/kpy tools/autoconnect.py $B/r.kicad_pcb
refill $B/r.kicad_pcb
cp $B/r.kicad_pcb $B/out.kicad_pcb
mapfile -t NETS < <(sort -u $B/affected.txt; printf '%s\n' TP_DATA TP_CLK VDD VCC data data_r)
while [ "$(bin/kpy tools/prune.py $B/out.kicad_pcb $B/out.kicad_pcb "${NETS[@]}" | tail -1)" != 0 ]; do :; done
# Finish: drop dead ends DRC finds, reconnect anything that opens, until clean.
for pass in 1 2 3; do
  bin/kcli pcb drc --refill-zones --save-board --format json -o $B/drc.json $B/out.kicad_pcb >/dev/null 2>&1 || true
  [ "$(bin/kpy tools/drop_dangling.py $B/out.kicad_pcb $B/drc.json | tail -1)" = 0 ] && \
    [ "$(python3 -c "import json;print(len([u for u in json.load(open('$B/drc.json')).get('unconnected_items',[]) if not all(i['description'].startswith('Zone') for i in u['items'])]))")" = 0 ] && break
  bin/kpy tools/autoconnect.py $B/out.kicad_pcb
done
bin/kcli pcb drc --refill-zones --save-board -o $B/drc.rpt $B/out.kicad_pcb >/dev/null 2>&1 || true
bin/kcli pcb drc --format json -o $B/drc.json $B/out.kicad_pcb >/dev/null 2>&1 || true
bin/kcli pcb drc --refill-zones --save-board --format json -o $B/drc_up.json $B/upstream.kicad_pcb >/dev/null 2>&1 || true
python3 tools/drcdiff.py $B/drc_up.json $B/drc.json
cp $B/out.kicad_pcb "pcb/corne choc.kicad_pcb"

# Switch plate (one design, flipped for the left half) and bottom plate.
git show 59d1639:"pcb/corne choc plate.kicad_pcb" > $B/plate_up.kicad_pcb
bin/kpy tools/plate.py $B/plate_up.kicad_pcb $B/out.kicad_pcb "pcb/corne choc plate.kicad_pcb"
bin/kcli pcb drc --refill-zones --save-board -o $B/plate_drc.rpt "pcb/corne choc plate.kicad_pcb" >/dev/null 2>&1 || true
bin/kpy tools/bottom_plate.py $B/out.kicad_pcb pcb/bottom.kicad_pcb
cp "pcb/corne choc plate.kicad_pro" pcb/bottom.kicad_pro
bin/kpy tools/printout.py $B/out.kicad_pcb $B/printout.svg
/nix/store/ii7wr6b6b8c5fq1ci26rw7amkb4apwm8-librsvg-2.62.3/bin/rsvg-convert -f pdf -o printout.pdf $B/printout.svg
