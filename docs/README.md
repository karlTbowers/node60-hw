# Node60 documentation

This folder is the Node60 documentation site ([Astro Starlight](https://starlight.astro.build/), DropOut Hardware Handbook chapter 08), published at **https://karltbowers.github.io/node60-hw/**.

| Document | Status |
|---|---|
| Architecture Rev C, 10 A variant | Baseline. Ported from the frozen single-file HTML (`public/legacy/`) on 2026-10-21 |
| Power-entry calculations (OV/UV divider, breaker, TMR) | Open |
| Thermal budget and dual-channel test plan | Open |
| Bring-up and verification checklist | Open |

## Layout

```
src/content/docs/        pages (MDX): overview, requirements, system, subsystems/, decisions, components, …
src/data/                facts with IDs: requirements.yaml, parts.yaml, gates.yaml, decisions/DEC-NNN-*.md,
                         status.yaml (overview grid), sources.yaml
src/content.config.ts    schemas; every cross-reference is checked at build time
src/diagrams/            power.d2 (dagre), signals.d2 (ELK), power-cycle.mmd (Mermaid)
src/components/          StatusGrid, RequirementTable, PartTable, GateList, DecisionList, Ref, D2Diagram, …
scripts/                 render-diagrams.mjs, parity.mjs (Rev C port check)
public/legacy/           frozen pre-Starlight documents, served as-is
```

## Build locally

Needs Node 22+ and the [`d2`](https://d2lang.com/) binary (`brew install node d2`).

```bash
cd docs
npm install
npm run dev        # renders diagrams, then serves http://localhost:4321/node60-hw/
npm run build      # renders diagrams, validates data, builds dist/
npm run parity     # after build: every MPN and number with a unit in frozen Rev C is on the site
```

To change a fact, edit its data file, not the page. A reference to an ID that doesn't exist fails the build (`<Ref id="DEC-001" />` in pages, `verified_by`, `parts`, `gates`, … in data).

Datasheets are linked from each symbol's `Datasheet` field rather than stored here.
