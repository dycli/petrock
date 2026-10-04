"""A self-contained web page with the assembled keyboard in 3D: drag to turn,
scroll to zoom. The GLB KiCad exports (tools/demo.sh) carries every STEP model;
the parts drawn as simple VRML stand-ins (tools/demo_models.py: controllers,
trackpoint sensors and nubs, drivers, standoffs), which KiCad's GLB export
leaves out, are rebuilt here as three.js boxes and prisms at their footprints.

usage: web3d.py BOARD GLB OUT.html   (BOARD: the assembled render board the GLB came from)
"""
import base64
import json
import math
import os
import sys

import pcbnew

NAVY, OLIVE, GOLD = (0.03, 0.12, 0.26), (0.27, 0.27, 0.17), (0.82, 0.73, 0.45)
BLACK, STEEL, HOLE, RED = (0.06, 0.06, 0.06), (0.75, 0.75, 0.77), (0.02, 0.02, 0.02), (0.80, 0.08, 0.08)
PCB_T, GAP = 1.6, 3.0


# Shapes in a footprint's frame, mm: x right, y down (as the footprint), z up from
# the board's top (negative: below its underside, under a part on the back).
def box(cx, cy, w, d, z0, h, rgb):
    return {"t": "box", "c": [cx, cy, z0 + h / 2], "s": [w, d, h], "rgb": rgb}


def prism(cx, cy, r, z0, h, rgb, n=40):
    return {"t": "cyl", "c": [cx, cy, z0 + h / 2], "r": r, "h": h, "n": n, "rgb": rgb}


def sensor():
    top = 0.8
    out = [box(0, (10.84 - 7.45) / 2, 13.2, 18.29, 0, 0.8, NAVY), prism(0, 0, 5.05, top, 0.02, OLIVE)]
    for x in (-4.75, 4.75):
        for y in (-4.75, 4.75):
            out += [prism(x, y, 1.4, top, 0.03, GOLD), prism(x, y, 0.8, top, 0.04, HOLE)]
    out += [box(x, 10.64, w, 2.0, top, 0.03, GOLD) for x, w in ((-3.75, 1.6), (-1.25, 1.6), (1.25, 2.0), (3.75, 2.0))]
    out += [box(x, 9.34, 1.6, 3.2, top, 0.03, GOLD) for x in (-6.5, 6.5)]
    out += [box(0, 0, 2.4, 2.4, top, 2.0, (0.86, 0.85, 0.78)), prism(0, 0, 3.5, 0.8 + 2.4 - 0.6, 2.6, RED)]
    return out


def controller():
    z0, t = 2.5, 1.6
    out = [box(0, -1.04, 17.9, 31.7, z0, t, BLACK), box(0, -16.9, 8.9, 3.2, z0 - 3.2 + t, 3.2, STEEL)]
    for x in (-7.61, 7.61):
        out.append(box(x, -0.51, 2.5, 30.5, 0, z0, (0.05, 0.05, 0.05)))
        for i in range(12):
            y = -14.48 + 2.54 * i
            out += [prism(x, y, 0.85, z0 + t, 0.03, GOLD), prism(x, y, 0.5, z0 + t, 0.04, HOLE)]
    return out


def driver():         # on the back, under the board
    return [box(0, 0, 23.0, 14.5, -PCB_T - 1.0, 1.0, NAVY)]


def standoff():
    return [prism(0, 0, 1.85, -PCB_T - GAP, GAP, (0.08, 0.08, 0.08), n=6)]


def main(board_path, glb, out):
    board = pcbnew.LoadBoard(board_path)
    kinds = {"sensor": sensor(), "controller": controller(), "driver": driver(), "standoff": standoff()}
    placed = []
    for f in board.GetFootprints():
        kind = ("sensor" if f.GetValue() == "SK8707-01 sensor" else "driver" if f.GetValue() == "SK8707-01 driver"
                else "controller" if f.GetReference() in ("U1", "U2")
                else "standoff" if f.GetFPIDAsString() == "holykeebs:M2_SPACER" else None)
        if kind:
            placed.append({"k": kind, "x": pcbnew.ToMM(f.GetPosition().x), "y": pcbnew.ToMM(f.GetPosition().y),
                           "a": f.GetOrientationDegrees(), "flip": f.IsFlipped()})
    data = base64.b64encode(open(glb, "rb").read()).decode()
    html = PAGE.replace("@@GLB@@", data).replace("@@KINDS@@", json.dumps(kinds)).replace("@@PLACED@@", json.dumps(placed)) \
               .replace("@@PCB_T@@", str(PCB_T))
    open(out, "w").write(html)
    print(f"{out}: {len(html) / 1e6:.1f} MB, {len(placed)} stand-in parts")


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Arc-40</title>
<style>html,body{margin:0;height:100%;background:#2b2d33;color:#ddd;font:14px system-ui,sans-serif;overflow:hidden}
#hint{position:fixed;left:16px;bottom:12px;opacity:.6}#title{position:fixed;left:16px;top:12px;font-size:20px;letter-spacing:.08em}</style>
<script type="importmap">{"imports":{"three":"https://unpkg.com/three@0.160.0/build/three.module.js","three/addons/":"https://unpkg.com/three@0.160.0/examples/jsm/"}}</script>
</head><body><div id="title">ARC-40</div><div id="hint">drag to turn &middot; right-drag to pan &middot; scroll to zoom</div>
<script type="module">
import * as THREE from "three";
import {GLTFLoader} from "three/addons/loaders/GLTFLoader.js";
import {OrbitControls} from "three/addons/controls/OrbitControls.js";
import {RoomEnvironment} from "three/addons/environments/RoomEnvironment.js";
const renderer = new THREE.WebGLRenderer({antialias: true});
renderer.setPixelRatio(devicePixelRatio); renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color(0x2b2d33);
const pmrem = new THREE.PMREMGenerator(renderer); scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(0.1, 0.4, 0.25); sun.castShadow = true; scene.add(sun);
const camera = new THREE.PerspectiveCamera(35, innerWidth / innerHeight, 0.001, 10);
const controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping = true;
const kit = new THREE.Group(); scene.add(kit);
const PCB_T = @@PCB_T@@ / 1000;
// KiCad's GLB: metres, KiCad x -> x, height -> y, KiCad y -> z; footprint angle turns about +y.
const KINDS = @@KINDS@@, PLACED = @@PLACED@@;
const mats = {};
function mat(rgb) { const k = rgb.join(); return mats[k] ||= new THREE.MeshStandardMaterial({color: new THREE.Color().setRGB(...rgb, THREE.SRGBColorSpace), roughness: 0.55, metalness: rgb[0] > 0.7 && rgb[2] < 0.5 ? 0.6 : 0.05}); }
for (const p of PLACED) {
  const g = new THREE.Group();
  for (const s of KINDS[p.k]) {
    const geo = s.t === "box" ? new THREE.BoxGeometry(s.s[0] / 1000, s.s[2] / 1000, s.s[1] / 1000)
                              : new THREE.CylinderGeometry(s.r / 1000, s.r / 1000, s.h / 1000, s.n);
    const m = new THREE.Mesh(geo, mat(s.rgb)); m.castShadow = m.receiveShadow = true;
    m.position.set(s.c[0] / 1000, s.c[2] / 1000, s.c[1] / 1000); g.add(m);
  }
  if (p.flip && p.k === "driver") g.scale.x = -1;
  g.rotation.y = p.a * Math.PI / 180;
  g.position.set(p.x / 1000, PCB_T, p.y / 1000);
  kit.add(g);
}
const bytes = Uint8Array.from(atob("@@GLB@@"), c => c.charCodeAt(0));
new GLTFLoader().parse(bytes.buffer, "", gltf => {
  gltf.scene.traverse(o => { if (o.isMesh) { o.castShadow = o.receiveShadow = true; } });
  kit.add(gltf.scene);
  const box = new THREE.Box3().setFromObject(kit), c = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3());
  kit.position.sub(c);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShadowMaterial({opacity: 0.35}));
  ground.rotation.x = -Math.PI / 2; ground.position.y = -size.y / 2 - 0.0015; ground.receiveShadow = true; scene.add(ground);
  sun.shadow.camera.left = sun.shadow.camera.bottom = -0.25; sun.shadow.camera.right = sun.shadow.camera.top = 0.25; sun.shadow.mapSize.set(4096, 4096);
  camera.position.set(0, size.x * 0.75, size.x * 0.75); controls.target.set(0, 0, 0); controls.update();
});
addEventListener("resize", () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });
(function loop() { requestAnimationFrame(loop); controls.update(); renderer.render(scene, camera); })();
</script></body></html>
"""

if __name__ == "__main__":
    main(*sys.argv[1:4])
    sys.stdout.flush()
    os._exit(0)
