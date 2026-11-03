// Render the front page's hero images of the enclosure (src/assets/hero/): the current enclosure
// version from enclosure-versions.json, the board exported by KiCad with its 3D models, and
// Amphenol's SurLok Plus models, lit and rendered by scripts/hero/scene.js in headless Chrome.
// Needs kicad-cli, so it runs on a workstation, not in CI; the images are committed.
//   npm run drawings && npm run hero
import { execFileSync } from 'node:child_process';
import { createServer } from 'node:http';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { extname, join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer';
import sharp from 'sharp';

const docs = join(dirname(fileURLToPath(import.meta.url)), '..');
const repo = join(docs, '..');
const sceneDir = join(docs, 'scripts/hero');
const build = join(sceneDir, 'build');
const out = join(docs, 'src/assets/hero');
mkdirSync(build, { recursive: true });
mkdirSync(out, { recursive: true });
const WIDTH = 2400, HEIGHT = 1200, SS = 2;   // output size; rendered SS times larger, then downsampled

// Geometry: the current version, as the drawings and the 3D mockup use it.
const index = JSON.parse(readFileSync(join(docs, 'src/diagrams/build/enclosure-versions.json'), 'utf8'));
const geometry = index.versions[index.current];

// The board outline in KiCad's coordinates (one Edge.Cuts rectangle).
const pcbFile = join(repo, 'node60.kicad_pcb');
const m = readFileSync(pcbFile, 'utf8').match(/\(gr_rect\s*\(start ([\d.-]+) ([\d.-]+)\)\s*\(end ([\d.-]+) ([\d.-]+)\)(?:(?!\(gr_rect)[\s\S])*?\(layer "Edge\.Cuts"\)/);
if (!m) throw new Error('no Edge.Cuts rectangle in node60.kicad_pcb');
const [x0, y0, x1, y1] = m.slice(1).map(Number);
const kicad = { x0: Math.min(x0, x1), x1: Math.max(x0, x1), y0: Math.min(y0, y1), y1: Math.max(y0, y1) };
writeFileSync(join(build, 'hero.json'), JSON.stringify({ geometry, kicad }));

// The board with its models, and the receptacles and plugs (enclosure parts, not on the board)
// through a scratch board so they come out in the same units and colours.
const cli = (...args) => execFileSync('kicad-cli', ['pcb', 'export', 'glb', '-f', ...args], { stdio: ['ignore', 'ignore', 'inherit'] });
cli('--include-pads', '--include-silkscreen', '--include-soldermask', '--include-tracks', '--subst-models',
    '-o', join(build, 'board.glb'), pcbFile);
const models = join(repo, 'lib/dropout-kicad-library/3dmodels/DropOut_Connector_Amphenol.3dshapes');
const parts = [['RECR', 'SLPRATPSR'], ['RECB', 'SLPRATPSB'], ['PLGR', 'SLPPA25BSR'], ['PLGB', 'SLPPA25BSB']];
const fps = parts.map(([ref, mpn], i) => `(footprint "hero:${ref}" (layer "F.Cu") (at ${i * 80} 0)
  (property "Reference" "${ref}" (at 0 0 0) (layer "F.SilkS") (hide yes) (effects (font (size 1 1))))
  (model "${models}/Amphenol_SurLok-Plus_${mpn}.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0))))`).join('\n');
writeFileSync(join(build, 'surlok.kicad_pcb'), `(kicad_pcb (version 20241229) (generator "pcbnew") (generator_version "9.0")
 (general (thickness 1.6) (legacy_teardrops no)) (paper "A4")
 (layers (0 "F.Cu" signal) (2 "B.Cu" signal) (5 "F.SilkS" user "F.Silkscreen") (25 "Edge.Cuts" user))
 (setup (pad_to_mask_clearance 0)) (net 0 "")
 ${fps}
 (gr_rect (start -1 -1) (end 1 1) (stroke (width 0.1) (type default)) (fill no) (layer "Edge.Cuts")))
`);
cli('--no-board-body', '-o', join(build, 'surlok.glb'), join(build, 'surlok.kicad_pcb'));

// Serve the scene (module scripts and fetch need http) and render each view.
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.glb': 'model/gltf-binary' };
const server = createServer((req, res) => {
  const path = join(sceneDir, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  let body;
  try { body = readFileSync(path); } catch { return res.writeHead(404).end(); }
  res.writeHead(200, { 'content-type': types[extname(path)] || 'application/octet-stream' }).end(body);
}).listen(0);
const port = server.address().port;
const browser = await puppeteer.launch({
  headless: true,
  args: ['--no-sandbox', '--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=metal', '--enable-unsafe-swiftshader'],
});
try {
  for (const view of ['assembled', 'exploded']) {
    const page = await browser.newPage();
    page.on('console', (msg) => console.log(`[${view}] ${msg.text()}`));
    page.on('pageerror', (err) => { throw err; });
    const w = WIDTH * SS, h = HEIGHT * SS;
    await page.setViewport({ width: w, height: h, deviceScaleFactor: 1 });
    await page.goto(`http://localhost:${port}/scene.html?view=${view}&w=${w}&h=${h}`);
    await page.waitForFunction('window.__rendered === true', { timeout: 600_000 });
    const png = await page.screenshot({ type: 'png' });
    const file = join(out, `node60-enclosure-${view}.webp`);
    await sharp(png).resize(WIDTH, HEIGHT, { kernel: 'lanczos3' }).webp({ quality: 90 }).toFile(file);
    console.log(`hero: ${file}`);
    await page.close();
  }
} finally {
  await browser.close();
  server.close();
}
