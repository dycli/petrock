#!/usr/bin/env bash
# Rebuild the board from the upstream file with as little change to its copper
# as the layout allows, then make the plates and the printout:
#   1. place: every part goes where the layout puts it, dragging its copper;
#   2. fit: copper the new edge crowds is nudged in (tools/edge_fit.py);
#   3. trim: only copper off the board or in a clash upstream didn't have goes
#      (tools/trim.py), so cut wires keep their stubs;
#   4. route: what is open, around the surviving stock copper, which the router
#      may not rip up ($KEEP_IDS) unless a connection is boxed in by it; then dead
#      ends go and DRC is diffed with upstream's.
#   usage: build.sh [single|dual]
#   single: SK8707-01 trackpoint at the right outer thumb key (pcb/, printout.pdf)
#   dual:   trackpoints at both outer thumb keys (pcb/dual/, printout-dual.pdf)
set -euo pipefail
cd "$(dirname "$0")/.."
VARIANT=${1:-single}
case $VARIANT in
  single) B=build;      OUT=pcb;      NAME="petrock-41";      TPS=(right);      PRINT=printout ;;
  dual)   B=build/dual; OUT=pcb/dual; NAME="petrock-40";      TPS=(right left); PRINT=printout-dual ;;
  *) echo "unknown variant $VARIANT" >&2; exit 1 ;;
esac
dual() { [ "$VARIANT" = dual ]; }
mkdir -p $B $OUT
# The stock board without its lighting (tools/no_leds.py) is the base everything
# is measured against.
git show 59d1639:"pcb/corne choc.kicad_pcb" > $B/upstream.kicad_pcb
bin/kpy tools/no_leds.py $B/upstream.kicad_pcb $B/upstream.kicad_pcb
for b in upstream out; do git show 59d1639:"pcb/corne choc.kicad_pro" > $B/$b.kicad_pro; done   # DRC's rules
python3 tools/make_footprints.py
drc() { bin/kcli pcb drc --refill-zones --save-board --format json -o "$2" "$1" >/dev/null 2>&1 || true; }
open_count() { python3 -c "import json;print(len(json.load(open('$1')).get('unconnected_items',[])))"; }
drc $B/upstream.kicad_pcb $B/drc_up.json

# 1. Place.
export MOVED_OUT=$B/moved.txt NEW_EDGES=$B/new_edges.txt
rm -f $MOVED_OUT $NEW_EDGES
bin/kpy tools/pins.py $B/upstream.kicad_pcb $B/s.kicad_pcb
bin/kpy tools/stagger.py $B/s.kicad_pcb $B/s.kicad_pcb
bin/kpy tools/widen.py $B/s.kicad_pcb $B/s.kicad_pcb
bin/kpy tools/outline.py $B/s.kicad_pcb $B/s.kicad_pcb
bin/kpy tools/inner_strip.py $B/s.kicad_pcb $B/s.kicad_pcb
bin/kpy tools/split_thumbs.py $B/s.kicad_pcb $B/s.kicad_pcb
for h in "${TPS[@]}"; do bin/kpy tools/outer_thumb.py $B/s.kicad_pcb $B/s.kicad_pcb $h; done
bin/kpy tools/strip.py $B/s.kicad_pcb $B/s.kicad_pcb
bin/kpy tools/standoffs.py $B/s.kicad_pcb $B/s.kicad_pcb

# 2. Fit, 3. trim.
cp $B/s.kicad_pcb $B/out.kicad_pcb
bin/kpy tools/edge_fit.py $B/out.kicad_pcb
for pass in 1 2 3 4; do
  drc $B/out.kicad_pcb $B/drc.json
  [ "$(bin/kpy tools/trim.py $B/out.kicad_pcb $B/drc.json $B/upstream.kicad_pcb $B/drc_up.json | tail -1)" = 0 ] && break
done
bin/kpy tools/ids.py $B/out.kicad_pcb | grep -E '^[0-9a-f-]{36}$' > $B/keep.txt
export KEEP_IDS=$B/keep.txt

# 4. Route. The sensor-to-driver links first (tools/tp_links.py: front out to a
# via beside the driver, back across to its pad), while the board is emptiest.
route() { bin/kpy tools/maze.py $B/out.kicad_pcb $B/out.kicad_pcb "$@"; }
links() {
  local vias
  vias=$(bin/kpy tools/tp_links.py $B/out.kicad_pcb $1 $2 | grep '^S')
  while read -r pad x y; do
    # (one that doesn't fit is left to the general router below)
    route TP_S${pad#S}$3 0.25 $1:$pad "$x,$y,F" || true
    route TP_S${pad#S}$3 0.25 $2:$pad "$x,$y,B" || true
  done <<<"$vias"
}
links TP1 TP2 ""
dual && links TP3 TP4 _L
connect() {
  bin/kpy tools/autoconnect.py $B/out.kicad_pcb
  # Strip every dead end DRC finds (each removal can expose the next).
  for strip in 1 2 3 4 5 6 7 8 9 10; do
    drc $B/out.kicad_pcb $B/drc.json
    [ "$(bin/kpy tools/drop_dangling.py $B/out.kicad_pcb $B/drc.json | tail -1)" = 0 ] && break
  done
  return 0
}
for pass in 1 2 3 4; do
  connect
  [ "$(open_count $B/drc.json)" = 0 ] && break
done
# Last resort for a connection boxed in by stock copper: stock may be ripped up too.
unset KEEP_IDS
for pass in 1 2 3 4; do
  [ "$(open_count $B/drc.json)" = 0 ] && break
  connect
done
bin/kpy tools/solid_starved.py $B/out.kicad_pcb $B/drc.json
bin/kpy tools/logo.py $B/out.kicad_pcb pcb             # the logo on the top silkscreen
bin/kpy tools/quiet_silk.py $B/out.kicad_pcb            # no outlines round the jack, reset and OLED header
sed -i 's/(copper_finish "[^"]*")/(copper_finish "ENIG")/' $B/out.kicad_pcb   # as ordered (README)
bin/kcli pcb drc --refill-zones --save-board -o $B/drc.rpt $B/out.kicad_pcb >/dev/null 2>&1 || true
drc $B/out.kicad_pcb $B/drc.json
python3 tools/drcdiff.py $B/drc_up.json $B/drc.json
bin/kpy tools/reuse.py $B/upstream.kicad_pcb $B/out.kicad_pcb
cp $B/out.kicad_pcb "$OUT/$NAME.kicad_pcb"

tools/plates.sh $VARIANT
