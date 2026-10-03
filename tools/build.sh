#!/usr/bin/env bash
# Rebuild the edited board from the upstream file, route it and run DRC, then
# make the plates and the printout.
#   usage: build.sh [single|dual]
#   single: SK8707-01 trackpoint at the right outer thumb key (pcb/, printout.pdf)
#   dual:   trackpoints at both outer thumb keys (pcb/dual/, printout-dual.pdf)
set -euo pipefail
cd "$(dirname "$0")/.."
VARIANT=${1:-single}
case $VARIANT in
  single) B=build;      OUT=pcb;      NAME="corne choc";      TPS=(right);      PRINT=printout ;;
  dual)   B=build/dual; OUT=pcb/dual; NAME="corne choc dual"; TPS=(right left); PRINT=printout-dual ;;
  *) echo "unknown variant $VARIANT" >&2; exit 1 ;;
esac
dual() { [ "$VARIANT" = dual ]; }
mkdir -p $B $OUT
git show 59d1639:"pcb/corne choc.kicad_pcb" > $B/upstream.kicad_pcb
python3 tools/make_footprints.py
refill() { bin/kcli pcb drc --refill-zones --save-board -o /dev/null "$1" >/dev/null 2>&1 || true; }

export NEW_EDGES=$B/new_edges.txt
rm -f $NEW_EDGES
bin/kpy tools/widen.py $B/upstream.kicad_pcb $B/s1.kicad_pcb
bin/kpy tools/top_edge.py $B/s1.kicad_pcb $B/s1.kicad_pcb
bin/kpy tools/split_thumbs.py $B/s1.kicad_pcb $B/s1.kicad_pcb
for h in "${TPS[@]}"; do bin/kpy tools/outer_thumb.py $B/s1.kicad_pcb $B/s1.kicad_pcb $h; done
bin/kpy tools/strip.py $B/s1.kicad_pcb $B/s1.kicad_pcb
bin/kpy tools/underglow.py $B/s1.kicad_pcb $B/s1.kicad_pcb
refill $B/s1.kicad_pcb
rm -f $B/affected.txt
AFFECTED_OUT=$B/affected.txt bin/kpy tools/cleanup.py $B/s1.kicad_pcb $B/s2.kicad_pcb \
  J1,J3,TP1,TP2,TP3,TP4,LED5,LED32,SW19,SW20,D19,D20,LED25,LED26,SW41,D41,LED53,SW21,SW42,SW43,SW44,D21,D42,D45,D46,LED27,LED54,LED55,LED56 >$B/cleanup.log
cp $B/s2.kicad_pcb $B/r.kicad_pcb
route() { bin/kpy tools/maze.py $B/r.kicad_pcb $B/r.kicad_pcb "$@"; }
# The sensor-to-driver links first (each a via straight through, front pad to
# back pad), then long or awkward runs, while the board is emptiest.
for i in 1 2 3 4; do route TP_S$i 0.25 TP1:S$i TP2:S$i; done
route VDD 0.3 TP2:5 J4:3                       # trackpoint 3.3 V (about 2 mA) from the OLED header
route TP_CLK 0.25 TP2:3 U2:12                  # trackpoint clock -> U2 pin 12 (GP9)
route TP_DATA 0.25 TP2:2 U2:11                 # trackpoint data  -> U2 pin 11 (GP8)
route GNDA 0.5 TP2:1 any                       # ground by track (the pad stays out of the pour)
if dual; then                                  # the same for the left trackpoint
  for i in 1 2 3 4; do route TP_S${i}_L 0.25 TP3:S$i TP4:S$i; done
  # The LED chain link its escape strip cut, before the wiring boxes in LED26.
  route Net-\(LED23-DOUT\) 0.25 LED23:2 LED26:4
  # Signals before power, the pin nearest the controller first.
  route TP_DATA_L 0.25 TP4:2 U1:11
  route TP_CLK_L 0.25 TP4:3 U1:12
  route VCC 0.3 TP4:5 J2:3
  route GND 0.5 TP4:1 any
fi
route data_r 0.25 J3:B U2:2                    # right TRRS data
route data 0.25 J1:B U1:2                      # left TRRS data
route VDD 0.3 J3:D U2:21                       # right TRRS power
route VCC 0.3 J1:D U1:21                       # left TRRS power
# Everything else DRC still reports missing.
bin/kpy tools/autoconnect.py $B/r.kicad_pcb
refill $B/r.kicad_pcb
cp $B/r.kicad_pcb $B/out.kicad_pcb
mapfile -t NETS < <(sort -u $B/affected.txt; printf '%s\n' TP_DATA TP_CLK TP_DATA_L TP_CLK_L VDD VCC data data_r)
while [ "$(bin/kpy tools/prune.py $B/out.kicad_pcb $B/out.kicad_pcb "${NETS[@]}" | tail -1)" != 0 ]; do :; done
# Finish: drop dead ends DRC finds, reconnect anything that opens, until clean.
for pass in 1 2 3 4 5; do
  bin/kcli pcb drc --refill-zones --save-board --format json -o $B/drc.json $B/out.kicad_pcb >/dev/null 2>&1 || true
  [ "$(bin/kpy tools/drop_dangling.py $B/out.kicad_pcb $B/drc.json | tail -1)" = 0 ] && \
    [ "$(python3 -c "import json;print(len([u for u in json.load(open('$B/drc.json')).get('unconnected_items',[]) if not all(i['description'].startswith('Zone') for i in u['items'])]))")" = 0 ] && break
  bin/kpy tools/autoconnect.py $B/out.kicad_pcb
done
bin/kpy tools/angle_marks.py $B/out.kicad_pcb pcb   # 15-degree marks in the thumb gaps (silkscreen)
bin/kcli pcb drc --refill-zones --save-board -o $B/drc.rpt $B/out.kicad_pcb >/dev/null 2>&1 || true
bin/kcli pcb drc --format json -o $B/drc.json $B/out.kicad_pcb >/dev/null 2>&1 || true
bin/kcli pcb drc --refill-zones --save-board --format json -o $B/drc_up.json $B/upstream.kicad_pcb >/dev/null 2>&1 || true
python3 tools/drcdiff.py $B/drc_up.json $B/drc.json
cp $B/out.kicad_pcb "$OUT/$NAME.kicad_pcb"

# Switch plates and bottom plate. Single: the left plate is the right-half design
# flipped, the right one also clears the trackpoint sensor. Dual: one design with
# the sensor opening, flipped for the left half.
PRO="pcb/corne choc plate.kicad_pro"
git show 59d1639:"pcb/corne choc plate.kicad_pcb" > $B/plate_up.kicad_pcb
bin/kpy tools/strip.py $B/plate_up.kicad_pcb $B/plate_up.kicad_pcb
if dual; then
  bin/kpy tools/plate.py $B/plate_up.kicad_pcb $B/out.kicad_pcb $B/plate_plain.kicad_pcb "$OUT/$NAME plate.kicad_pcb"
  PLATES=("$OUT/$NAME plate.kicad_pcb")
else
  bin/kpy tools/plate.py $B/plate_up.kicad_pcb $B/out.kicad_pcb "$OUT/$NAME plate.kicad_pcb" "$OUT/$NAME plate right.kicad_pcb"
  PLATES=("$OUT/$NAME plate.kicad_pcb" "$OUT/$NAME plate right.kicad_pcb")
fi
for p in "${PLATES[@]}"; do
  bin/kpy tools/angle_marks.py "$p" plate
  [ "$p" = "$PRO" ] || [ "${p%.kicad_pcb}.kicad_pro" = "$PRO" ] || cp "$PRO" "${p%.kicad_pcb}.kicad_pro"
  bin/kcli pcb drc --refill-zones --save-board -o "$B/$(basename "${p%.kicad_pcb}")_drc.rpt" "$p" >/dev/null 2>&1 || true
done
bin/kpy tools/bottom_plate.py $B/out.kicad_pcb $OUT/bottom.kicad_pcb
[ -f $OUT/bottom.kicad_pro ] || cp "$PRO" $OUT/bottom.kicad_pro
bin/kpy tools/printout.py $B/out.kicad_pcb $B/printout.svg
/nix/store/ii7wr6b6b8c5fq1ci26rw7amkb4apwm8-librsvg-2.62.3/bin/rsvg-convert -f pdf -o $PRINT.pdf $B/printout.svg
