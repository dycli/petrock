#!/usr/bin/env bash
# Export JLCPCB-style Gerber + drill zips for each board, and JLC's assembly files.
#   usage: fab.sh [single|dual]   (single -> fab/, dual -> fab/dual/)
set -euo pipefail
cd "$(dirname "$0")/.."
VARIANT=${1:-single}
case $VARIANT in
  single) F=fab;      P=pcb;      NAME="petrock-41" ;;
  dual)   F=fab/dual; P=pcb/dual; NAME="petrock-40" ;;
  *) echo "unknown variant $VARIANT" >&2; exit 1 ;;
esac
mkdir -p $F
export_board() {  # name board
  local d; d=$(mktemp -d)
  bin/kcli pcb export gerbers --no-x2 --subtract-soldermask \
    --layers F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
    -o "$d/" "$2" >/dev/null
  bin/kcli pcb export drill --format excellon --drill-origin absolute --excellon-units mm --excellon-separate-th \
    --generate-map --map-format gerberx2 -o "$d/" "$2" >/dev/null
  (cd "$d" && zip -q -r - .) > "$F/$1.zip"
  rm -rf "$d"
  echo "$F/$1.zip: $(unzip -l "$F/$1.zip" | tail -1)"
}
export_board pcb "$P/$NAME.kicad_pcb"
if [ "$VARIANT" = dual ]; then
  export_board plate "$P/$NAME plate.kicad_pcb"                 # one design, both halves (flip it for the left)
else
  export_board plate-left "$P/$NAME plate.kicad_pcb"            # drawn as a right half; flip it
  export_board plate-right "$P/$NAME plate right.kicad_pcb"     # clears the trackpoint sensor
fi
export_board bottom "$P/bottom.kicad_pcb"
bin/kpy tools/jlc.py "$P/$NAME.kicad_pcb" $F            # assembly BOM + placement for JLC's back-side SMD parts
