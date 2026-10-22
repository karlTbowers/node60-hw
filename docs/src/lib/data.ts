// Loads the architecture data collections once per build, resolves every
// cross-reference, and fails the build on an unknown ID (handbook chapter 08,
// "Traceability"). Components import from here rather than calling getCollection.
import { getCollection, type CollectionEntry } from 'astro:content';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

export type Requirement = CollectionEntry<'requirements'>['data'];
export type Part = CollectionEntry<'parts'>['data'];
export type Gate = CollectionEntry<'gates'>['data'];
export type Decision = CollectionEntry<'decisions'>['data'] & { body: string };
export type StatusItem = CollectionEntry<'status'>['data'];
export type Source = CollectionEntry<'sources'>['data'];

export interface Data {
	requirements: Requirement[];
	parts: Part[];
	gates: Gate[];
	decisions: Decision[];
	status: StatusItem[];
	sources: Source[];
	docPages: Set<string>;
}

let cache: Promise<Data> | undefined;

export function loadData(): Promise<Data> {
	cache ??= load();
	return cache;
}

async function load(): Promise<Data> {
	const byId = <T extends { id: string }>(a: T, b: T) => a.id.localeCompare(b.id);
	const data: Data = {
		requirements: inFileOrder('requirements', (await getCollection('requirements')).map((e) => e.data)),
		parts: inFileOrder('parts', (await getCollection('parts')).map((e) => e.data)),
		gates: inFileOrder('gates', (await getCollection('gates')).map((e) => e.data)),
		decisions: (await getCollection('decisions')).map((e) => ({ ...e.data, body: e.body ?? '' })).sort(byId),
		status: inFileOrder('status', (await getCollection('status')).map((e) => e.data)),
		sources: inFileOrder('sources', (await getCollection('sources')).map((e) => e.data)),
		docPages: new Set((await getCollection('docs')).map((e) => e.id)),
	};
	validate(data);
	return data;
}

/** Keep the order the YAML file lists its entries in (the loader doesn't). */
function inFileOrder<T extends { id: string }>(name: string, entries: T[]): T[] {
	const text = readFileSync(join(process.cwd(), 'src/data', `${name}.yaml`), 'utf8');
	const order = [...text.matchAll(/^- id: (.+)$/gm)].map((m) => m[1].trim());
	return entries.sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id));
}

function validate(d: Data) {
	const errors: string[] = [];
	const ids = {
		requirements: new Set(d.requirements.map((r) => r.id)),
		parts: new Set(d.parts.map((p) => p.id)),
		gates: new Set(d.gates.map((g) => g.id)),
		decisions: new Set(d.decisions.map((x) => x.id)),
	};
	const check = (from: string, kind: keyof typeof ids, refs: { id: string }[]) => {
		for (const r of refs) if (!ids[kind].has(r.id)) errors.push(`${from}: unknown ${kind} ID "${r.id}"`);
	};
	const checkPage = (from: string, page: string | undefined) => {
		if (page !== undefined && !d.docPages.has(page)) errors.push(`${from}: page "${page}" does not exist`);
	};

	for (const r of d.requirements) {
		check(r.id, 'gates', r.verified_by);
		checkPage(r.id, r.page);
	}
	for (const p of d.parts) {
		check(p.id, 'decisions', p.decisions);
		if (p.second_source && !ids.parts.has(p.second_source))
			errors.push(`${p.id}: second source "${p.second_source}" is not in parts.yaml`);
	}
	for (const g of d.gates) checkPage(g.id, g.page);
	for (const x of d.decisions) {
		check(x.id, 'decisions', x.supersedes);
		check(x.id, 'requirements', x.requirements);
		check(x.id, 'parts', x.parts);
		check(x.id, 'gates', x.gates);
		checkPage(x.id, x.page);
	}
	for (const s of d.status) checkPage(`status ${s.id}`, s.page);

	if (errors.length) throw new Error(`Architecture data has broken references:\n  ${errors.join('\n  ')}`);
}

/** Resolve an ID of any kind to its title and link; throws if it doesn't exist. */
export async function resolveRef(id: string): Promise<{ label: string; title: string; href: string }> {
	const d = await loadData();
	const req = d.requirements.find((r) => r.id === id);
	if (req) return { label: id, title: req.parameter ?? req.text, href: url(`requirements/#${anchor(id)}`) };
	const dec = d.decisions.find((x) => x.id === id);
	if (dec) return { label: id, title: dec.title, href: decisionUrl(id) };
	const gate = d.gates.find((g) => g.id === id);
	if (gate) return { label: id, title: gate.title, href: url(`verification/#${anchor(id)}`) };
	const src = d.sources.find((s) => s.id === id);
	if (src) return { label: id, title: src.title, href: url(`sources/#${anchor(id)}`) };
	const part = d.parts.find((p) => p.id === id);
	if (part) return { label: partName(part), title: part.function, href: url(`components/#${anchor(id)}`) };
	throw new Error(`<Ref id="${id}">: no requirement, decision, gate, source, or part has this ID`);
}

/** Site URL for a docs page ID ("subsystems/power") or a page-relative path with a hash. */
export function url(path: string): string {
	const base = import.meta.env.BASE_URL.replace(/\/$/, '');
	if (path === '' || path === 'index') return `${base}/`;
	const [p, hash] = path.split('#');
	const withSlash = p === '' ? '' : p.endsWith('/') ? p : `${p}/`;
	return `${base}/${withSlash}${hash ? `#${hash}` : ''}`;
}

export const decisionUrl = (id: string) => url(`decisions/${id.toLowerCase()}`);

export const anchor = (id: string) => id.toLowerCase().replace(/[^a-z0-9]+/g, '-');

export const partName = (p: Part) => p.mpn ?? p.label ?? p.id;

// Whole dollars as written ("$1"); otherwise at least cents ("$3.20", "$1.952").
const usd = (n: number) =>
	`$${Number.isInteger(n) ? n : n.toFixed(Math.max(2, (String(n).split('.')[1] ?? '').length))}`;

/** One observation as Rev C wrote it, e.g. "$5.43 @1 / ≈$3.20 @1k; 32,413 DigiKey". */
export function formatObservation(o: Part['observations'][number]): string {
	const prices = o.prices
		.map((p) => `${p.approx ? '≈' : ''}${usd(p.usd)} ${/^\d|k$/.test(p.qty) ? '@' + p.qty : p.qty}`)
		.join(' / ');
	const stock =
		o.stock === undefined
			? ''
			: o.stock === 0
				? `0 stock at ${o.source}`
				: `${o.stock_approx ? '≈' : ''}${o.stock.toLocaleString('en-US')} at ${o.source}`;
	const parts = [prices, stock].filter(Boolean);
	let text = parts.join('; ');
	if (!text) text = o.source;
	if (o.note) text += ` (${o.note})`;
	return text;
}

export const isoDate = (d: Date) => d.toISOString().slice(0, 10);
