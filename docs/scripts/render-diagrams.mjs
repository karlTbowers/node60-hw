// Render every diagram source in src/diagrams/ to SVG in src/diagrams/build/ (gitignored).
// D2 (*.d2) needs the `d2` binary on PATH; each file sets its own layout engine.
// Mermaid (*.mmd) uses the mermaid-cli devDependency.
// Pages inline the SVGs through the D2Diagram and MermaidDiagram components.
import { execFileSync } from 'node:child_process';
import { mkdirSync, readdirSync } from 'node:fs';
import { join, basename, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = join(root, 'src/diagrams');
const out = join(src, 'build');
mkdirSync(out, { recursive: true });

for (const file of readdirSync(src).sort()) {
	const input = join(src, file);
	if (file.endsWith('.d2')) {
		const output = join(out, basename(file, '.d2') + '.svg');
		execFileSync('d2', ['--pad', '20', input, output], { stdio: 'inherit' });
	} else if (file.endsWith('.mmd')) {
		const output = join(out, basename(file, '.mmd') + '.svg');
		execFileSync(
			join(root, 'node_modules/.bin/mmdc'),
			['--quiet', '-p', join(root, 'scripts/puppeteer.json'), '-b', 'transparent', '-i', input, '-o', output],
			{ stdio: 'inherit' },
		);
	} else {
		continue;
	}
	console.log(`diagram: ${file}`);
}
