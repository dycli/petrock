#!/usr/bin/env bash
# Render the demo images in demo/ from the last build (build/out.kicad_pcb and the plates).
# Fetches the switch, keycap and part 3D models (marbastlib, foostan/kbd, KLP Lame) into build/models.
set -euo pipefail
cd "$(dirname "$0")/.."
B=build
K=.nix/kicad-full/bin/kicad-cli      # full KiCad, with the 3D renderer
P3D=$PWD/.nix/packages3d/share/kicad/3dmodels
RSVG=.nix/librsvg/bin/rsvg-convert
PIL=.nix/pillow/lib/python3.14/site-packages

mkdir -p $B/models
[ -d $B/models/marbastlib ] || git clone -q --depth 1 https://github.com/ebastler/marbastlib $B/models/marbastlib
[ -d $B/models/kbd ] || git clone -q --depth 1 https://github.com/foostan/kbd $B/models/kbd
mkdir -p $B/models/klp                                     # KLP Lame keycaps (braindefender)
for k in Normal Normal_Homing Thumb; do
  f=$B/models/klp/Choc_Stem_Choc_Size_$k.step
  [ -s $f ] || curl -sfL -o $f "https://raw.githubusercontent.com/braindefender/KLP-Lame-Keycaps/master/STEP/Choc%20Stem%20%2B%20Choc%20Size/Choc_Stem_Choc_Size_$k.step"
  # The models come satin grey; render them as white caps.
  sed -i "s/COLOUR_RGB('[^']*',[^)]*)/COLOUR_RGB('White keycap',0.94,0.94,0.92)/" $f
done
python3 tools/demo_models.py demo/models

bin/kpy tools/demo_board.py $B/out.kicad_pcb $B/demo.kicad_pcb "$PWD/$B/models/marbastlib" "$PWD/$B/models/kbd" $P3D "$PWD/demo/models" "$PWD/$B/models/klp" >/dev/null
bin/kpy tools/demo_board.py $B/out.kicad_pcb $B/demo-bare.kicad_pcb "$PWD/$B/models/marbastlib" "$PWD/$B/models/kbd" $P3D "$PWD/demo/models" "$PWD/$B/models/klp" bare >/dev/null
# Plates in black, like the PCB. Pure black: the plates render as STEP models,
# which take more light than the board itself, so this matches its #141414 mask.
for p in "petrock-41 plate right:demo-plate" "petrock-41 plate:demo-plate-plain" "bottom:demo-bottom"; do
  cp "pcb/${p%%:*}.kicad_pcb" "$B/${p##*:}.kicad_pcb"
  python3 - "$B/${p##*:}.kicad_pcb" <<'EOF'
import re, sys
t = open(sys.argv[1]).read()
for layer in ("F.Mask", "B.Mask"):
    t = re.sub(r'(\(layer "' + re.escape(layer) + r'"\s*\(type "[^"]*"\))', lambda m: m.group(1) + ' (color "#000000FF")', t, count=1)
# Dark core too: the STEP export used for the assembled render colours the body by it.
t = re.sub(r'(\(layer "dielectric 1"\s*\(type "[^"]*"\))(\s*\(color "[^"]*"\))?', lambda m: m.group(1) + ' (color "#000000FF")', t, count=1)
open(sys.argv[1], "w").write(t)
EOF
done
# The assembled board: both switch plates in place, the left one mirrored.
bin/kpy tools/flip_plate.py $B/demo-plate-plain.kicad_pcb $B/demo-plate-left.kicad_pcb >/dev/null
for n in demo-plate demo-plate-left; do
  $K pcb export step --board-only --include-silkscreen --user-origin 0x0mm -f -o $B/$n.step $B/$n.kicad_pcb >/dev/null 2>&1
done
bin/kpy tools/demo_plates.py $B/demo.kicad_pcb "$PWD/$B/demo-plate.step" "$PWD/$B/demo-plate-left.step" $B/demo-assembled.kicad_pcb >/dev/null
# And without the OLED modules (they're optional).
bin/kpy tools/demo_board.py $B/out.kicad_pcb $B/demo-nooled.kicad_pcb "$PWD/$B/models/marbastlib" "$PWD/$B/models/kbd" $P3D "$PWD/demo/models" "$PWD/$B/models/klp" nooled >/dev/null
bin/kpy tools/demo_plates.py $B/demo-nooled.kicad_pcb "$PWD/$B/demo-plate.step" "$PWD/$B/demo-plate-left.step" $B/demo-nooled-assembled.kicad_pcb >/dev/null

R() { $K pcb render --quality high --background opaque --use-board-stackup-colors "$@" >/dev/null 2>&1; }
R -o demo/01-top.png -w 2600 -h 1300 --side top --zoom 1.65 $B/demo.kicad_pcb
R -o demo/02-angled.png -w 2600 -h 1500 --side top --perspective --rotate '-35,0,0' --zoom 1.5 --floor $B/demo.kicad_pcb
R -o demo/04-bare-front.png -w 2600 -h 1300 --side top --zoom 1.65 $B/demo-bare.kicad_pcb
R -o demo/05-bare-back.png -w 2600 -h 1300 --side bottom --zoom 1.65 $B/demo-bare.kicad_pcb
R -o demo/06-bottom-angled.png -w 2600 -h 1500 --side bottom --perspective --rotate '35,0,0' --zoom 1.5 --floor $B/demo.kicad_pcb
R -o demo/07-switch-plate.png -w 1800 -h 1200 --side top --zoom 1.3 $B/demo-plate.kicad_pcb
R -o demo/08-bottom-plate.png -w 2600 -h 1300 --side top --zoom 1.65 $B/demo-bottom.kicad_pcb
R -o demo/12-assembled.png -w 2600 -h 1500 --side top --perspective --rotate '-35,0,0' --zoom 1.5 --floor $B/demo-assembled.kicad_pcb
R -o demo/14-assembled-top.png -w 2600 -h 1300 --side top --zoom 1.65 $B/demo-assembled.kicad_pcb
R -o demo/15-no-oled-angled.png -w 2600 -h 1500 --side top --perspective --rotate '-35,0,0' --zoom 1.5 --floor $B/demo-nooled-assembled.kicad_pcb
R -o demo/16-no-oled-top.png -w 2600 -h 1300 --side top --zoom 1.65 $B/demo-nooled-assembled.kicad_pcb
# Close-ups are crops of one big angled render.
R -o $B/big-angled.png -w 6400 -h 3700 --side top --perspective --rotate '-35,0,0' --zoom 1.5 $B/demo.kicad_pcb
R -o $B/big-assembled.png -w 6400 -h 3700 --side top --perspective --rotate '-35,0,0' --zoom 1.5 $B/demo-assembled.kicad_pcb
PYTHONPATH=$PIL .nix/python/bin/python3.14 - $B/big-angled.png $B/big-assembled.png <<'EOF'
import sys
from PIL import Image
for src, name, box in ((1, "03-trackpoint-closeup", (0.50, 0.44, 0.78, 0.72)),
                       (1, "09-left-thumbs-closeup", (0.22, 0.44, 0.50, 0.72)),
                       (1, "10-jacks-controllers-closeup", (0.38, 0.28, 0.62, 0.52)),
                       (2, "13-assembled-trackpoint", (0.50, 0.44, 0.78, 0.72))):
    im = Image.open(sys.argv[src]); W, H = im.size
    im.crop(tuple(int(f * d) for f, d in zip(box, (W, H, W, H)))).save(f"demo/{name}.png")
EOF
bin/kpy tools/compare.py $B/upstream.kicad_pcb $B/out.kicad_pcb $B/compare.svg >/dev/null
$RSVG $B/compare.svg -o demo/11-before-after.png
ls demo/*.png
