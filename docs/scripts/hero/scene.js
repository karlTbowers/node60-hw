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
const EXPLODED = VIEW === 'exploded', LAMPS = VIEW === 'lamps';
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
const SH = LAMPS ? 560 : 260;                        // the lamps view spreads wider
key.shadow.camera.left = -SH; key.shadow.camera.right = SH;
key.shadow.camera.top = SH; key.shadow.camera.bottom = -SH;
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
const powerRuns = [];                                  // each plugged cable's centre line, in the scene's frame
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
  if (LAMPS && dir === 'E') {                         // the lamps view: bend away north-east, clear of the lamps
    path.add(new THREE.CubicBezierCurve3(new THREE.Vector3(out + 110, R, 0), new THREE.Vector3(out + 190, R, 0),
                                         new THREE.Vector3(out + 230, R, -40), new THREE.Vector3(out + 290, R, -120)));
    path.add(new THREE.LineCurve3(new THREE.Vector3(out + 290, R, -120), new THREE.Vector3(out + 650, R, -600)));
  } else path.add(new THREE.LineCurve3(new THREE.Vector3(out + 110, R, 0), new THREE.Vector3(out + 600, R, 0)));
  const geo = new THREE.TubeGeometry(path, 400, R, 32);
  geo.translate(0, -(CONTACT + PLUG_LIFT), 0);
  const cable = new THREE.Mesh(geo, cableMat(bat ? 0x7c0f13 : 0x151619));
  pg.add(cable); shade(pg); plugs.add(pg);
  pg.updateMatrixWorld(true);
  const lift = new THREE.Vector3(0, -(CONTACT + PLUG_LIFT), 0), mw = pg.matrixWorld.clone();
  powerRuns.push({ ref: t.ref, at: (u) => path.getPoint(u).add(lift).applyMatrix4(mw) });
}

// ---- Lamps view: a plug in every output and both T1S headers, a vehicle's front lamps on the outputs --
// A concept, one load per output: OUT1 a DRL bar, OUT2 a parking (position) lamp, OUT3 an amber turn
// indicator, OUT4 a round fog lamp, OUT5 and OUT6 a 7" round LED headlight's low and high beams.
// Procedural, no maker's models; each lamp is built facing +z, its back at -z.
if (LAMPS) {
  const world = new THREE.Group(); scene.add(world);
  scene.updateMatrixWorld(true);
  const black = new THREE.MeshPhysicalMaterial({ color: 0x18191b, metalness: 0.35, roughness: 0.5 });
  const rubber = new THREE.MeshStandardMaterial({ color: 0x111213, roughness: 0.8 });
  const chrome = new THREE.MeshStandardMaterial({ color: 0xe6e9ec, metalness: 1, roughness: 0.08 });
  const glass = new THREE.MeshPhysicalMaterial({ color: 0xf4f8fb, metalness: 0, roughness: 0.04, transparent: true,
    opacity: 0.14, clearcoat: 1, clearcoatRoughness: 0.02, depthWrite: false });
  const led = (c, i) => new THREE.MeshStandardMaterial({ color: c, emissive: c, emissiveIntensity: i, roughness: 0.4 });
  const jacket = cableMat(0x1a1b1d);
  const lathe = (pts, m, seg = 96) => {      // a profile of [r, z] revolved about z
    const g = new THREE.LatheGeometry(pts.map(([r, z]) => new THREE.Vector2(r, z)), seg); g.rotateX(Math.PI / 2);
    const mm = m.clone(); mm.side = THREE.DoubleSide; return new THREE.Mesh(g, mm);
  };
  const cap = (rim, sag, m, seg = 96) => {    // a spherical lens, its rim at z = 0, bulging to z = sag
    const R = (rim * rim + sag * sag) / (2 * sag), g = new THREE.SphereGeometry(R, seg, 24, 0, Math.PI * 2, 0, Math.asin(rim / R));
    g.rotateX(Math.PI / 2); g.translate(0, 0, sag - R); return new THREE.Mesh(g, m);
  };
  const at = (o, x, y, z) => { o.position.set(x, y, z); return o; };

  // Mating plugs: the visible body behind the header's shroud, a lock ridge on the tab side, a rear grommet.
  const headerFace = (ref, face) => {
    const b = new THREE.Box3().setFromObject(pcb.getObjectByName(ref));
    return face === 'front' ? b.max.z : b.min.z;
  };
  const plug = (c) => {
    const t = G.cutout_types[c.type], s = c.face === 'front' ? 1 : -1;
    const w = t.width - 0.6, h = t.full - 0.6, len = c.type === 'AT13' ? 26 : 22;
    const z0 = headerFace(c.ref, c.face) - s * 1, [x] = P(c.x, 0), y = c.z - (t.full / 2 - t.near / 2) * 0;
    const g = new THREE.Group();
    g.add(at(new THREE.Mesh(new RoundedBoxGeometry(w, h, len, 3, 1.6), housing), 0, 0, len / 2));
    for (let k = 1; k < 4; k++) g.add(at(new THREE.Mesh(new RoundedBoxGeometry(w + 0.8, h + 0.8, 1.4, 2, 0.6), housing), 0, 0, len - 3 - k * 3.2));
    g.add(at(new THREE.Mesh(new RoundedBoxGeometry(t.tab * 0.6, 2.6, len * 0.7, 2, 0.8), housing), 0, -h / 2 - 1.1, len * 0.45));
    const gr = new THREE.Mesh(new THREE.CylinderGeometry(w * 0.32, w * 0.36, 7, 32), rubber);
    gr.rotation.x = Math.PI / 2; g.add(at(gr, 0, 0, len + 3.5));
    g.position.set(x, c.z - (t.near - t.full / 2) * 0, z0); if (s < 0) g.rotation.y = Math.PI;
    shade(g); world.add(g);
    return new THREE.Vector3(x, g.position.y, z0 + s * (len + 7));   // where the wires leave
  };
  const out = Object.fromEntries(G.cutouts.filter(c => c.face !== 'top').map(c => [c.ref, c]));

  // Lamps, placed in front of the outputs and turned three-quarters toward the camera.
  const blob = (x, z, w, d) => {             // a soft contact shadow, as under the case
    const c = document.createElement('canvas'); c.width = 256; c.height = 256;
    const k = c.getContext('2d'), gr = k.createRadialGradient(128, 128, 4, 128, 128, 124);
    gr.addColorStop(0, 'rgba(20,28,36,0.55)'); gr.addColorStop(1, 'rgba(20,28,36,0)'); k.fillStyle = gr; k.fillRect(0, 0, 256, 256);
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false }));
    m.rotation.x = -Math.PI / 2; m.position.set(x, 0.06, z); world.add(m);
  };
  // A label printed on the floor in front of a lamp, in the backdrop's greys so it stays quiet.
  const label = (lines, x, z, yaw, ahead, side = 0, size = 1) => {
    const c = document.createElement('canvas'); c.width = 1024; c.height = 256;
    const k = c.getContext('2d'); k.textAlign = 'center'; k.textBaseline = 'middle';
    k.fillStyle = 'rgba(88,98,108,0.9)'; k.font = '700 58px -apple-system, "Helvetica Neue", Arial, sans-serif';
    k.fillText(lines[0], 512, 82);
    k.fillStyle = 'rgba(88,98,108,0.75)'; k.font = '500 66px -apple-system, "Helvetica Neue", Arial, sans-serif';
    k.fillText(lines[1], 512, 172);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 16;
    const g = new THREE.PlaneGeometry(200 * size, 50 * size); g.rotateX(-Math.PI / 2);
    const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ map: t, transparent: true, depthWrite: false, toneMapped: false }));
    m.rotation.y = yaw;
    m.position.set(x + ahead * Math.sin(yaw) + side * Math.cos(yaw), 0.08, z + ahead * Math.cos(yaw) - side * Math.sin(yaw)); world.add(m);
  };
  const lamp = (build, x, z, yaw, w = 120, d = 120) => {
    const g = new THREE.Group(); build(g); g.position.set(x, 0, z); g.rotation.y = yaw; blob(x, z - 20, w, d);
    shade(g); world.add(g); g.updateMatrixWorld(true);
    return (v) => v.clone().applyMatrix4(g.matrixWorld);
  };
  // 7" (178 mm) round headlight with one dual-filament bulb (H4 type: the low and high beams are the
  // bulb's two filaments): housing, a chrome parabolic reflector, the bulb with its tip cap, a clear
  // lens with faint prism ribs.
  const HR = 89, HC = HR + 3;
  const head = lamp((g) => {
    const l = new THREE.Group(); l.position.y = HC; g.add(l);
    l.add(lathe([[0, -88], [38, -88], [60, -80], [76, -58], [85, -30], [HR, -6], [HR, 1]], black));
    l.add(at(new THREE.Mesh(new THREE.TorusGeometry(HR - 1.5, 3.4, 20, 128), chrome), 0, 0, 1));
    const refl = []; for (let r = 15; r <= HR - 4; r += 2.5) refl.push([r, -70 + r * r / 112]); l.add(lathe(refl, chrome));
    l.add(at(lathe([[0, -71], [15, -71], [15, -68]], steel), 0, 0, 0));            // the bulb's collar
    const env = new THREE.Mesh(new THREE.CylinderGeometry(5.6, 5.6, 26, 32), glass);
    env.rotation.x = Math.PI / 2; l.add(at(env, 0, 0, -54));
    l.add(at(new THREE.Mesh(new THREE.SphereGeometry(5.6, 32, 16), glass), 0, 0, -41));
    for (const fz of [-58, -49]) {                     // the two filaments, the low beam's lit
      const fil = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 0.9, 5, 12), led(0xffe7b8, fz > -50 ? 2.2 : 0.3));
      fil.rotation.x = Math.PI / 2; l.add(at(fil, 0, fz > -50 ? 1.2 : -0.8, fz));
    }
    l.add(at(cap(5.4, 3.2, new THREE.MeshStandardMaterial({ color: 0x141516, roughness: 0.4 }), 32), 0, 0, -37.5));   // tip cap
    l.add(cap(HR - 2, 11, glass));
    const rib = glass.clone(); rib.opacity = 0.045;
    for (let k = -7; k <= 7; k++) {                    // the lens's prism ribs
      const len = 2 * Math.sqrt((HR - 6) ** 2 - (k * 11) ** 2), z = 11 - (k * 11) ** 2 / 690;
      const v = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.6, len, 10), rib); l.add(at(v, k * 11, 0, z));
      const h = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.6, len, 10), rib); h.rotation.z = Math.PI / 2; l.add(at(h, 0, k * 11, z));
    }
    l.add(at(new THREE.Mesh(new RoundedBoxGeometry(34, 22, 20, 3, 3), rubber), 0, 0, -97));   // the plug on its back
    // a cradle: a black stand under the housing
    g.add(at(new THREE.Mesh(new RoundedBoxGeometry(70, 6, 110, 3, 2), black), 0, 3, -40));
    g.add(at(new THREE.Mesh(new RoundedBoxGeometry(12, 14, 70, 2, 2), black), -32, 10, -40));
    g.add(at(new THREE.Mesh(new RoundedBoxGeometry(12, 14, 70, 2, 2), black), 32, 10, -40));
  }, 360, 110, -0.45, 230, 200);
  // Round fog lamp, 120 mm: housing, a chrome reflector and bulb, a fluted clear lens, a pedestal mount.
  const FR = 60, FC = FR + 30;
  const fog = lamp((g) => {
    const l = new THREE.Group(); l.position.y = FC; g.add(l);
    l.add(lathe([[0, -70], [24, -70], [43, -59], [55, -36], [FR, -9], [FR, 1]], black));
    l.add(at(new THREE.Mesh(new THREE.TorusGeometry(FR - 1, 3.4, 18, 112), chrome), 0, 0, 1));
    l.add(at(cap(9, 6, chrome), 0, 0, -31));                 // the bulb's shield
    const flute = glass.clone(); flute.opacity = 0.07;
    const refl = []; for (let r = 7; r <= 57; r += 2.5) refl.push([r, -54 + r * r / 62]); l.add(lathe(refl, chrome));
    l.add(at(new THREE.Mesh(new THREE.SphereGeometry(6, 24, 16), led(0xfff2d8, 0.9)), 0, 0, -38));
    l.add(cap(FR - 2, 6, glass));
    for (let k = -3; k <= 3; k++) {          // the lens's flutes
      const len = 2 * Math.sqrt((FR - 4) ** 2 - (k * 14) ** 2);
      const f = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 0.7, len, 12), flute);
      l.add(at(f, k * 14, 0, 4.5));
    }
    g.add(at(new THREE.Mesh(new THREE.CylinderGeometry(7, 9, 30, 24), black), 0, 17, -38));
    g.add(at(new THREE.Mesh(new THREE.CylinderGeometry(24, 26, 5, 40), black), 0, 2.5, -38));
  }, 190, 300, -0.5, 115, 115);
  // Amber turn indicator, 80 mm: a chrome bowl and bezel on a stalk, its ribbed lens lit.
  const TR = 36, TC = TR + 34;
  const turn = lamp((g) => {
    const l = new THREE.Group(); l.position.y = TC; g.add(l);
    l.add(lathe([[0, -44], [20, -44], [33, -30], [TR, -8], [TR, 1]], black));
    l.add(at(new THREE.Mesh(new THREE.TorusGeometry(TR - 1, 2.4, 16, 96), chrome), 0, 0, 1));
    const amber = new THREE.MeshPhysicalMaterial({ color: 0xff8a12, emissive: 0xff7a00, emissiveIntensity: 0.9,
      roughness: 0.18, clearcoat: 1, transmission: 0 });
    l.add(cap(TR - 2, 13, amber));
    for (const rr of [10, 20, 30]) l.add(at(new THREE.Mesh(new THREE.TorusGeometry(rr, 0.9, 10, 64), amber), 0, 0, 13 - rr * rr / 82));
    const st = new THREE.Mesh(new THREE.CylinderGeometry(5, 6, 36, 24), black); g.add(at(st, 0, 18, -26));
    g.add(at(new THREE.Mesh(new THREE.CylinderGeometry(17, 18, 4, 40), black), 0, 2, -26));
  }, 45, 390, -0.55, 80, 80);
  // Parking (position) lamp, 96 x 46 mm: a chrome bezel round a frosted lens, dimly lit, on a bracket.
  const PW = 96, PH = 46, PC = PH / 2 + 30;
  const park = lamp((g) => {
    const l = new THREE.Group(); l.position.y = PC; g.add(l);
    l.add(at(new THREE.Mesh(new RoundedBoxGeometry(PW - 4, PH - 4, 34, 4, 8), black), 0, 0, -17));
    const sh = new THREE.Shape(); roundRect(sh, -PW / 2, -PH / 2, PW / 2, PH / 2, 12);
    const hole = new THREE.Path(); roundRect(hole, -PW / 2 + 6, -PH / 2 + 6, PW / 2 - 6, PH / 2 - 6, 7); sh.holes.push(hole);
    l.add(new THREE.Mesh(new THREE.ExtrudeGeometry(sh, { depth: 3, bevelEnabled: true, bevelThickness: 1, bevelSize: 1, bevelSegments: 3, curveSegments: 16 }), chrome));
    const lens = new THREE.MeshPhysicalMaterial({ color: 0xfaf6ee, emissive: 0xffe2b0, emissiveIntensity: 0.22, roughness: 0.5, clearcoat: 0.6 });
    l.add(at(new THREE.Mesh(new RoundedBoxGeometry(PW - 11, PH - 11, 4, 3, 1.8), lens), 0, 0, 1));
    g.add(at(new THREE.Mesh(new RoundedBoxGeometry(10, 32, 10, 2, 2), black), 0, 16, -22));
    g.add(at(new THREE.Mesh(new RoundedBoxGeometry(44, 4, 30, 2, 1.5), black), 0, 2, -22));
  }, -55, 330, -0.55, 110, 70);
  // DRL: a slim LED bar, 200 mm, its lit strip behind a clear cover, on two feet.
  const DW = 200, DH = 24, DC = DH / 2 + 22;
  const drl = lamp((g) => {
    const l = new THREE.Group(); l.position.y = DC; g.add(l);
    l.add(at(new THREE.Mesh(new RoundedBoxGeometry(DW, DH, 30, 4, 5), black), 0, 0, -15));
    l.add(at(new THREE.Mesh(new RoundedBoxGeometry(DW - 16, 7, 2, 2, 1), led(0xf4f8ff, 2.4)), 0, 0, 0.6));
    l.add(at(new THREE.Mesh(new RoundedBoxGeometry(DW - 8, DH - 8, 3, 2, 1.4), glass), 0, 0, 1));
    for (const fx of [-DW / 2 + 22, DW / 2 - 22]) {
      g.add(at(new THREE.Mesh(new RoundedBoxGeometry(8, 22, 8, 2, 2), black), fx, 11, -15));
      g.add(at(new THREE.Mesh(new RoundedBoxGeometry(26, 4, 34, 2, 1.5), black), fx, 2, -15));
    }
  }, -255, 195, -0.5, 240, 80);

  label(['OUT1', 'Daytime running light'], -255, 195, -0.5, 40);
  label(['OUT2', 'Parking light'], -55, 330, -0.55, 38);
  label(['OUT3', 'Turn signal'], 45, 390, -0.55, 42);
  label(['OUT4', 'Fog light'], 190, 300, -0.5, 52);
  label(['OUT5 + OUT6', 'Headlight, low and high beam'], 360, 110, -0.45, 75, 150, 1.3);   // beside it, the fog lamp being in front; larger, being farther

  // Cables: out of the plug, down to the floor, along it, up into the lamp's back.
  const R = 3.2;
  const route = (from, to, back, drop = 55) => new THREE.CatmullRomCurve3([
    from, from.clone().add(new THREE.Vector3(0, 0, Math.sign(back.z || 1) * 0)).add(new THREE.Vector3(0, 0, 14)),
    new THREE.Vector3(from.x, R, from.z + drop), ...back.floor,
    to.clone().add(back.dir.clone().multiplyScalar(30)), to], false, 'centripetal');
  const cable = (curve, m = jacket, r = R) => {
    const c = new THREE.Mesh(new THREE.TubeGeometry(curve, 300, r, 20), m); shade(c); world.add(c);
  };
  const backOf = (toWorld, local, floorAt) => {
    const to = toWorld(new THREE.Vector3(...local)), behind = toWorld(new THREE.Vector3(local[0], local[1], local[2] - 60));
    const dir = behind.clone().sub(to).normalize();
    return { to, dir, floor: floorAt.map(([lx, lz]) => { const v = toWorld(new THREE.Vector3(lx, 0, lz)); v.y = R; return v; }) };
  };
  for (const [ref, toWorld, local, floor, drop] of [
    ['J904', drl, [0, DC, -30], [[0, -70]]], ['J905', park, [0, PC, -34], [[0, -70]]],
    ['J906', turn, [0, TC - 6, -44], [[0, -90]]], ['J907', fog, [0, FC - 10, -70], [[0, -120]]],
    ['J908', head, [-5, HC, -107], [[-5, -150]]], ['J909', head, [5, HC, -107], [[8, -160]], 70]]) {
    const b = backOf(toWorld, local, floor); cable(route(plug(out[ref]), b.to, b, drop));
  }

  // T1S: a twisted pair out of each ATM13 plug, round the case's back corner and then alongside the
  // nearer return cable (the outer side, away from the battery cable), as a harness would run.
  const wireA = cableMat(0xe9e6df), wireB = cableMat(0x2f5fb0), WR = 1.5, GAP = 5.5 + 2 * WR + 1.5;
  for (const [ref, gnd, side] of [['J903', 'J902', 1], ['J912', 'J911', -1]]) {
    const run = powerRuns.find(r => r.ref === gnd), bat = powerRuns.find(r => r.ref !== gnd && Math.sign(r.at(0).x) === side);
    const along = [];
    for (let i = 0; i <= 200; i++) {
      const u = i / 200, p = run.at(u);
      if (side * p.x < OX / 2 + 25 || p.y > 6.5) continue;   // join it on the floor, clear of the case
      const tg = run.at(Math.min(1, u + 0.002)).sub(run.at(Math.max(0, u - 0.002))).setY(0).normalize();
      let n = new THREE.Vector3(-tg.z, 0, tg.x);
      if (n.dot(p.clone().sub(bat.at(u))) < 0) n.negate();
      along.push(p.add(n.multiplyScalar(GAP)).setY(WR * 2));
    }
    const from = plug(out[ref]);
    const path = new THREE.CatmullRomCurve3([from, from.clone().add(new THREE.Vector3(0, 0, -14)),
      new THREE.Vector3(from.x, WR * 2, from.z - 45), new THREE.Vector3(side * (OX / 2 + 8), WR * 2, -OY / 2 - 22),
      ...along.slice(12).filter((_, i) => i % 3 === 0)],
      false, 'centripetal');
    const len = path.getLength(), N = Math.ceil(len / 0.6), fr = path.computeFrenetFrames(N, false), lay = 14;
    for (const [ph, m] of [[0, wireA], [Math.PI, wireB]]) {
      const pts = [];
      for (let i = 0; i <= N; i++) {
        const th = ph + 2 * Math.PI * (i / N) * len / lay, p = path.getPointAt(i / N);
        pts.push(p.add(fr.normals[i].clone().multiplyScalar(Math.cos(th) * WR * 0.95)).add(fr.binormals[i].clone().multiplyScalar(Math.sin(th) * WR * 0.95)));
      }
      cable(new THREE.CatmullRomCurve3(pts), m, WR);
    }
  }
}

// ---- Views ---------------------------------------------------------------------------------------
const camera = new THREE.PerspectiveCamera(24, W_PX / H_PX, 60, 3000);
if (EXPLODED) {
  board.position.y = 62; lid.position.y = 128; recs.position.y = 168; plugs.visible = false;
  camera.position.set(-330, 400, 540); camera.lookAt(0, 88, 0);
} else if (LAMPS) {
  // Pulled back and shifted right and down, so the headline's corner (top left) stays clear.
  const at0 = new THREE.Vector3(120, 30, 190);
  camera.position.set(-320, 700, 1070).sub(at0).multiplyScalar(1.25).add(at0); camera.lookAt(at0);
} else {
  camera.position.set(-270, 390, 450); camera.lookAt(8, 10, -4);
}
camera.setViewOffset(W_PX, H_PX, -W_PX * (LAMPS ? 0.14 : 0.13), LAMPS ? -H_PX * 0.09 : 0, W_PX, H_PX);   // the case right of centre: the page's headline goes left
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const ao = new GTAOPass(scene, camera, W_PX, H_PX);
ao.updateGtaoMaterial({ radius: 6, distanceExponent: 1.5, thickness: 4, scale: 1.2, samples: 16 });
ao.blendIntensity = 0.85;
composer.addPass(ao);
composer.addPass(new OutputPass());
composer.render();
window.__rendered = true;
