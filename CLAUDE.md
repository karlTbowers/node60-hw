# Node60 — instructions for Claude

Node60 is DropOut's open-hardware automotive power distribution node: six protected high-side outputs (10 A target each) with current and voltage telemetry, controlled over multidrop 10BASE-T1S.

**Follows DropOut Hardware Handbook v0.10.0** (updated from v0.4.0 on 2026-10-29) (the `dropout-hardware` Claude Code plugin; working copy at `~/Dev/dropout-hardware-handbook`). Use the `dropout-standards` skill for process and conventions, `find-part` for part selection, and the library repo's `add-part` skill for new library parts. This file holds only what is specific to Node60; the handbook covers everything else.

## Board facts

- KiCad project: `node60` (`node60.kicad_pro`, `.kicad_sch`, `.kicad_pcb`) at the repo root. CI expects exactly these names.
- **Architecture:** the Starlight site in `docs/` (published at https://karltbowers.github.io/node60-hw/) holds Architecture **Rev A** (10 A variant), tagged `arch-rev-a`; facts live in `docs/src/data/` (requirements, parts, decisions, gates). Its decisions are the baseline: S32K344EHT1MMMST MCU, LAN8670D0 PHY over RMII, 3 × TPS2HCS08A-Q1, LM74910H-Q1 + 0.25 mΩ RSENSE + INA228A-Q1 input, discrete INH-gated LMQ66430 power tree (no FS26), TMP175-Q1 + 4 NTCs, TPS3702-Q1 supervisor, IS25LP032D-JNLA3 log flash. Don't change an architecture decision without the user's agreement; flag conflicts instead.
- **Rev B in progress** (accepted on `main`, not yet tagged): DEC-012 rev. B (T1S line order), DEC-018 (one LPSPI bus per output switch: U601 = LPSPI4, U701 = LPSPI5, U801 = LPSPI3, SPI watchdog limp-home off), DEC-019 (Zephyr is the core RTOS; pin-plan rules for EIRQ lines, ADC channel groups and native PCS chip selects), DEC-021 (board component side up, 2.6 mm thick; busbars under the SurLok receptacles; lid with a raised T; T1S on the north wall; supersedes DEC-020, which mounted the board component side down).
- **Enclosure options (2026-10-30):** eight candidate mechanical versions are kept until one is chosen; each is a parameter set in `VERSIONS` in `scripts/place_connectors.py` (v1 = DEC-020 flipped board; v2 = DEC-021; v3 = T1S on the side walls by the outputs, one raised front band, staggered receptacles; v4/v5 = v2/v3 with REDCUBE press-fit 786202106 and the busbars on the blocks; v6 = v2 with two outputs on each of the west, south and east walls, the side-wall ones in the corners, a raised front band plus raised back corners and T1S hood, staggered receptacles between them, board 139 mm deep (`depth`); v7 = v2 without the T's stem: a raised front band and a separate hood over the T1S pair, receptacles placed as v6's in x (battery 52 mm, return 78 mm from the centre line, so a north cable clears the T1S hood) on the 160 mm board; v8 = v7 plus an MCU board under the main board carrying the T1S pair through a notch in the main board, 10 mm board gap, no T1S hood; not placeable until the design is split into two boards). `scripts/enclosure_versions.py` draws them all at docs build time (site: Enclosure options), `check_surlok_clearance.py` checks all of them, and the 3D mockup switches between them. The PCB holds `CURRENT` (v2); `place_connectors.py <netlist> vN` places another.
- **PCB and enclosure (DEC-021, 2026-10-30, supersedes DEC-020):** 2.6 mm thick, outline 250 × 160 mm (provisional), component side up, so KiCad's top view is the view from above. Outputs J904–J909 on the front edge at a 40 mm pitch; T1S J903/J912 in the middle of the north edge, 41 mm apart (45 until 2026-10-31; versions 6–8 keep 45). REDCUBE 74660016R on B.Cu; a 1/8" × 1" C110 copper busbar on the top face joins each power pair (outlines on User.Drawings, no parts under them); the SurLok receptacles sit on the busbars in two low sections of a lid with a raised T over the headers. Plugs point outward or north; battery receptacles 57.5 mm and return 78.7 mm from the centre line (staggered 2026-10-31, so a north cable passes beside the return receptacle). Open: the SurLok stud length (decides the busbar thickness), header pin tails on 2.6 mm, stackup and fab house. `scripts/place_connectors.py` places J901–J912 and the outline from positions written as seen from above the lid; `scripts/check_surlok_clearance.py` checks each version's allowed plug directions against the plugs, flanges and raised sections, the flanges against each other, and each plug's cable (11 mm, assumed) against the raised sections and the other receptacles and plugs (v1 fails it and is left as DEC-020's record), and that a plug pointing west or east stays inside the walls. The 3D enclosure mockup is `docs/src/mockups/node60-enclosure.html`; the docs build fills in every version's geometry from `enclosure-versions.json` (`docs/scripts/wrap-mockups.mjs`, also `--fill` for the artifact copy), so it shows the same designs as the drawings. The dimensioned enclosure drawing on the site's Enclosure & mechanical page follows the handbook's `enclosure-drawing` skill: `scripts/enclosure_drawing.py` is the skill's engine (copied; re-copy to update) and draws at docs build time (via `scripts/enclosure_versions.py`) from `scripts/enclosure_geometry.py`, whose `spec(version)` reads the positions from `place_connectors.py` and holds the enclosure assumptions (wall, gaps) and the panel cutouts. Edit those, not the SVGs; `python3 scripts/enclosure_drawing.py scripts/enclosure_geometry.py --check` checks the cutouts. Open: AT13/ATM13 pin tails leave only 0.1–0.5 mm on 2.6 mm; stackup and fab house not chosen.
- **Qualification:** AEC-Q100/Q101/Q200 Grade 1 (−40…+125 °C) for all active parts.
- **Sheet plan** (Rev A) → schematic pages: 1 root/index · A Power entry = p2 (`sheets/power-entry.kicad_sch`) · B Regulators = p3 · C MCU/NVM = p4 · D T1S = p5 · E–G Outputs 1-2 / 3-4 / 5-6 = p6–p8 (one file, `sheets/output-switch.kicad_sch`, placed three times) · K Connectors = p9. Reference designators follow the page (R201 on page 2); the project's annotation is set to sheet number × 100.

## Schematic project answers

Handbook chapter 05 asks seven project questions. Questions 1–4: the user accepted the defaults on 2026-10-22. Questions 5–7: answered 2026-10-22 (5) and 2026-10-29 (6, 7).

- **0201 passives:** not used; 0402 minimum.
- **Signal test points:** 1 mm exposed pads. Ground test points are probe loops.
- **0R debug resistors:** on every regulator output (VDDAU_AON, 3V3_MAIN, 1V5_CORE), with feedback taken on the regulator side.
- **Debug header:** 2 × 5 1.27 mm Cortex Debug (Samtec FTSH-105, in the library).
- **Ambient range and grade:** −40…+125 °C, AEC-Q100/Q101/Q200 Grade 1 (architecture requirement REQ-QUAL-001). Parts with no AEC qualification (connectors, relays, terminals, crystals) must still be rated to +125 °C.
- **Environment:** sealed enclosure (IP67 target; the AT13, ATM13 and SurLok Plus connectors are IP67 mated) in a vehicle, condensation possible inside, automotive vibration and shock (GATE-THM-02). No conformal coating for now. Power-entry sealing is still open (DEC-016).
- **Capacitor dielectrics:** X7R, X7S, X8R and C0G only; no X5R, Y5V or Z5U. C0G where the value sets a timing, filter or oscillator (handbook chapter 05). On the board today: X7R and C0G.
- **Passive text on the sheets (2026-10-29/30):** every two-terminal passive shows its pin numbers (library PR #38), value, ratings and MPN. Placed symbols stack them as Reference / Value / ratings two per row / MPN at 0.8 mm; where room is short the text may move to another side, go smaller or onto fewer, longer rows (user's call). Groups were spaced out so no text overprints; T1S (p5) is A1 since.

Net names: Node60 keeps its Rev A rail names (`VBAT_PROT`, `VDDAU_AON`, `3V3_MAIN`, `1V5_CORE`), as rule O-1 allows. Everything else follows the new naming: active-low signals end in `_L`, buses are `<BUS><n>_<PURPOSE>_<SIGNAL>` (`I2C0_TELEMETRY_SDA`), differential pairs end in `_P` / `_N`. The architecture site uses the same net names (2026-10-28); the device pin names map to them in the table on its interfaces page.

## Schematic review answers (2026-10-28)

The user settled the open questions from the first schematic draft:

- **LM74910H:** OV cut-off 34.0 V, UVLO 5.47 V falling, SLEEP_OV on OUT. Accepted.
- **TPS3702AX33:** SET low, 3.10 / 3.50 V window on 3V3_MAIN. Accepted.
- **MCU clock:** fit a 16 MHz crystal on FXOSC (DEC-015). The user chose Abracon ABM8AIG-16.000MHZ-8-1Z-T (Y401), with 10 pF C0G loads and a 0 Ω RsEXT, as on NXP's FRDM-A-S32K344.
- **PHY reset:** RESET_N stays on RESET_L, shared with the MCU. Measure the MCU's reset hold time at GATE-NET-01.
- **EMI filter:** regulator branch only (VBAT_PROT to VBAT_FILT). L201/C208 values follow the emissions test.
- **Parked current:** TPS7B8133-Q1 (3.5 µA) stays; the parked budget is ≈52 µA typical.
- **TMP175:** VSSOP (DGK) package.
- **Page order:** Rev A page numbers stay.
- **Connector pin 1:** confirmed on samples (GATE-HAR-01). Blocks board release, not the schematic or layout.
- **GATE-MCU-01:** passed 2026-10-28. All 257 balls cross-checked against NXP's IOMUX table, IBIS model and BSDL file; the user signed off. Re-run for DEC-018's eight new balls and signed off 2026-10-30. Re-run it if U401's pin plan changes.

## Deviations from the handbook

One-time exceptions, decided by the user on 2026-10-22 when the first complete architecture was renumbered from Rev C to **Rev A** (earlier drafts were incomplete and are not revisions):

- The tag `arch-rev-c` was deleted and replaced by `arch-rev-a` (chapter 02 says tags are never moved or deleted).
- The single-file HTML architecture document (labelled Rev C) was deleted rather than kept as a frozen record (chapter 08). It remains in git history, last at commit `a9f418b` (`docs/public/legacy/Node60-Architecture-RevC.html`).

The next architecture revision is **Rev B**.

Temporary, decided by the user on 2026-10-30 (PR #21):

- **Unrouted connections are DRC warnings, not errors**, while layout is in progress: `node60.kicad_pro` sets `rule_severities.unconnected_items` to `warning`, so CI's DRC (errors fail, chapter 06) passes on an unrouted board while every other DRC and parity error still fails. Set it back to `error` (delete the override) before routing is signed off and before any `rev-*` tag. If KiCad is open on the project, saving the board settings may rewrite this; check the diff.

## Current release blockers

- **10 A continuous is unproven.** TPS2HCS08A-Q1 is rated 8 A per channel with both channels on at 85 °C. The 10 A rating stays blocked until the dual-channel thermal test passes.
- LAN8670D0-E/LMXVAO and TPS2HCS08AQPWPRQ1 had zero distributor stock at the last observation (2026-10-13): procurement risk.
- Output and T1S connector pin 1 must be confirmed on AT13/ATM13 samples (GATE-HAR-01).
- T1S termination relay G6KU-2F-Y-T1-TRS DC3 (DEC-017) had no stock at DigiKey or Mouser on 2026-10-28 (reel MOQ 900 at DigiKey).
- Power entry (DEC-016): the downstream pass-through is limited to 40 A (provisional, 60 A target) until GATE-HAR-02 proves the current path; power-entry sealing is not decided. 74660016R is listed only at Mouser, with no stock figure (2026-10-28).

## History

- 2026-10-21: the architecture (then labelled Rev C) was ported from a single-file HTML document to the Starlight site without content changes; a parity script checked every MPN and number with a unit against the original. The generic starter was back-ported to the handbook board template (v0.3.0).
- 2026-10-22: renumbered to Rev A; the original HTML and the parity script were removed.
