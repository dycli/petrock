#!/usr/bin/env bash
# Switch plates, bottom plate and printout for a built board (tools/build.sh).
#   usage: plates.sh [single|dual]
set -euo pipefail
cd "$(dirname "$0")/.."
VARIANT=${1:-single}
case $VARIANT in
  single) B=build;      OUT=pcb;      NAME="petrock-41";      PRINT=printout ;;
  dual)   B=build/dual; OUT=pcb/dual; NAME="petrock-40";      PRINT=printout-dual ;;
  *) echo "unknown variant $VARIANT" >&2; exit 1 ;;
esac
dual() { [ "$VARIANT" = dual ]; }

# Switch plates and bottom plate. Single: the left plate is the right-half design
# flipped, the right one also clears the trackpoint sensor. Dual: one design with
# the sensor opening, flipped for the left half.
PRO="pcb/petrock-41 plate.kicad_pro"
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
  bin/kpy tools/logo.py "$p" plate
  [ "$p" = "$PRO" ] || [ "${p%.kicad_pcb}.kicad_pro" = "$PRO" ] || cp "$PRO" "${p%.kicad_pcb}.kicad_pro"
  bin/kcli pcb drc --refill-zones --save-board -o "$B/$(basename "${p%.kicad_pcb}")_drc.rpt" "$p" >/dev/null 2>&1 || true
done
bin/kpy tools/bottom_plate.py $B/out.kicad_pcb $OUT/bottom.kicad_pcb
[ -f $OUT/bottom.kicad_pro ] || cp "$PRO" $OUT/bottom.kicad_pro
bin/kpy tools/printout.py $B/out.kicad_pcb $B/printout.svg
/nix/store/ii7wr6b6b8c5fq1ci26rw7amkb4apwm8-librsvg-2.62.3/bin/rsvg-convert -f pdf -o $PRINT.pdf $B/printout.svg
