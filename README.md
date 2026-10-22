# Node60 — Automotive 10BASE-T1S Power Distribution Node

Open-hardware six-output automotive power distribution node by DropOut. Each output is a protected smart high-side switch with current and voltage telemetry, reported over a multidrop 10BASE-T1S network.

**Status:** Architecture Rev A, schematic capture starting. Not yet validated hardware.

**Architecture and design documentation:** https://karltbowers.github.io/node60-hw/ (source in [`docs/`](docs/)).

| | |
|---|---|
| MCU | NXP S32K344 |
| Network | Microchip LAN8670 10BASE-T1S PHY (RMII), PLCA follower |
| Outputs | 6 × 10 A target, 3 × TI TPS2HCS08A-Q1 dual smart eFuses |
| Input | 12 V battery-direct, TI LM74910H-Q1 ideal diode + 75 A breaker |
| Tools | KiCad 10, Zephyr RTOS (firmware in a separate repo) |

## Cloning

The DropOut part library is a git submodule, so clone recursively:

```bash
git clone --recursive https://github.com/karlTbowers/node60-hw.git
```

Already cloned without it? Run `git submodule update --init`.

## Layout

```
node60.kicad_pro / .kicad_sch / .kicad_pcb    KiCad 10 project; node60.kicad_sch is the root sheet (page 1, index)
sheets/                                       every other schematic sheet, flat (handbook ch. 05)
scripts/check_schematic.py                    CI check: sheet files, page numbers, reference designators
sym-lib-table, fp-lib-table                   point into lib/ — do not use global DropOut tables
lib/dropout-kicad-library/                    submodule: symbols, footprints, 3D models
docs/                                         Starlight documentation site: architecture, calculations, test plans
.github/workflows/ci.yml                      ERC/DRC on every push; fab outputs on tags
.github/workflows/docs.yml                    builds docs/ on PRs; deploys main to GitHub Pages
```

## Library

All parts come from [dropout-kicad-library](https://github.com/karlTbowers/dropout-kicad-library). The project library tables use `${KIPRJMOD}/lib/dropout-kicad-library/...`, so nothing needs to be configured in KiCad's global settings.

Update the library:

```bash
git -C lib/dropout-kicad-library pull origin main
git add lib/dropout-kicad-library
git commit -m "Update DropOut library"
```

## Releases

Board revisions are git tags: `rev-a`, `rev-b`, … Pushing a tag makes CI run ERC and DRC and attach the fabrication package (Gerbers, drill, position file, BOM, schematic PDF) to a GitHub Release.

```bash
git tag rev-a && git push origin rev-a
```

## License

TBD — to be chosen before the first public release.
