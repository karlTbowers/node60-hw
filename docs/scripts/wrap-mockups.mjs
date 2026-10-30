// Wrap each HTML fragment in src/mockups/ into a full page in public/mockups/ (gitignored).
// The fragments are also published as Claude artifacts, which add their own document skeleton,
// so the source keeps no <!doctype>, <html>, <head> or <body> of its own.
// A fragment may contain the marker /*ENCLOSURE_VERSIONS_JSON*/null: it is replaced by every
// enclosure version's geometry that `npm run drawings` wrote (src/diagrams/build/
// enclosure-versions.json), so the mockup and the dimensioned drawings always show the same designs. Run with `--fill <fragment> <out>`
// to write a filled fragment without the page skeleton (for publishing the artifact).
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = join(root, 'src/mockups');
const out = join(root, 'public/mockups');
mkdirSync(out, { recursive: true });

const head = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>
:root { color-scheme: light; padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px); }
body { margin: 0; font: 14px system-ui, sans-serif; }
img { max-width: 100%; }
[hidden] { display: none !important; }
</style>
`;

const geometry = join(root, 'src/diagrams/build/enclosure-versions.json');
const fill = (body) => {
	if (!body.includes('/*ENCLOSURE_VERSIONS_JSON*/null')) return body;
	const json = readFileSync(geometry, 'utf8').trim();
	return body.replace('/*ENCLOSURE_VERSIONS_JSON*/null', () => json);
};

if (process.argv[2] === '--fill') {
	writeFileSync(process.argv[4], fill(readFileSync(process.argv[3], 'utf8')));
	console.log(`mockup filled: ${process.argv[4]}`);
	process.exit(0);
}

for (const file of readdirSync(src).sort()) {
	if (!file.endsWith('.html')) continue;
	const body = fill(readFileSync(join(src, file), 'utf8'));
	writeFileSync(join(out, file), `${head}</head>\n<body>\n${body}\n</body>\n</html>\n`);
	console.log(`mockup: ${file}`);
}
