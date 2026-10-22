# Node60 — instructions for Claude

Node60 is DropOut's open-hardware automotive power distribution node: six protected high-side outputs (10 A target each) with current and voltage telemetry, controlled over multidrop 10BASE-T1S.

**Follows DropOut Hardware Handbook v0.2.0** (the `dropout-hardware` Claude Code plugin; working copy at `~/Dev/dropout-hardware-handbook`). Use the `dropout-standards` skill for process and conventions, `find-part` for part selection, and the library repo's `add-part` skill for new library parts. This file holds only what is specific to Node60; the handbook covers everything else.

## Board facts

- KiCad project: `node60` (`node60.kicad_pro`, `.kicad_sch`, `.kicad_pcb`) at the repo root. CI expects exactly these names.
- **Architecture:** the Starlight site in `docs/` (published at https://karltbowers.github.io/node60-hw/) holds Architecture **Rev A** (10 A variant), tagged `arch-rev-a`; facts live in `docs/src/data/` (requirements, parts, decisions, gates). Its decisions are the baseline: S32K344EHT1MMMST MCU, LAN8670D0 PHY over RMII, 3 × TPS2HCS08A-Q1, LM74910H-Q1 + 0.25 mΩ RSENSE + INA228A-Q1 input, discrete INH-gated LMQ66430 power tree (no FS26), TMP175-Q1 + 4 NTCs, TPS3702-Q1 supervisor, IS25LP032D-JNLA3 log flash. Don't change an architecture decision without the user's agreement; flag conflicts instead.
- **Qualification:** AEC-Q100/Q101/Q200 Grade 1 (−40…+125 °C) for all active parts.
- **Sheet plan** (Rev A): A Power entry · B Regulators · C MCU/NVM · D T1S · E–G Outputs (one dual switch per sheet) · K Connectors.

## Deviations from the handbook

One-time exceptions, decided by the user on 2026-10-22 when the first complete architecture was renumbered from Rev C to **Rev A** (earlier drafts were incomplete and are not revisions):

- The tag `arch-rev-c` was deleted and replaced by `arch-rev-a` (chapter 02 says tags are never moved or deleted).
- The single-file HTML architecture document (labelled Rev C) was deleted rather than kept as a frozen record (chapter 08). It remains in git history, last at commit `a9f418b` (`docs/public/legacy/Node60-Architecture-RevC.html`).

The next architecture revision is **Rev B**.

## Current release blockers

- **10 A continuous is unproven.** TPS2HCS08A-Q1 is rated 8 A per channel with both channels on at 85 °C. The 10 A rating stays blocked until the dual-channel thermal test passes.
- LAN8670D0-E/LMXVAO and TPS2HCS08AQPWPRQ1 had zero distributor stock at the last observation (2026-10-13): procurement risk.
- The S32K344EHT1MMMST package ball map must be verified during schematic capture.

## History

- 2026-10-21: the architecture (then labelled Rev C) was ported from a single-file HTML document to the Starlight site without content changes; a parity script checked every MPN and number with a unit against the original. The generic starter was back-ported to the handbook board template (v0.3.0).
- 2026-10-22: renumbered to Rev A; the original HTML and the parity script were removed.
