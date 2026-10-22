# Node60 — instructions for Claude

Node60 is DropOut's open-hardware automotive power distribution node: six protected high-side outputs (10 A target each) with current and voltage telemetry, controlled over multidrop 10BASE-T1S.

**Follows DropOut Hardware Handbook v0.2.0** (the `dropout-hardware` Claude Code plugin; working copy at `~/Dev/dropout-hardware-handbook`). Use the `dropout-standards` skill for process and conventions, `find-part` for part selection, and the library repo's `add-part` skill for new library parts. This file holds only what is specific to Node60; the handbook covers everything else.

## Board facts

- KiCad project: `node60` (`node60.kicad_pro`, `.kicad_sch`, `.kicad_pcb`) at the repo root. CI expects exactly these names.
- **Architecture:** the Starlight site in `docs/` holds Architecture Rev C (10 A variant); facts live in `docs/src/data/` (requirements, parts, decisions, gates). The original single-file Rev C is frozen at `docs/public/legacy/Node60-Architecture-RevC.html`. Its decisions are the baseline: S32K344EHT1MMMST MCU, LAN8670D0 PHY over RMII, 3 × TPS2HCS08A-Q1, LM74910H-Q1 + 0.25 mΩ RSENSE + INA228A-Q1 input, discrete INH-gated LMQ66430 power tree (no FS26), TMP175-Q1 + 4 NTCs, TPS3702-Q1 supervisor, IS25LP032D-JNLA3 log flash. Don't change an architecture decision without the user's agreement; flag conflicts instead.
- **Qualification:** AEC-Q100/Q101/Q200 Grade 1 (−40…+125 °C) for all active parts.
- **Sheet plan** (Rev C): A Power entry · B Regulators · C MCU/NVM · D T1S · E–G Outputs (one dual switch per sheet) · K Connectors.

## Deviations from the handbook

None.

## Current release blockers

- **10 A continuous is unproven.** TPS2HCS08A-Q1 is rated 8 A per channel with both channels on at 85 °C. The 10 A rating stays blocked until the dual-channel thermal test passes.
- LAN8670D0-E/LMXVAO and TPS2HCS08AQPWPRQ1 had zero distributor stock at the last observation (2026-10-13): procurement risk.
- The S32K344EHT1MMMST package ball map must be verified during schematic capture.

## Done: port Architecture Rev C to Starlight (2026-10-21)

Completed; kept for the record. Rev D is next. `npm run build && npm run parity` in `docs/` re-checks the site against the frozen Rev C.

Handbook chapter 08 makes Starlight the format for all architecture documents. Rev C (formerly `docs/architecture/Node60-Architecture-RevC.html`) is the frozen source. **This port changes the format only, not the content: the result is still Rev C.** Rev D starts afterwards.

1. **Scaffold** the Starlight project in `docs/` per chapter 08's layout; `base: "/node60-hw"`. Move the frozen HTML to `docs/public/legacy/Node60-Architecture-RevC.html` and link it from the revisions page.
2. **Extract data** from Rev C into `docs/src/data/` with content-collection schemas:
   - `requirements.yaml`: the design-basis requirements and the parameter table (`REQ-<AREA>-NNN`).
   - `parts.yaml`: every part in the component baseline, with its price and stock as **observations dated 2026-10-13**, second source, and status.
   - `decisions/DEC-NNN-*.md`: one per decision, **including rejected alternatives with reasons**. At minimum: LM74910H-Q1 over LM74800-Q1 and LM74900-Q1; INA228A-Q1 over INA281/INA240/INA229/INA186/TSC2011/PAC193x; FS26 removed in favour of discrete INH gating; TPS2HCS08A-Q1 output stage (with the 8 A both-on limit); internal SWT with no external watchdog (TPS3430 deferred, TPS3823 rejected); TPS3702-Q1 3V3 supervisor; TMP175-Q1 over TMP126-Q1; IS25LP032D-JNLA3 log flash (W25Q32JVSSSQ second source); XLD8A24CA over SMBJ24CA; T1S-only wake with controller-commanded shutdown, bus-idle timeout rejected.
   - `gates.yaml`: every verification and release gate (`GATE-<AREA>-NN`), with what it blocks.
3. **Pages** mirror Rev C sections 00–15 (overview, purpose, system, power, compute, supervision, network, outputs, temperature, harness, firmware, safety, components, interfaces, verification, sources), rendering tables from data and keeping the reasoning prose.
4. **Diagrams:** the two D2 architecture views from `docs/diagram-drafts/` (now `docs/src/diagrams/`), **power** (`power.d2`) and **signals** (`signals.d2`), with every block linking to its page: both left-to-right, power with dagre and signals with ELK (set in each file, per handbook chapter 08); the controlled power cycle (parked → wake → run → shutdown) as a Mermaid state or sequence diagram.
5. **Parity check:** a script that extracts every MPN and every number with a unit from the frozen HTML and from the built site, and lists anything missing. The port isn't done until the list is empty or each difference is explained.
6. **CI and publishing:** a `docs.yml` workflow (Node + `d2`), building on PRs and deploying `main` to GitHub Pages. GitHub Pages is already set to deploy from GitHub Actions (done by the user, 2026-10-21); the site will be at `https://karltbowers.github.io/node60-hw/`.
7. **Tag** `arch-rev-c` on the commit that completes the port.
8. **Back-port to the handbook:** extract the generic Starlight starter (config, schemas, components, empty data files, `docs.yml`) into `dropout-hardware-handbook/templates/board/docs/`, update the `new-board` skill, and bump the handbook version.
