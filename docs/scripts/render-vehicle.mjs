// Draw the front page's vehicle wiring concept (src/diagrams/build/vehicle-wiring.svg): a classic
// pickup in an isometric view, painted in a warm cartoon style, with a Node60 at each corner, the
// battery's fused feeds, the power jumpers between the nodes of each pair, and Hub 100's T1S runs.
// The body is solid; VehicleWiring.astro fades it to a ghost and draws the wiring on (the groups
// and the per-cable delays are set here, the transitions in src/styles/custom.css, .n60-vw).
// Plain SVG, no dependencies. Units are millimetres in the truck's frame: x rearward from the
// front of the body, y to the left (driver's side), z up from the ground.
import { mkdirSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const out = join(dirname(fileURLToPath(import.meta.url)), '..', 'src/diagrams/build');
mkdirSync(out, { recursive: true });

// --- Projection: orthographic, camera in front of the truck's left side, looking down. The truck
// frame (x rear, y left, z up) is left-handed, so the screen axes are found with y flipped.
const AZ = (54 * Math.PI) / 180, EL = (28 * Math.PI) / 180;
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const sub = (a, b) => a.map((v, i) => v - b[i]);
const norm = (a) => { const l = Math.hypot(...a); return a.map((v) => v / l); };
const flip = ([x, y, z]) => [x, -y, z];
const C = [-Math.cos(EL) * Math.cos(AZ), Math.cos(EL) * Math.sin(AZ), Math.sin(EL)]; // towards the camera
const Rr = norm(cross(flip(C).map((v) => -v), [0, 0, 1]));
const R = flip(Rr), U = flip(cross(Rr, flip(C).map((v) => -v)));
const S = 0.2; // px per mm
const proj = (p) => [dot(p, R) * S, -dot(p, U) * S];
const depth = (p) => dot(p, C);
const LIGHT = norm([-0.45, 0.55, 1]);

// --- Paint: flat colours, shaded per face by its normal.
const PAL = {
	paint: '#9dbf9c', cream: '#f2e7d0', bed: '#a9c7a6', chrome: '#e4e1d8', glass: '#d6e6e2', tire: '#3e3733',
	seat: '#8c6f57', dash: '#6e5a49', frame: '#6c6763', engine: '#7c8b93', grille: '#6b5d50',
	node: '#1d1f22', hub: '#6a5ed2', battery: '#3c4148', fuse: '#d9534f',
};
const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const shade = (h, n) => {
	const k = Math.min(1.06, 0.8 + 0.26 * Math.max(0, dot(n, LIGHT)));
	return '#' + hex(h).map((v) => Math.round(Math.min(255, v * k)).toString(16).padStart(2, '0')).join('');
};

// --- Faces. Each solid gives its faces with outward normals; a face is drawn only if it faces the
// camera. Layers are drawn in order; faces within a layer are sorted far to near.
const layers = {};
const face = (layer, pts, n, mat, extra = {}) => {
	if (dot(n, C) <= 1e-6) return;
	const c = pts.reduce((a, p) => a.map((v, i) => v + p[i] / pts.length), [0, 0, 0]);
	(layers[layer] ??= []).push({ pts, depth: depth(c) + (extra.bias ?? 0), fill: PAL[mat] ? shade(PAL[mat], n) : mat, ...extra });
};
const box = (layer, [x0, x1], [y0, y1], [z0, z1], mat, extra) => {
	const P = (x, y, z) => [x, y, z];
	face(layer, [P(x0, y0, z0), P(x0, y1, z0), P(x0, y1, z1), P(x0, y0, z1)], [-1, 0, 0], mat, extra);
	face(layer, [P(x1, y0, z0), P(x1, y0, z1), P(x1, y1, z1), P(x1, y1, z0)], [1, 0, 0], mat, extra);
	face(layer, [P(x0, y0, z0), P(x0, y0, z1), P(x1, y0, z1), P(x1, y0, z0)], [0, -1, 0], mat, extra);
	face(layer, [P(x0, y1, z0), P(x1, y1, z0), P(x1, y1, z1), P(x0, y1, z1)], [0, 1, 0], mat, extra);
	face(layer, [P(x0, y0, z1), P(x0, y1, z1), P(x1, y1, z1), P(x1, y0, z1)], [0, 0, 1], mat, extra);
	face(layer, [P(x0, y0, z0), P(x1, y0, z0), P(x1, y1, z0), P(x0, y1, z0)], [0, 0, -1], mat, extra);
};
// A side profile in (x, z), extruded across y0..y1.
const extrude = (layer, profile, y0, y1, mat) => {
	let pr = profile;
	const area = pr.reduce((a, p, i) => { const q = pr[(i + 1) % pr.length]; return a + p[0] * q[1] - q[0] * p[1]; }, 0);
	if (area < 0) pr = [...pr].reverse(); // counter-clockwise with x right, z up
	face(layer, pr.map(([x, z]) => [x, y1, z]), [0, 1, 0], mat);
	face(layer, pr.map(([x, z]) => [x, y0, z]), [0, -1, 0], mat);
	pr.forEach(([x, z], i) => {
		const [x2, z2] = pr[(i + 1) % pr.length];
		face(layer, [[x, y0, z], [x2, y0, z2], [x2, y1, z2], [x, y1, z]], norm([z2 - z, 0, -(x2 - x)]), mat);
	});
};
const arc = (cx, cz, r, a0, a1, n = 14) =>
	Array.from({ length: n + 1 }, (_, i) => { const a = ((a0 + ((a1 - a0) * i) / n) * Math.PI) / 180; return [cx + r * Math.cos(a), cz + r * Math.sin(a)]; });
const ring = (n) => Array.from({ length: n }, (_, i) => (i * 2 * Math.PI) / n);
// A circle in a plane of constant y (wheel faces) or constant x (lamps).
const discY = (x, y, z, r, n = 36) => ring(n).map((t) => [x + r * Math.cos(t), y, z + r * Math.sin(t)]);
const discX = (x, y, z, r, n = 28) => ring(n).map((t) => [x, y + r * Math.cos(t), z + r * Math.sin(t)]);
const wheel = (layer, x, yc, z) => {
	const r = 380, hw = 120, N = 36, y0 = yc - hw, y1 = yc + hw, T = ring(N);
	T.forEach((a, i) => {
		const b = T[(i + 1) % N], p = (t, y) => [x + r * Math.cos(t), y, z + r * Math.sin(t)];
		face(layer, [p(a, y0), p(b, y0), p(b, y1), p(a, y1)], [Math.cos((a + b) / 2), 0, Math.sin((a + b) / 2)], 'tire', { edge: 'soft' });
	});
	for (const [y, n] of [[y0, -1], [y1, 1]]) {
		face(layer, discY(x, y, z, r), [0, n, 0], 'tire');
		face(layer, discY(x, y + n, z, 292), [0, n, 0], 'cream', { bias: 1 });
		face(layer, discY(x, y + 2 * n, z, 210), [0, n, 0], 'chrome', { bias: 2 });
		face(layer, discY(x, y + 3 * n, z, 70), [0, n, 0], '#a9a59c', { bias: 3 });
	}
};

// --- The truck: a classic styleside pickup, about 5.07 m long and 2 m wide.
const W = 980; // half the body width
const FA = 850, RA = 3850, WR = 380, ARCH = 470, ROCK = 470;
const archStart = (Math.asin((ROCK - WR) / ARCH) * 180) / Math.PI;
const lowerBody = [
	[70, ROCK], [60, 1000], [130, 1090], [1680, 1135], [1730, 1150], [2740, 1150], [2765, 1110], [2765, ROCK],
	...arc(FA, WR, ARCH, archStart, 180 - archStart),
];
const bedSide = [[2800, ROCK], ...arc(RA, WR, ARCH, 180 - archStart, archStart), [4960, ROCK], [4960, 1215], [2800, 1215]];

// Chassis and cab interior: hidden by the body until it fades.
box('inner', [150, 4950], [400, 480], [380, 520], 'frame');
box('inner', [150, 4950], [-480, -400], [380, 520], 'frame');
box('inner', [150, 230], [-480, 480], [380, 520], 'frame');
box('inner', [4870, 4950], [-480, 480], [380, 520], 'frame');
box('inner', [520, 1450], [-330, 330], [520, 1020], 'engine');
box('inner', [150, 230], [-650, 650], [520, 1000], 'engine'); // radiator
box('inner', [1720, 1940], [-W + 60, W - 60], [1000, 1150], 'dash');
box('inner', [2330, 2690], [-W + 120, W - 120], [600, 960], 'seat');
box('inner', [2560, 2690], [-W + 120, W - 120], [960, 1420], 'seat');
face('inner', discX(2030, 420, 1230, 170, 24).map(([x, y, z]) => [x + (z - 1230) * 0.5, y, z]), norm([-1, 0, 0.5]), 'dash'); // steering wheel
wheel('far', FA, -860, WR);
wheel('far', RA, -860, WR);

// Body.
extrude('body', lowerBody, -W, W, 'paint');
box('body', [-70, 60], [-1000, 1000], [290, 470], 'cream');
box('body', [4960, 5070], [-1000, 1000], [330, 480], 'cream');
extrude('body', bedSide, W - 80, W, 'paint');
extrude('body', bedSide, -W, -W + 80, 'paint');
box('body', [2800, 2870], [-W + 80, W - 80], [780, 1215], 'paint');
box('body', [4890, 4960], [-W + 80, W - 80], [780, 1215], 'paint');
box('body', [2870, 4890], [-W + 80, W - 80], [780, 820], 'bed'); // above the wheel tops
// Side stripe and door seams on both flanks.
for (const s of [1, -1]) {
	const y = s * (W + 2), n = [0, s, 0];
	for (const [xa, xb] of [[330, 2740], [2830, 4930]]) face('body', [[xa, y, 905], [xb, y, 905], [xb, y, 940], [xa, y, 940]], n, 'cream', { bias: 5, edge: 'thin' });
	face('body', [[1750, y, 500], [1762, y, 500], [1762, y, 1148], [1750, y, 1148]], n, '#6f8f6e', { bias: 5, edge: 'none' });
	face('body', [[2700, y, 500], [2712, y, 500], [2712, y, 1148], [2700, y, 1148]], n, '#6f8f6e', { bias: 5, edge: 'none' });
	face('body', [[2560, y, 1040], [2660, y, 1040], [2660, y, 1066], [2560, y, 1066]], n, 'chrome', { bias: 6, edge: 'thin' });
}
// Cab greenhouse: a frustum from the beltline to the cream roof; the pillars frame the glass.
const centre = [2235, 0, 1470];
const ghFaces = [
	[[[1730, -W + 20, 1150], [1730, W - 20, 1150], [2060, W - 100, 1790], [2060, -W + 100, 1790]], 0.86],
	[[[1730, W - 20, 1150], [2740, W - 20, 1150], [2700, W - 100, 1790], [2060, W - 100, 1790]], 0.8],
	[[[2740, -W + 20, 1150], [1730, -W + 20, 1150], [2060, -W + 100, 1790], [2700, -W + 100, 1790]], 0.8],
	[[[2740, W - 20, 1150], [2740, -W + 20, 1150], [2700, -W + 100, 1790], [2700, W - 100, 1790]], 0.6],
	[[[2060, -W + 100, 1790], [2060, W - 100, 1790], [2700, W - 100, 1790], [2700, -W + 100, 1790]], 0],
];
const mean = (pts) => pts.reduce((a, p) => a.map((v, i) => v + p[i] / pts.length), [0, 0, 0]);
for (const [pts, k] of ghFaces) {
	const c = mean(pts);
	let n = norm(cross(sub(pts[1], pts[0]), sub(pts[2], pts[0])));
	if (dot(n, sub(c, centre)) < 0) n = n.map((v) => -v);
	const hole = k ? pts.map((p) => p.map((v, i) => c[i] + (v - c[i]) * k)) : null;
	face('body', pts, n, 'cream', { hole });
	if (hole) face('body', hole, n, 'glass', { glass: true, bias: -1 });
}
// Grille, lamps and lights on the front face.
face('body', [[58, -740, 560], [58, 740, 560], [58, 740, 960], [58, -740, 960]], [-1, 0, 0], 'grille', { bias: 5 });
for (let z = 600; z < 950; z += 62) face('body', [[56, -720, z], [56, 720, z], [56, 720, z + 24], [56, -720, z + 24]], [-1, 0, 0], 'chrome', { bias: 6, edge: 'thin' });
const LAMP = { head: '#f4eccd', fog: '#f4eccd', turn: '#e8a24a', tail: '#c9524a', plate: '#efe9dc' };
const lamps = [
	{ kind: 'head', pts: discX(54, 840, 800, 105), at: [54, 840, 800] },
	{ kind: 'head', pts: discX(54, -840, 800, 105), at: [54, -840, 800] },
	{ kind: 'turn', pts: [[54, 780, 570], [54, 920, 570], [54, 920, 640], [54, 780, 640]], at: [54, 850, 605] },
	{ kind: 'turn', pts: [[54, -920, 570], [54, -780, 570], [54, -780, 640], [54, -920, 640]], at: [54, -850, 605] },
	{ kind: 'fog', pts: discX(-72, 600, 380, 60), at: [-72, 600, 380] },
	{ kind: 'fog', pts: discX(-72, -600, 380, 60), at: [-72, -600, 380] },
	{ kind: 'tail', pts: [[4962, 984, 860], [4962, 984, 1160], [4890, 984, 1160], [4890, 984, 860]], at: [4930, 984, 1010] },
	{ kind: 'tail', pts: [[4962, -984, 860], [4962, -984, 1160], [4890, -984, 1160], [4890, -984, 860]], at: [4930, -984, 1010] },
	{ kind: 'plate', pts: [[5072, -160, 350], [5072, 160, 350], [5072, 160, 470], [5072, -160, 470]], at: [5072, 0, 410] },
];
for (const l of lamps) {
	const n = l.kind === 'tail' ? [0, Math.sign(l.at[1]), 0] : l.kind === 'plate' ? [1, 0, 0] : [-1, 0, 0];
	face('body', l.pts, n, LAMP[l.kind], { bias: 1500, edge: 'thin' }); // over the face it sits on
}

wheel('near', FA, 860, WR);
wheel('near', RA, 860, WR);

// --- Electrical: parts and cables, on top of the faded body.
const nodes = { FL: [430, 700, 930], FR: [430, -700, 930], RL: [4650, 700, 560], RR: [4650, -700, 560] };
const NODE = [300, 146, 56]; // Node60 at 1.25 × its 238 × 117 × 45 mm, so it reads
const parts = [];
const solid = (mat, [cx, cy, cz], [lx, ly, lz]) => {
	box('part', [cx - lx / 2, cx + lx / 2], [cy - ly / 2, cy + ly / 2], [cz - lz / 2, cz + lz / 2], mat);
	parts.push(...layers.part);
	delete layers.part;
};
for (const p of Object.values(nodes)) solid('node', p, NODE);
const HUB = [1880, 260, 900];
solid('hub', HUB, [200, 300, 60]);
const BAT = [1330, -730, 900];
solid('battery', BAT, [260, 180, 200]);
solid('fuse', [1150, -700, 960], [70, 120, 70]);

// Each cable: kind, delay (s) for the draw-on, points.
const cables = [
	['feed', 0.7, [[1150, -700, 960], [900, -780, 990], [580, -700, 930]]],
	['feed', 0.7, [[1150, -700, 960], [1260, -560, 760], [1500, -440, 540], [4400, -440, 540], [4500, -680, 560]]],
	['feed', 0.7, [[1150, -700, 960], [1250, -480, 1060], [1700, -250, 1080], [1780, 160, 920]]],
	['feed', 1.3, [[280, -700, 930], [245, -600, 975], [245, 600, 975], [280, 700, 930]]],
	['feed', 1.3, [[4800, -700, 560], [4880, -600, 545], [4880, 600, 545], [4800, 700, 560]]],
	['t1s', 1.1, [[1780, 360, 900], [1700, 460, 1010], [900, 790, 1010], [580, 720, 950]]],
	['t1s', 1.1, [[1960, 380, 870], [2000, 440, 560], [4400, 440, 560], [4500, 700, 585]]],
	['t1s', 1.6, [[280, 720, 950], [235, 580, 1030], [235, -580, 1030], [280, -720, 950]]],
	['t1s', 1.6, [[4800, 720, 585], [4895, 560, 610], [4895, -560, 610], [4800, -720, 585]]],
	['out', 2.0, [[280, 760, 920], [140, 810, 860], [60, 840, 800]]],
	['out', 2.0, [[280, 740, 905], [120, 820, 640], [60, 850, 605]]],
	['out', 2.0, [[300, 660, 905], [150, 620, 560], [20, 600, 380], [-70, 600, 380]]],
	['out', 2.0, [[280, -760, 920], [140, -810, 860], [60, -840, 800]]],
	['out', 2.0, [[280, -740, 905], [120, -820, 640], [60, -850, 605]]],
	['out', 2.0, [[300, -660, 905], [150, -620, 560], [20, -600, 380], [-70, -600, 380]]],
	['out', 2.0, [[4800, 740, 570], [4920, 930, 800], [4930, 975, 1000]]],
	['out', 2.0, [[4800, -740, 570], [4920, -930, 800], [4930, -975, 1000]]],
	['out', 2.0, [[4790, -650, 560], [4980, -150, 500], [5070, 0, 450]]],
];

// --- Labels: anchor in 3D, text placed in screen px relative to the anchor's projection.
const labels = [
	{ at: nodes.FL, dx: -250, dy: 150, title: 'Node60 · front left', sub: 'Headlight, turn signal, fog lamp', anchor: 'end' },
	{ at: nodes.FR, dx: 20, dy: -175, title: 'Node60 · front right', sub: 'Headlight, turn signal, fog lamp', anchor: 'end' },
	{ at: nodes.RL, dx: 30, dy: 215, title: 'Node60 · rear left', sub: 'Tail, brake and turn lamp' },
	{ at: nodes.RR, dx: 70, dy: -200, title: 'Node60 · rear right', sub: 'Tail, brake, turn and plate lamps' },
	{ at: HUB, dx: -60, dy: -365, title: 'Hub 100 under the dash', sub: 'Replaces the fuse panel' },
	{ at: BAT, dx: -30, dy: -300, title: 'Battery', sub: 'Fused feeds: front pair, rear pair, hub', anchor: 'end' },
];

// --- Emit.
const all = [...Object.values(layers).flat(), ...parts].flatMap((f) => f.pts.map(proj));
const minX = Math.min(...all.map((p) => p[0])), maxX = Math.max(...all.map((p) => p[0]));
const minY = Math.min(...all.map((p) => p[1])), maxY = Math.max(...all.map((p) => p[1]));
const PADX = 360, PADT = 150, PADB = 150;
const ox = PADX - minX, oy = PADT - minY;
const VW = Math.round(maxX - minX + 2 * PADX), VH = Math.round(maxY - minY + PADT + PADB);
const xy = (p) => { const [x, y] = proj(p); return [x + ox, y + oy]; };
const f1 = (v) => v.toFixed(1);
const ptsAttr = (pts) => pts.map((p) => xy(p).map(f1).join(',')).join(' ');
const ringPath = (pts) => pts.map((p, i) => `${i ? 'L' : 'M'}${xy(p).map(f1).join(' ')}`).join('') + 'Z';
const EDGE = { soft: 'e-soft', thin: 'e-thin', none: 'e-none' };
const polygon = (f) => {
	const cls = [f.glass ? 'glass' : '', EDGE[f.edge] ?? ''].filter(Boolean).join(' ');
	const c = cls ? ` class="${cls}"` : '';
	if (f.hole) return `<path${c} fill="${f.fill}" fill-rule="evenodd" d="${ringPath(f.pts)}${ringPath(f.hole)}"/>`;
	return `<polygon${c} fill="${f.fill}" points="${ptsAttr(f.pts)}"/>`;
};
const drawLayer = (name) => (layers[name] ?? []).sort((a, b) => a.depth - b.depth).map(polygon).join('');
const linePath = (pts) => pts.map((p, i) => `${i ? 'L' : 'M'}${xy(p).map(f1).join(' ')}`).join('');
const cablesSvg = cables.map(([kind, delay, pts]) => {
	const d = linePath(pts), s = ` style="--d:${delay}s"`;
	if (kind === 'out') return `<path class="cable out" pathLength="1"${s} d="${d}"/>`;
	return `<path class="cable ${kind}" pathLength="1"${s} d="${d}"/><path class="cable ${kind}-core"${s} d="${d}"/>`;
}).join('');
const lampsSvg = lamps.map((l) => {
	const [gx, gy] = xy(l.at);
	return `<circle class="glow ${l.kind}" cx="${f1(gx)}" cy="${f1(gy)}" r="${l.kind === 'head' ? 42 : 30}"/>`;
}).join('');
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
const label = ({ at, dx, dy, title, sub, anchor = 'start' }) => {
	const [ax, ay] = xy(at);
	const tx = ax + dx, ty = ay + dy;
	const lx = tx + (anchor === 'end' ? 10 : -10);
	return `<g class="callout"><path class="leader" d="M${f1(ax)} ${f1(ay)}L${f1(lx)} ${f1(ty - 6)}"/><circle class="pin" cx="${f1(ax)}" cy="${f1(ay)}" r="5"/>` +
		`<text x="${f1(tx)}" y="${f1(ty)}" text-anchor="${anchor}"><tspan class="lt">${esc(title)}</tspan><tspan class="ls" x="${f1(tx)}" dy="1.4em">${esc(sub)}</tspan></text></g>`;
};
let lx = VW - 1620;
const legend = [['feed', 'Power and ground; node to node: the jumper'], ['t1s', '10BASE-T1S pair'], ['out', 'Switched output to a lamp']].map(([k, t]) => {
	const x = lx, y = VH - 50, d = `M${x} ${y}h56`;
	lx += 72 + t.length * 14.5 + 50;
	return `<path class="cable ${k} key" d="${d}"/>${k === 'out' ? '' : `<path class="cable ${k}-core key" d="${d}"/>`}<text class="ls" x="${x + 72}" y="${y + 6}">${t}</text>`;
}).join('');
const shadow = `<polygon class="shadow" points="${ptsAttr([[-120, -1100, 0], [5150, -1100, 0], [5150, 1050, 0], [-120, 1050, 0]].map(([x, y, z]) => [x + 250, y - 250, z]))}"/>`;

const svg = `<svg xmlns="http://www.w3.org/2000/svg" class="n60-vw-svg" viewBox="0 0 ${VW} ${VH}" role="img" aria-labelledby="vw-title vw-desc">
<title id="vw-title">A classic pickup wired with four Node60s and Hub 100</title>
<desc id="vw-desc">Isometric drawing of a classic pickup truck. Revealed, the body turns see-through: a Node60 sits behind each front corner and each rear corner. The battery sends one fused feed to the front right node and one along the frame to the rear right node; each passes power to the node beside it through a jumper. Hub 100 under the dash takes its own feed and runs one T1S pair to the front left node, on to the front right, and another along the frame to the rear left node, on to the rear right. Each node drives its corner's lamps: headlight, turn signal and fog lamp at the front; tail, brake and turn lamps and the plate lamp at the rear.</desc>
<defs><filter id="vw-blur" x="-20%" y="-30%" width="140%" height="160%"><feGaussianBlur stdDeviation="18"/></filter><filter id="vw-glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="10"/></filter></defs>
<g filter="url(#vw-blur)">${shadow}</g>
<g class="vw-inner">${drawLayer('far')}${drawLayer('inner')}</g>
<g class="vw-body">${drawLayer('body')}</g>
<g class="vw-wiring">${cablesSvg}<g class="vw-parts">${parts.sort((a, b) => a.depth - b.depth).map(polygon).join('')}</g></g>
<g class="vw-near">${drawLayer('near')}</g>
<g class="vw-lamps">${lampsSvg}</g>
<g class="vw-notes">${labels.map(label).join('')}${legend}</g>
</svg>
`;
writeFileSync(join(out, 'vehicle-wiring.svg'), svg);
console.log(`vehicle: ${join(out, 'vehicle-wiring.svg')} (${VW} × ${VH})`);
