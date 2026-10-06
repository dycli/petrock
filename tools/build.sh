#!/usr/bin/env bash
# Rebuild the board from the upstream file, then make the plates and the printout:
#   1. place: every part goes where the layout puts it;
#   2. route: every wire drawn by rule from the key positions (tools/route.py),
#      ground poured on both sides and stitched (tools/stitch.py);
#   3. check: the build fails unless DRC finds nothing but the stock footprints'
#      library notices and every connection is made.
#   usage: build.sh [single|dual|none]
#   single: SK8707-01 trackpoint at the right outer thumb key (pcb/, printout.pdf)
#   dual:   trackpoints at both outer thumb keys (pcb/dual/, printout-dual.pdf)
#   none:   no trackpoints, a key at both outer thumbs (pcb/none/, printout-none.pdf)
set -euo pipefail
cd "$(dirname "$0")/.."
VARIANT=${1:-single}
case $VARIANT in
  single) B=build;      OUT=pcb;      NAME="petrock-41";      TPS=(right);      PRINT=printout ;;
  dual)   B=build/dual; OUT=pcb/dual; NAME="petrock-40";      TPS=(right left); PRINT=printout-dual ;;
  none)   B=build/none; OUT=pcb/none; NAME="petrock-42";      TPS=();           PRINT=printout-none ;;
  *) echo "unknown variant $VARIANT" >&2; exit 1 ;;
esac
dual() { [ "$VARIANT" = dual ]; }
mkdir -p $B $OUT
# The stock board without its lighting (tools/no_leds.py) is where placement starts.
git show 59d1639:"pcb/corne choc.kicad_pcb" > $B/upstream.kicad_pcb
bin/kpy tools/no_leds.py $B/upstream.kicad_pcb $B/upstream.kicad_pcb
for b in upstream out; do git show 59d1639:"pcb/corne choc.kicad_pro" > $B/$b.kicad_pro; done   # DRC's rules
python3 tools/make_footprints.py
drc() { bin/kcli pcb drc --refill-zones --save-board --format json -o "$2" "$1" >/dev/null 2>&1 || true; }

# 1. Place.
export MOVED_OUT=$B/moved.txt NEW_EDGES=$B/new_edges.txt
rm -f $MOVED_OUT $NEW_EDGES
bin/kpy tools/pins.py $B/upstream.kicad_pcb $B/s.kicad_pcb
bin/kpy tools/stagger.py $B/s.kicad_pcb $B/s.kicad_pcb
bin/kpy tools/widen.py $B/s.kicad_pcb $B/s.kicad_pcb
bin/kpy tools/outline.py $B/s.kicad_pcb $B/s.kicad_pcb
bin/kpy tools/inner_strip.py $B/s.kicad_pcb $B/s.kicad_pcb
bin/kpy tools/split_thumbs.py $B/s.kicad_pcb $B/s.kicad_pcb
for h in ${TPS[@]+"${TPS[@]}"}; do bin/kpy tools/outer_thumb.py $B/s.kicad_pcb $B/s.kicad_pcb $h; done
bin/kpy tools/strip.py $B/s.kicad_pcb $B/s.kicad_pcb
bin/kpy tools/standoffs.py $B/s.kicad_pcb $B/s.kicad_pcb

# 2. Route by rule, then pour and stitch the ground.
cp $B/s.kicad_pcb $B/out.kicad_pcb
bin/kpy tools/clear_copper.py $B/out.kicad_pcb
bin/kpy tools/route.py $B/out.kicad_pcb $B/out.kicad_pcb
bin/kpy tools/stitch.py $B/out.kicad_pcb >/dev/null
bin/kpy tools/logo.py $B/out.kicad_pcb pcb             # the logo on the top silkscreen
bin/kpy tools/quiet_silk.py $B/out.kicad_pcb            # no outlines round the jack, reset and OLED header
# The commit this board is built from, printed on its back.
git diff --quiet HEAD -- tools lib || { echo "commit the scripts first: the stamp must name the sources" >&2; exit 1; }
bin/kpy tools/stamp.py $B/out.kicad_pcb "$(git rev-parse --short HEAD)"
sed -i 's/(copper_finish "[^"]*")/(copper_finish "HASL")/' $B/out.kicad_pcb   # as ordered (README)
bin/kcli pcb drc --refill-zones --save-board -o $B/drc.rpt $B/out.kicad_pcb >/dev/null 2>&1 || true
drc $B/out.kicad_pcb $B/drc.json
# 3. Check.
python3 - $B/drc.json <<'PY'
import collections, json, sys
d = json.load(open(sys.argv[1]))
bad = [v for v in d["violations"] if v["type"] != "lib_footprint_issues"]
for v in bad:
    print(v["type"], v["description"], [i["description"] for i in v["items"]], file=sys.stderr)
print("DRC:", dict(collections.Counter(v["type"] for v in d["violations"])), "unconnected:", len(d["unconnected_items"]))
sys.exit(1 if bad or d["unconnected_items"] else 0)
PY
cp $B/out.kicad_pcb "$OUT/$NAME.kicad_pcb"

tools/plates.sh $VARIANT
