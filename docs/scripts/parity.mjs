// Parity check for the Rev C port (handbook chapter 08 port, step 5).
// Extracts every MPN-like token and every number with a unit from the frozen
// Rev C HTML and from the built site (dist/, excluding the legacy copy), and
// lists anything in Rev C that the site lacks. Differences that are expected
// are explained in scripts/parity-explained.json. Exits 1 on any unexplained gap.
//
//   npm run build && npm run parity
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { join, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const legacy = join(root, 'public/legacy/Node60-Architecture-RevC.html');
const dist = join(root, 'dist');
const explainedFile = join(root, 'scripts/parity-explained.json');

if (!existsSync(dist)) {
	console.error('dist/ not found: run `npm run build` first.');
	process.exit(2);
}

const entities = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', ndash: '–', mdash: '—', hellip: '…', rsquo: '’', lsquo: '‘', ldquo: '“', rdquo: '”', times: '×', plusmn: '±', deg: '°', micro: 'µ', ohm: 'Ω', minus: '−', asymp: '≈', le: '≤', ge: '≥', rarr: '→', larr: '←', middot: '·', sup2: '²' };

function htmlToText(html) {
	return html
		.replace(/<style[\s\S]*?<\/style>/gi, ' ')
		.replace(/<script[\s\S]*?<\/script>/gi, ' ')
		.replace(/data:[^"')\s]+/g, ' ')
		.replace(/<[^>]+>/g, ' ')
		.replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)))
		.replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(Number(d)))
		.replace(/&([a-z0-9]+);/gi, (m, n) => entities[n] ?? m)
		.replace(/[   ]/g, ' ')
		.replace(/\s+/g, ' ');
}

// MPN-like: letters and digits (with - or /), at least one of each, 5+ characters.
const MPN = /(?<![A-Za-z0-9\-\/])[A-Z0-9][A-Za-z0-9]*(?:[-\/][A-Za-z0-9]+)*(?![A-Za-z0-9])/g;
const isMpn = (t) => t.length >= 5 && /[A-Z]/.test(t) && /\d/.test(t);

// Number with a unit, including ranges (1–2 µA), approximations (≈$3.20) and prices.
const UNITS = ['mΩ', 'kΩ', 'Ω', 'µA', 'mA', 'kW', 'mW', 'W', 'mV', 'V', 'A', '°C', 'MHz', 'ppm', 'nF', 'µF', 'µs', 'ms', 'Mbit', 'KB', 'bit', 'byte', 'oz', 'AWG', 'mm', 'mil', 'week', 'weeks', 'years', 'days', 'pieces', 'units', 'events', '%', 's'];
const num = String.raw`\d+(?:,\d{3})*(?:\.\d+)?`;
const unitAlt = UNITS.map((u) => u.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
const QUANTITY = new RegExp(
	String.raw`(?<![A-Za-z0-9.])([≈±~−-]?)(${num})(?:\s?([–…-])\s?[≈±]?(${num}))?\s?-?(${unitAlt})(?![A-Za-z0-9])`,
	'g',
);
const PRICE = new RegExp(String.raw`[≈]?\$${num}(?:[–-]${num})?`, 'g');

function extract(text) {
	const mpns = new Set();
	for (const m of text.matchAll(MPN)) if (isMpn(m[0])) mpns.add(m[0]);
	const quantities = new Set();
	for (const m of text.matchAll(QUANTITY)) {
		const [, sign, a, sep, b, unit] = m;
		quantities.add(`${sign}${a}${sep ? sep + b : ''} ${unit}`);
	}
	for (const m of text.matchAll(PRICE)) quantities.add(m[0]);
	return { mpns, quantities };
}

function htmlFiles(dir) {
	const out = [];
	for (const name of readdirSync(dir)) {
		const p = join(dir, name);
		const rel = relative(dist, p);
		if (rel === 'legacy' || rel === 'pagefind' || rel === '_astro') continue;
		if (statSync(p).isDirectory()) out.push(...htmlFiles(p));
		else if (name.endsWith('.html') && name !== '404.html') out.push(p);
	}
	return out;
}

const rev = extract(htmlToText(readFileSync(legacy, 'utf8')));
const siteText = htmlFiles(dist)
	.map((f) => htmlToText(readFileSync(f, 'utf8')))
	.join(' ');
const site = extract(siteText);
const explained = existsSync(explainedFile) ? JSON.parse(readFileSync(explainedFile, 'utf8')) : {};

let unexplained = 0;
for (const [kind, label] of [
	['mpns', 'MPNs'],
	['quantities', 'numbers with units'],
]) {
	const missing = [...rev[kind]].filter((t) => !site[kind].has(t)).sort();
	console.log(`${label}: ${rev[kind].size} in Rev C, ${missing.length} missing from the site`);
	for (const t of missing) {
		if (explained[t]) console.log(`  explained  ${t}  — ${explained[t]}`);
		else {
			console.log(`  MISSING    ${t}`);
			unexplained++;
		}
	}
}
const stale = Object.keys(explained).filter((t) => !(rev.mpns.has(t) && !site.mpns.has(t)) && !(rev.quantities.has(t) && !site.quantities.has(t)));
for (const t of stale) console.log(`  note: explanation for "${t}" is no longer needed`);

if (unexplained) {
	console.error(`\n${unexplained} item(s) from Rev C are missing from the site.`);
	process.exit(1);
}
console.log('\nParity OK: every MPN and every number with a unit in Rev C is on the site or explained.');
