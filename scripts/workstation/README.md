# Node60 workstation setup

`scripts/setup-workstation.sh` rebuilds the Node60 design environment of the reference Mac (an M3 MacBook Air, macOS 26.4) on another Apple-silicon Mac, then checks that the new machine reproduces the process: KiCad's `pcbnew`, KiCadRoutingTools (KRT) and its router, CI's DRC, the rule proofs, and one timed judging run compared with the Air's.

It follows the handbook's "Setting up a new Mac" (chapter 07, in the `dropout-hardware` plugin) and adds what Node60's placement process needs: KRT, its Python, `ee-skills` and the pinned versions. Where the two disagree, the user decides: a Node60 exception or a handbook change (CLAUDE.md).

It is safe to re-run. It installs only what is missing, prints `CHANGED` for each change, and never touches an existing git checkout: no checkout, pull or fetch. On the reference Mac it changes nothing.

## Use

On a new Mac, first install the Command Line Tools and Homebrew. Both ask for your password:

```bash
xcode-select --install
```

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then get this script. Before anything is cloned you can download it alone, or clone the repo by hand:

```bash
brew install gh && gh auth login
```

```bash
gh repo clone karlTbowers/node60-hw ~/Dev/node60-hw -- --recurse-submodules
```

```bash
~/Dev/node60-hw/scripts/setup-workstation.sh
```

Options:

| Option | Effect |
|---|---|
| `--check` | Change nothing. Report what is missing and what would run, then verify. |
| `--no-judge` | Skip the timed judging run (7–36 min). |
| `--extras` | Also install the reference Mac's other Homebrew packages. The process doesn't need them. |
| `--no-plugins` | Don't install the Claude Code plugins `dropout-hardware` and `kicad-happy`. |
| `--ref REF` | The node60-hw commit to verify. The default is `origin/placement/routing-readiness` (the reference run's branch), or `origin/main` if that branch is gone. |
| `--judge-out DIR` | Where the judging run goes. The default is `~/Dev/node60-judge-runs/<host>-<time>`. |

The script exits 0 only when every check passes. Warnings, such as a newer Homebrew formula than the reference, don't fail it.

## What it installs, in order

1. **Checks only:** the CPU (`arm64`, with performance and efficiency core counts), the memory, and the macOS version. It suggests how many judging runs can run at once.
2. **PATH:** only if a fresh login shell can't find `/opt/homebrew/bin/brew`. Homebrew's installer doesn't set PATH; its `.pkg` writes `/etc/paths.d/homebrew` instead. In that case the script adds a marked block to `~/.zprofile`, keeping a backup:
   ```bash
   eval "$(/opt/homebrew/bin/brew shellenv)"
   ```
   Open a new terminal afterwards.
3. **Homebrew packages** the process needs. These are the brew commands the script runs:
   ```bash
   brew install gh uv poppler git-lfs d2 node
   ```
   ```bash
   brew install --cask kicad
   ```
   The cask is used only while it is still at 10.0.7. Once it moves on, the script downloads the same `kicad-unified-universal-10.0.7.dmg` from KiCad's GitHub releases, checks its sha256, copies `KiCad` into `/Applications/KiCad` and links `kicad-cli` into `/opt/homebrew/bin`, as the cask does. With `--extras` it also runs the reference Mac's other on-request packages, which the design process doesn't use:
   ```bash
   brew install python@3.15 python-tk@3.15 numpy scipy imagemagick-full cmake ncdu sdl2_image sdl2_mixer sdl2_ttf
   ```
   ```bash
   brew install --cask inkscape blender iina pairpods
   ```
4. **GitHub and credentials:** you must have run `gh auth login` (`dropout-vendor-docs` is private). The script then runs `git lfs install`. It checks your git `user.name` and `user.email`, that `~/.local/share/dropout/vendor-logins` exists with mode 600, and that `~/.zshrc` runs `vendor-env.sh`. It never reads the credentials file, and it never edits `~/.zshrc`; those are your steps (handbook steps 5 and 8).
5. **Repos under `~/Dev`,** cloned only when missing: `node60-hw` (with the `lib/dropout-kicad-library` submodule), `dropout-hardware-handbook`, `dropout-kicad-library`, `dropout-library-catalog`, `dropout-vendor-docs` (185 LFS files) and `ee-skills` (from `charlesh97/ee-skills`).
6. **KRT** at `~/Dev/KiCadRoutingTools`: cloned from `drandyhaas/KiCadRoutingTools`, with `main` at `e91017d1`. An existing checkout at another commit gets a warning and is left alone. The Rust router `rust_router/grid_router.so` comes from `build_router.py --tag v0.23.7`, which downloads the release's `grid_router-macos-arm64.so`, checked by sha256. `rust_router/` hasn't changed between v0.23.7 and `e91017d1`, so no cargo is needed.
7. **KRT's Python** at `~/.cache/dropout/krt-venv`: `uv python install 3.12.16`, `uv venv`, then `uv pip sync` with [`krt-requirements.txt`](krt-requirements.txt) (numpy 2.5.4, scipy 1.18.1, shapely 2.2.0, pillow 13.0.0).
8. **The library's tools:** it runs `dropout-kicad-library/scripts/setup_tools.sh`, the library's own setup, which builds `~/.cache/dropout/klt-venv` with CadQuery.
9. **Claude Code plugins,** user scope, from GitHub, as in handbook step 7:
   ```bash
   claude plugin marketplace add karlTbowers/dropout-hardware-handbook && claude plugin install dropout-hardware@dropout
   ```
   ```bash
   claude plugin marketplace add aklofas/kicad-happy && claude plugin install kicad-happy@kicad-happy
   ``` For ee-skills, add `~/Dev/ee-skills/skills/pcb-placement` to a session as a folder when the skill needs it. That's how the reference Mac uses it.

## Verify ("done")

The checks run on a `git archive` export of `--ref` in a temporary folder, with the submodule's commit exported from a local clone, or fetched by hash into the temporary folder. Nothing in `~/Dev` is written, so `node60.kicad_pro` needs no restoring.

- KiCad's Python imports `pcbnew`.
- `krt-venv` imports `grid_router` (from `rust_router/`), numpy, scipy and shapely.
- CI's check, `kicad-cli pcb drc --exit-code-violations --severity-error --schematic-parity node60.kicad_pcb`, exits 0.
- `rules/prove_rules.py` passes every case.
- The handbook's own checks (step 11): the library's `setup_tools.sh --check`, `distributor_lookup.py S32K344EHT1MMMST` and `klc_check.py`. These run on the library checkout as it is, so they only warn: the first needs your API keys, and the last depends on the library branch you have checked out.
- One judging run: `judge_route.sh node60.kicad_pcb`, with `KRT_PY` set to the venv. Then `perf_report.py` reports this run beside the reference in [`reference/`](reference/). The blocking count and open nets must match the reference. That comparison only holds at the reference commit (`b6d7085`), and the script says so when `--ref` is a different commit.

## Pins

[`pins.env`](pins.env) holds every version. Some are **pinned**: the script installs exactly that version. Others are only **recorded**: Homebrew can't install an old formula, so the script installs the current one and warns if it differs.

| | Reference | |
|---|---|---|
| macOS | 26.4 (25E246) | recorded |
| Command Line Tools | 26.4.0.0.1774242506 | recorded |
| Homebrew | 7.0.12 | recorded |
| KiCad | 10.0.7 (cask, or the dmg by sha256) | pinned |
| KiCad's Python | 3.9.13 (inside KiCad.app) | pinned with KiCad |
| uv | 0.13.7 | recorded |
| node / npm | 26.13.0 / 11.20.0 | recorded |
| gh | 2.103.3 | recorded |
| git-lfs | 3.8.1 | recorded |
| poppler | current | not recorded |
| d2 | 0.9.0 | recorded |
| dropout-hardware plugin | 0.10.1 | recorded (follows the handbook's `main`) |
| kicad-happy plugin | 3.0.0 | recorded (follows its repo) |
| KRT | `e91017d1` | pinned (new clones) |
| grid_router.so | v0.23.7 macos-arm64, sha256 `4ef09467…` | pinned |
| KRT's Python | CPython 3.12.16 (uv) | pinned |
| numpy, scipy, shapely, pillow | 2.5.4, 1.18.1, 2.2.0, 13.0.0 | pinned |
| klt-venv | the library's `setup_tools.sh` | not pinned here |
| Claude Code | 2.1.314 | recorded (it updates itself) |
| Repos | their current branches | not pinned (cloned at the default branch) |

KRT's `requirements.txt` at `e91017d1` also asks for `ortools>=9.15`, for its bus step. The Node60 judging flow never runs that step and the reference venv doesn't have it, so the pin leaves it out.

## Paths

The script **recreates the reference layout** instead of making paths configurable, because the judging scripts hard-code it: `~/Dev/KiCadRoutingTools`, `~/.cache/dropout/krt-venv`, `/Applications/KiCad/KiCad.app/...` and `/opt/homebrew/bin/kicad-cli`. Paths written with `~` work for any user name.

These absolute paths remain in the repo:

- `/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3`, KiCad's Python, in `judge_route*.sh` (five), `nudge.sh`, and the run instructions of `prove_rules.py`, `draw_rule_areas.py`, `place_connectors.py`, `sync_footprint_fields.py`, `import_footprints.py`, `add_missing_footprints.py` and the skill's `SKILL.md`. Also `.../MacOS/kicad-cli`, as the fallback after `kicad-cli` on PATH, in `prove_rules.py`, `check_schematic.py`, `mcu_pinmap.py`, and the skill's `gate.py` and `grade_route.py`. The script installs KiCad there.
- `~/Dev/KiCadRoutingTools` is fixed (`KRT=`) in the five `judge_route*.sh`. The skill's `pose_search.py` takes `KRT_DIR`, and `gate.py` takes the plan's `krt`.
- **`/Users/karl`**, which breaks under any other user name:
  - `placement/2026-11-02-bars/plan.json` `krt_python`, read by the skill's `gate.py` unless `KRT_PY` is set. With another user name, set `KRT_PY=~/.cache/dropout/krt-venv/bin/python`.
  - `nudge.sh` (`cd /Users/karl/Dev/KiCadRoutingTools`, and `bosses.json` under `/Users/karl/Dev/node60-hw-place`) and the retired `route_open.sh`.
  - The `"board"` fields in `gate.json`, `baseline_rules.json`, `intent.json` and every `judge_*/rules*.json`. These are records of past runs, and nothing reads them.

The script warns when `$HOME` isn't `/Users/karl`.

## Running N judging variants at once

The router is single-threaded, and a judging run is about 90 % KRT route passes, so a Mac with N performance cores can judge N placements in about the time of one. The runs share nothing but read-only inputs: each writes only to its own output folder. KRT's own checkout gains only `py_router/__pycache__`, which Python writes safely from several processes.

```bash
cd ~/Dev/node60-hw
for v in a b c d; do
  KRT_PY=~/.cache/dropout/krt-venv/bin/python \
    zsh placement/2026-11-02-bars/judge_route.sh variants/$v.kicad_pcb runs/$v > runs/$v.out 2>&1 &
done
wait
python3 placement/2026-11-02-bars/rules/perf_report.py runs/a runs/b runs/c runs/d
```

- Run at most one per performance core (`sysctl -n hw.perflevel0.physicalcpu`): an M5 MacBook Pro or an M1 Ultra has 10 to 16 of them. The setup script prints the suggested number, which also respects memory. One run peaks at about the `maxrss_mb` in [`reference/timing.tsv`](reference/timing.tsv).
- macOS can't pin a process to a core, and doesn't need to: the scheduler puts busy default-priority threads on the performance cores. Don't use `nice`, `taskpolicy -b` or a background QoS, which push the work onto the efficiency cores.
- Give each variant its own output folder. `judge_route.sh` copies `node60.kicad_pro` and `node60.kicad_dru` from its own checkout, so variants with different rules need their own checkouts (`git worktree add`).
- Leave headroom for the grading step at the end, which runs KiCad.
