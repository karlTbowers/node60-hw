// Node60 hero render: the current enclosure version with the board as KiCad exports it, in a
// studio scene. Loaded by scripts/render-hero.mjs, which writes build/hero.json (the current
// version's geometry from enclosure-versions.json plus the KiCad outline) and the two GLBs.
// Geometry follows src/mockups/node60-enclosure.html: x east, y north (outside frame, mm),
// scene x = x - OX/2, scene z = OY/2 - y, scene y = height above the floor's underside.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const q = new URLSearchParams(location.search);
const VIEW = q.get('view') || 'assembled', W_PX = +q.get('w') || 1600, H_PX = +q.get('h') || 900;
const EXPLODED = VIEW === 'exploded';
const DATA = await (await fetch('build/hero.json')).json();
const G = DATA.geometry, K = DATA.kicad;

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W_PX, H_PX);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.92;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
// Reflections: a light grey studio with softboxes (overhead, strips left and behind, a low fill).
{
  const studio = new THREE.Scene();
  studio.add(new THREE.Mesh(new THREE.BoxGeometry(100, 100, 100),
    new THREE.MeshBasicMaterial({ color: 0x8a9096, side: THREE.BackSide })));
  const box = (w, h, x, y, z, ry, rx, i) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(i, i, i), side: THREE.DoubleSide }));
    m.position.set(x, y, z); m.rotation.set(rx, ry, 0); studio.add(m);
  };
  box(40, 24, 0, 49, -10, 0, Math.PI / 2, 2.6);      // overhead, toward the back
  box(8, 60, -49, 10, 10, Math.PI / 2, 0, 3.5);      // strip, left
  box(60, 6, 0, 20, -49, 0, 0, 3.0);                 // strip, behind
  box(50, 14, 20, -8, 49, 0, 0, 1.4);                // low fill, front
  box(10, 40, 49, 15, 0, -Math.PI / 2, 0, 2.0);      // right
  scene.environment = pmrem.fromScene(studio, 0.02).texture;
  scene.environmentIntensity = 1.0;
}

// Studio backdrop: a light, cool grey sweep, brightest behind the enclosure (the case is black).
{
  const c = document.createElement('canvas'); c.width = 512; c.height = 512;
  const x = c.getContext('2d');
  const lin = x.createLinearGradient(0, 0, 0, 512);
  lin.addColorStop(0, '#dfe4e9'); lin.addColorStop(0.55, '#e9edf0'); lin.addColorStop(1, '#cfd5db');
  x.fillStyle = lin; x.fillRect(0, 0, 512, 512);
  const rad = x.createRadialGradient(256, 240, 10, 256, 240, 300);
  rad.addColorStop(0, 'rgba(255,255,255,0.75)'); rad.addColorStop(1, 'rgba(255,255,255,0)');
  x.fillStyle = rad; x.fillRect(0, 0, 512, 512);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  scene.background = t;
}

// Lights: a soft key from the front left, a cool rim from behind, the room environment for reflections.
const key = new THREE.DirectionalLight(0xfff4e6, 1.9);
key.position.set(-260, 420, 300);
key.castShadow = true;
key.shadow.mapSize.set(8192, 8192);
key.shadow.camera.left = -260; key.shadow.camera.right = 260;
key.shadow.camera.top = 260; key.shadow.camera.bottom = -260;
key.shadow.camera.near = 10; key.shadow.camera.far = 1500;
key.shadow.bias = -0.0002; key.shadow.normalBias = 0.25; key.shadow.radius = 6;
scene.add(key);
const rim = new THREE.DirectionalLight(0xbcd4ff, 1.6); rim.position.set(300, 260, -380); scene.add(rim);
const fill = new THREE.DirectionalLight(0xffffff, 0.35); fill.position.set(320, 120, 260); scene.add(fill);

// Ground: shadow only, over the backdrop.
const ground = new THREE.Mesh(new THREE.PlaneGeometry(4000, 4000), new THREE.ShadowMaterial({ opacity: 0.3 }));
ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; scene.add(ground);
{ // a soft contact shadow directly under the case
  const c = document.createElement('canvas'); c.width = 512; c.height = 256;
  const x = c.getContext('2d'); x.filter = 'blur(28px)'; x.fillStyle = 'rgba(20,28,36,0.6)';
  x.fillRect(70, 60, 372, 136);
  const t = new THREE.CanvasTexture(c);
  const m = new THREE.Mesh(new THREE.PlaneGeometry(G.outside.x * 1.45, G.outside.y * 1.9),
    new THREE.MeshBasicMaterial({ map: t, transparent: true, depthWrite: false }));
  m.rotation.x = -Math.PI / 2; m.position.y = 0.05; scene.add(m);
}

// Materials
const alu = new THREE.MeshPhysicalMaterial({ color: 0x1c1e21, metalness: 0.45, roughness: 0.52 });   // black anodized, satin
const steel = new THREE.MeshStandardMaterial({ color: 0x9aa0a6, metalness: 1, roughness: 0.3 });
const copper = new THREE.MeshPhysicalMaterial({ color: 0xd9825a, metalness: 1, roughness: 0.22, clearcoat: 0.3 });
const cableMat = (c) => new THREE.MeshPhysicalMaterial({ color: c, roughness: 0.5, metalness: 0, clearcoat: 0.25, clearcoatRoughness: 0.5 });

const OX = G.outside.x, OY = G.outside.y, W = G.wall, LT = G.lid_thickness ?? W, B = G.board;
const REC = G.parts.receptacle, TOP = G.outside.z, CONTACT = REC.contact_z;
const HOOD = Math.max(TOP, ...G.raised.map(r => r.z));
const P = (x, y) => [x - OX / 2, OY / 2 - y];
const shade = (o) => o.traverse(m => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; } });
const span = (x0, x1, y0, y1, z0, z1, m, r = 0.6) => {
  const [a, b] = P((x0 + x1) / 2, (y0 + y1) / 2), w = Math.abs(x1 - x0), d = Math.abs(y1 - y0), h = z1 - z0;
  const rr = Math.min(r, w / 2 - 0.01, d / 2 - 0.01, h / 2 - 0.01);
  const g = rr > 0.05 ? new RoundedBoxGeometry(w, h, d, 3, rr) : new THREE.BoxGeometry(w, h, d);
  const mesh = new THREE.Mesh(g, m); mesh.position.set(a, (z0 + z1) / 2, b); return mesh;
};
const roundRect = (p, x0, y0, x1, y1, r) => {
  p.moveTo(x0 + r, y0); p.lineTo(x1 - r, y0); p.quadraticCurveTo(x1, y0, x1, y0 + r);
  p.lineTo(x1, y1 - r); p.quadraticCurveTo(x1, y1, x1 - r, y1); p.lineTo(x0 + r, y1);
  p.quadraticCurveTo(x0, y1, x0, y1 - r); p.lineTo(x0, y0 + r); p.quadraticCurveTo(x0, y0, x0 + r, y0);
};
const EXTRUDE = { depth: W - 0.8, bevelEnabled: true, bevelThickness: 0.4, bevelSize: 0.4, bevelSegments: 2, curveSegments: 24 };

// ---- Body: floor and walls (up to the lid's underside), headers' cutouts -------------------------
const xs = [...new Set([0, OX, ...G.raised.flatMap(r => [r.x0, r.x1])])].sort((a, b) => a - b);
const ys = [...new Set([0, OY, ...G.raised.flatMap(r => [r.y0, r.y1])])].sort((a, b) => a - b);
const raisedAt = (x, y) => G.raised.some(r => x > r.x0 && x < r.x1 && y > r.y0 && y < r.y1);
const wallTop = (face, u) => (raisedAt(...{ front: [u, 0.01], back: [OX - u, OY - 0.01], left: [0.01, OY - u],
                                            right: [OX - 0.01, u] }[face]) ? HOOD : TOP) - LT;
// Header cutouts as the dimensioned drawings cut them (scripts/enclosure_drawing.py, outline()):
// keyed slots around the header's shroud, its two flange screw holes beside them.
function outline(t) {
  const hw = t.width / 2, ht = t.tab / 2, top = t.near, full = top - t.full, total = top - t.total;
  const r = t.corner, small = t.small_corner ?? 0.8, narrow = t.tab < t.width;
  const pts = [[-hw, top], [hw, top], [hw, full], [ht, full], [ht, total], [-ht, total], [-ht, full], [-hw, full]];
  const radii = [r, r, narrow ? r : small, small, narrow ? small : r, narrow ? small : r, small, narrow ? r : small];
  return [pts, radii];
}
function filleted(p, pts, radii) {   // a polygon with each corner rounded
  const n = pts.length;
  pts.forEach(([cx, cy], i) => {
    const [px, py] = pts[(i + n - 1) % n], [nx, ny] = pts[(i + 1) % n];
    const d1 = Math.hypot(px - cx, py - cy), d2 = Math.hypot(nx - cx, ny - cy), rr = Math.min(radii[i], d1 / 2, d2 / 2);
    const a = [cx + (px - cx) / d1 * rr, cy + (py - cy) / d1 * rr], b = [cx + (nx - cx) / d2 * rr, cy + (ny - cy) / d2 * rr];
    i ? p.lineTo(...a) : p.moveTo(...a); p.quadraticCurveTo(cx, cy, ...b);
  });
  p.closePath();
}
const cuts = { front: [], back: [], left: [], right: [] }, screws = [];
for (const c of G.cutouts.filter(c => c.face !== 'top')) {
  const t = G.cutout_types[c.type];
  const u = { front: c.x, back: OX - c.x, right: c.y, left: OY - c.y }[c.face];
  let [pts, radii] = outline(t);
  if (c.near_edge === 'down') { pts = pts.map(([a, b]) => [a, -b]).reverse(); radii = radii.slice().reverse(); }
  cuts[c.face].push({ pts: pts.map(([a, b]) => [u + a, c.z + b]), radii });
  for (const su of [-1, 1]) {
    cuts[c.face].push({ circle: [u + su * t.holes / 2, c.z, t.hole_d / 2] });
    if (c.face === 'front' || c.face === 'back') screws.push({ face: c.face, x: c.x + (c.face === 'front' ? su : -su) * t.holes / 2, z: c.z });
  }
}
function wallShape(face, len, holes) {
  const s = new THREE.Shape(), along = face === 'front' || face === 'back' ? xs : ys;
  const flip = face === 'back' ? OX : face === 'left' ? OY : null;
  const brk = [...new Set([0, len, ...along.map(v => flip ? flip - v : v)])].filter(v => v >= 0 && v <= len).sort((a, b) => a - b);
  s.moveTo(0.4, 0.4); s.lineTo(len - 0.4, 0.4);
  for (let i = brk.length - 1; i > 0; i--) {
    const z = wallTop(face, (brk[i] + brk[i - 1]) / 2) - 0.4;
    s.lineTo(Math.min(brk[i], len - 0.4), z); s.lineTo(Math.max(brk[i - 1], 0.4), z);
  }
  s.closePath();
  for (const h of holes) {
    const p = new THREE.Path();
    h.circle ? p.absarc(...h.circle, 0, Math.PI * 2, true) : filleted(p, h.pts, h.radii);
    s.holes.push(p);
  }
  const m = new THREE.Mesh(new THREE.ExtrudeGeometry(s, EXTRUDE), alu);
  m.geometry.translate(0, 0, 0.4);
  return m;
}
const body = new THREE.Group(), panel = new THREE.Group();
scene.add(body); body.add(panel);
const f = wallShape('front', OX, cuts.front); f.position.set(-OX / 2, 0, OY / 2 - W); body.add(f);
const bk = wallShape('back', OX, cuts.back); bk.rotation.y = Math.PI; bk.position.set(OX / 2, 0, -OY / 2 + W);
const l = wallShape('left', OY, cuts.left); l.rotation.y = -Math.PI / 2; l.position.set(-OX / 2 + W, 0, -OY / 2); body.add(l);
const r = wallShape('right', OY, cuts.right); r.rotation.y = Math.PI / 2; r.position.set(OX / 2 - W, 0, OY / 2); body.add(r);
(G.removable || []).includes('back') ? panel.add(bk) : body.add(bk);
body.add(span(W - 0.2, OX - W + 0.2, W - 0.2, OY - W + 0.2, 0, W, alu, 0.4));   // floor, between the walls
for (const sc of screws) {                 // the headers' flange screws, heads outside the wall
  const h = new THREE.Mesh(new THREE.CylinderGeometry(3.2, 3.4, 1.8, 32), steel);
  h.rotation.x = Math.PI / 2;
  h.position.set(sc.x - OX / 2, sc.z, sc.face === 'front' ? OY / 2 + 0.9 : -OY / 2 - 0.9);
  (sc.face === 'back' && (G.removable || []).includes('back') ? panel : body).add(h);
}
shade(body);

// ---- Lid: low plates with the receptacle holes, raised band and hood, risers, M4 bosses ----------
const lid = new THREE.Group(); scene.add(lid);
const TERMS = G.cutouts.filter(c => c.plug_dirs);
for (let i = 0; i + 1 < xs.length; i++) for (let j = 0; j + 1 < ys.length; j++) {
  const [x0, x1, y0, y1] = [xs[i], xs[i + 1], ys[j], ys[j + 1]];
  if (raisedAt((x0 + x1) / 2, (y0 + y1) / 2)) continue;
  const sh = new THREE.Shape(); sh.moveTo(x0, y0); sh.lineTo(x1, y0); sh.lineTo(x1, y1); sh.lineTo(x0, y1); sh.closePath();
  for (const t of TERMS) if (t.x > x0 && t.x < x1 && t.y > y0 && t.y < y1) {
    const p = new THREE.Path(); p.absarc(t.x, t.y, G.cutout_types[t.type].d / 2, 0, Math.PI * 2, true); sh.holes.push(p);
  }
  const m = new THREE.Mesh(new THREE.ExtrudeGeometry(sh, { ...EXTRUDE, depth: LT - 0.8 }), alu);
  m.geometry.translate(0, 0, 0.4);
  m.rotation.x = -Math.PI / 2; m.position.set(-OX / 2, TOP - LT, OY / 2); lid.add(m);
}
for (const rr of G.raised) {
  lid.add(span(rr.x0, rr.x1, rr.y0, rr.y1, rr.z - LT, rr.z, alu, 1.2));
  const edges = [[rr.x0, rr.y0, rr.x1, rr.y0, 0, -1], [rr.x0, rr.y1, rr.x1, rr.y1, 0, 1],
                 [rr.x0, rr.y0, rr.x0, rr.y1, -1, 0], [rr.x1, rr.y0, rr.x1, rr.y1, 1, 0]];
  for (const [ax, ay, bx, by, nx, ny] of edges) {    // a riser where the far side is low lid
    const stops = [nx ? ay : ax, ...(nx ? ys.filter(v => v > ay && v < by) : xs.filter(v => v > ax && v < bx)), nx ? by : bx];
    for (let k = 0; k + 1 < stops.length; k++) {
      const [s0, s1] = [stops[k], stops[k + 1]], mm = (s0 + s1) / 2;
      const xm = nx ? ax + nx : mm, ym = nx ? mm : ay + ny;
      if (xm <= 0 || xm >= OX || ym <= 0 || ym >= OY || raisedAt(xm, ym)) continue;
      lid.add(nx ? span(ax - (nx < 0 ? 0 : W), ax + (nx < 0 ? W : 0), s0, s1, TOP - LT, rr.z - LT + 0.5, alu)
                 : span(s0, s1, ay - (ny < 0 ? 0 : W), ay + (ny < 0 ? W : 0), TOP - LT, rr.z - LT + 0.5, alu));
    }
  }
}
for (const bo of G.bosses || []) {
  const [bx, bz] = P(bo.x, bo.y);
  const c = new THREE.Mesh(new THREE.CylinderGeometry(bo.d / 2, bo.d / 2, bo.z1 - bo.z0, 40), alu);
  c.position.set(bx, (bo.z0 + bo.z1) / 2, bz); lid.add(c);
}
shade(lid);

// ---- Board, as KiCad exports it (metres, origin at KiCad's origin, y up, z = KiCad y) -------------
const loader = new GLTFLoader();
const glb = async (url) => (await loader.loadAsync(url)).scene;
const board = new THREE.Group(); scene.add(board);
const pcb = await glb('build/board.glb');
pcb.scale.setScalar(1000);
// KiCad (x, y) -> outside frame (x - K.x0 + B.x0, B.y0 + K.y1 - y): the front edge is KiCad's bottom edge.
pcb.position.set(B.x0 - K.x0 - OX / 2, B.z0, OY / 2 - B.y0 - K.y1);
pcb.traverse(o => {
  if (!o.isMesh) return;
  const mats = Array.isArray(o.material) ? o.material : [o.material];
  for (const m of mats) {
    if (m.metalness > 0.5) m.roughness = Math.max(0.2, m.roughness);
    // KiCad's solder mask (0.08, 0.2, 0.14) and board body (0.42, 0.45, 0.29), which shows through it
    // here: both a glossy dark green.
    const is = (r, g, b) => Math.abs(m.color.r - r) + Math.abs(m.color.g - g) + Math.abs(m.color.b - b) < 0.01;
    if (is(0.08, 0.2, 0.14) || is(0.42, 0.45, 0.29)) {
      Object.assign(m, { transparent: false, opacity: 1, roughness: 0.32, metalness: 0 }); m.color.setRGB(0.012, 0.09, 0.045);
    }
  }
});
for (const ref of ['BB901', 'BB902']) pcb.getObjectByName(ref)?.traverse(o => { if (o.isMesh) o.material = copper; });
// The output and T1S headers' housings in grey (the models' near-white), their seals as modelled.
const housing = new THREE.MeshPhysicalMaterial({ color: 0x5f6469, roughness: 0.55, metalness: 0, clearcoat: 0.1 });
for (const c of G.cutouts.filter(c => c.face !== 'top')) pcb.getObjectByName(c.ref)?.traverse(o => {
  if (o.isMesh && o.material.color.r > 0.8 && o.material.color.g > 0.8 && o.material.color.b > 0.8) o.material = housing;
});
board.add(pcb);
shade(board);

// ---- SurLok Plus receptacles (on the busbars) and plugs, from Amphenol's models via KiCad ---------
// The models stand stud up, their origin on the seat; flipped, the seat rests on the busbar.
const surlok = await glb('build/surlok.glb');
surlok.scale.setScalar(1000);
surlok.updateMatrixWorld(true);
const part = (name) => {
  const src = surlok.getObjectByName(name), g = new THREE.Group(), c = src.clone(true);
  c.position.set(0, 0, 0); c.scale.setScalar(1000); c.rotation.x = Math.PI; g.add(c); shade(g); return g;
};
const recs = new THREE.Group(), plugs = new THREE.Group(); scene.add(recs, plugs);
const FLANGE_TOP = REC.depth + REC.seal + REC.flange_t;
const PLUG_LIFT = FLANGE_TOP + 0.5 - 11.55;           // the plug's skirt (11.55 mm above the seat in its model) clears the flange
const DIR_ANGLE = { E: 0, N: Math.PI / 2, W: Math.PI };
const screwHead = () => {
  const g = new THREE.Group();
  const h = new THREE.Mesh(new THREE.CylinderGeometry(3.5, 3.6, 2.2, 32), steel); h.position.y = 1.1; g.add(h);
  const s = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.8, 2.6), new THREE.MeshStandardMaterial({ color: 0x222222, roughness: 0.6 }));
  s.position.y = 2.0; g.add(s); return g;
};
for (const t of TERMS) {
  const [x, z] = P(t.x, t.y), bat = t.label === 'VBAT_IN';
  const rg = part(bat ? 'RECR' : 'RECB'); rg.position.set(x, CONTACT, z);
  const sq = G.cutout_types[t.type].screw_square / 2;
  for (const [dx, dz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
    const s = screwHead(); s.position.set(dx * sq, FLANGE_TOP, dz * sq); rg.add(s);
  }
  shade(rg); recs.add(rg);
  const dir = t.x > OX / 2 ? 'E' : 'W';               // outward: allowed for all four (plug_dirs)
  if (!t.plug_dirs.includes(dir)) continue;
  const pg = new THREE.Group(); pg.position.set(x, CONTACT + PLUG_LIFT, z); pg.rotation.y = DIR_ANGLE[dir];
  pg.add(part(bat ? 'PLGR' : 'PLGB'));
  // Cable: out of the plug's shell, down to the floor, then away.
  const ax = 22.2, R = 5.5, out = 45.2;
  const y0 = CONTACT + PLUG_LIFT + ax, path = new THREE.CurvePath();
  path.add(new THREE.LineCurve3(new THREE.Vector3(out - 2, y0, 0), new THREE.Vector3(out + 10, y0, 0)));
  path.add(new THREE.CubicBezierCurve3(new THREE.Vector3(out + 10, y0, 0), new THREE.Vector3(out + 60, y0, 0),
                                       new THREE.Vector3(out + 50, R, 0), new THREE.Vector3(out + 110, R, 0)));
  path.add(new THREE.LineCurve3(new THREE.Vector3(out + 110, R, 0), new THREE.Vector3(out + 600, R, 0)));
  const geo = new THREE.TubeGeometry(path, 400, R, 32);
  geo.translate(0, -(CONTACT + PLUG_LIFT), 0);
  const cable = new THREE.Mesh(geo, cableMat(bat ? 0x7c0f13 : 0x151619));
  pg.add(cable); shade(pg); plugs.add(pg);
}

// ---- Views ---------------------------------------------------------------------------------------
const camera = new THREE.PerspectiveCamera(24, W_PX / H_PX, 60, 3000);
if (EXPLODED) {
  board.position.y = 62; lid.position.y = 128; recs.position.y = 168; plugs.visible = false;
  camera.position.set(-330, 400, 540); camera.lookAt(0, 88, 0);
} else {
  camera.position.set(-270, 390, 450); camera.lookAt(8, 10, -4);
}
camera.setViewOffset(W_PX, H_PX, -W_PX * 0.13, 0, W_PX, H_PX);   // the case right of centre: the page's headline goes left
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const ao = new GTAOPass(scene, camera, W_PX, H_PX);
ao.updateGtaoMaterial({ radius: 6, distanceExponent: 1.5, thickness: 4, scale: 1.2, samples: 16 });
ao.blendIntensity = 0.85;
composer.addPass(ao);
composer.addPass(new OutputPass());
composer.render();
window.__rendered = true;
