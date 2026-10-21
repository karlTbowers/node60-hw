# Node60 — instructions for Claude

Node60 is DropOut's open-hardware automotive power distribution node: six protected high-side outputs (10 A target each) with current and voltage telemetry, controlled over multidrop 10BASE-T1S. Designed in **KiCad 10**. The repo is **public**.

## Source of truth

- **Architecture:** `docs/architecture/` holds the Architecture Rev C (10 A variant). Its decisions are the baseline: S32K344EHT1MMMST MCU, LAN8670D0 PHY over RMII, 3 × TPS2HCS08A-Q1, LM74910H-Q1 + 0.25 mΩ RSENSE + INA228A-Q1 input, discrete INH-gated LMQ66430 power tree (no FS26), TMP175-Q1 + 4 NTCs, TPS3702-Q1 supervisor, IS25LP032D-JNLA3 log flash. Do not change an architecture decision without the user's agreement; flag conflicts instead.
- **Release blocker to keep in mind:** TPS2HCS08A-Q1 is rated 8 A per channel with both channels on at 85 °C, so the 10 A rating is unproven until thermal tests pass.

## Project layout and conventions

- KiCad project name is **`node60`** (`node60.kicad_pro`, `.kicad_sch`, `.kicad_pcb`) at the repo root. CI looks for exactly these names.
- Schematic sheets follow the Rev C capture plan: A Power entry · B Regulators · C MCU/NVM · D T1S · E–G Outputs (one dual switch per sheet) · K Connectors.
- **Parts come only from the DropOut library** at `lib/dropout-kicad-library` (git submodule). The project's `sym-lib-table` and `fp-lib-table` reference it via `${KIPRJMOD}/lib/dropout-kicad-library/...`. Never use global libraries or KiCad stock parts on this board. If a part is missing, add it to the librarian copy at `~/Dev/dropout-kicad-library` (follow that repo's `CLAUDE.md`), merge it, then update the submodule here:
  ```bash
  git -C lib/dropout-kicad-library pull origin main
  git add lib/dropout-kicad-library && git commit -m "Update DropOut library"
  ```
- Don't commit `*.kicad_prl`, backups, `fp-info-cache`, or generated outputs (see `.gitignore`).

## CI and releases

- `.github/workflows/ci.yml` runs ERC and DRC (with schematic parity) on every push and PR, and exports PDF, BOM (MPN / DigiKey / Mouser columns), Gerbers, drill, positions, and STEP.
- Board revisions are tags `rev-a`, `rev-b`, …; pushing one creates a GitHub Release with the fab package.
- Before pushing schematic or PCB changes, run ERC/DRC locally with `kicad-cli` if available.

## Tools available on this Mac

- **kicad-happy** skills (schematic analysis, BOM, DigiKey, Mouser, element14, SPICE).
- **Konnect** KiCad 10 MCP for live project and board edits (needs KiCad running).
- Distributor API keys reach the environment via `~/Dev/dropout-kicad-library/scripts/vendor-env.sh`. Credentials live in `~/.local/share/dropout/vendor-logins`: never print, commit, or `source` it.
