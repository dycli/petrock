#!/usr/bin/env bash
# Export JLCPCB-style Gerber + drill zips for each board.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p fab
export_board() {  # name board
  local d; d=$(mktemp -d)
  bin/kcli pcb export gerbers --no-x2 --subtract-soldermask \
    --layers F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
    -o "$d/" "$2" >/dev/null
  bin/kcli pcb export drill --format excellon --drill-origin absolute --excellon-units mm \
    --generate-map --map-format gerberx2 -o "$d/" "$2" >/dev/null
  (cd "$d" && zip -q -r - .) > "fab/$1.zip"
  rm -rf "$d"
  echo "fab/$1.zip: $(unzip -l "fab/$1.zip" | tail -1)"
}
export_board pcb "pcb/corne choc.kicad_pcb"
export_board plate "pcb/corne choc plate.kicad_pcb"     # upstream plate, unchanged
