# Node60 workstation setup

`scripts/setup-workstation.sh` rebuilds the Node60 design environment of the reference Mac (an M3 MacBook Air, macOS 26.4) on another Apple-silicon Mac, then checks that the new machine reproduces the process: KiCad's `pcbnew`, KiCadRoutingTools (KRT) and its router, CI's DRC, the rule proofs, and one timed judging run compared with the Air's.

It follows the handbook's "Setting up a new Mac" (chapter 07, in the `dropout-hardware` plugin) and adds what Node60's placement process needs: KRT, its Python, `ee-skills`, and pinned KiCad and Python versions. Where the two disagree, the user decides: a Node60 exception or a handbook change (CLAUDE.md).

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
| `--update-krt` | Fast-forward an existing `~/Dev/KiCadRoutingTools` to `origin/main`, if it is on a clean `main`. Off by default, because other sessions' judging runs may be using that checkout. |
| `--krt-at WHICH` | KRT for the judging run. `reference` (the default) uses a temporary copy of the reference run's KRT commit, and the result must then match. `live` uses the checkout as it is, and the result is information only. |
| `--ref REF` | The node60-hw commit to verify. The default is the reference run's commit, `b6d7085` on `placement/routing-readiness`, so the comparison is like-for-like. A commit missing from your clones is fetched by hash into the temporary folder. |
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
4. **GitHub and credentials:** you must have run `gh auth login` (`dropout-vendor-docs` is private). The script then runs `git lfs install`. It checks your git `user.name` and `user.email`, that `~/.local/share/dropout/vendor-logins` exists with mode 600, and that `~/.zshrc` runs `vendor-env.sh`. It never reads the credentials file; creating it is your step (handbook step 8). Once the file exists, the script adds the handbook's line to `~/.zshrc` in a marked block, after making a backup, so the API keys reach every shell and Claude:
   ```bash
   eval "$("$HOME/Dev/dropout-kicad-library/scripts/vendor-env.sh")"
   ```
   Open a new terminal, or restart the Claude app, afterwards.
5. **Repos under `~/Dev`,** cloned only when missing: `node60-hw` (with the `lib/dropout-kicad-library` submodule), `dropout-hardware-handbook`, `dropout-kicad-library`, `dropout-library-catalog`, `dropout-vendor-docs` (185 LFS files) and `ee-skills` (from `charlesh97/ee-skills`).
6. **KRT** at `~/Dev/KiCadRoutingTools`, cloned from `drandyhaas/KiCadRoutingTools` at `origin/main`. KRT isn't pinned: it tracks its latest commit (user, 2026-11-04: KRT is under heavy development). An existing checkout is reported with its commit and how far it is behind `origin/main` as last fetched. It is moved only with `--update-krt`. The Rust router `rust_router/grid_router.so` is the published prebuilt whose version matches the checkout's `rust_router/Cargo.toml`, installed by KRT's `build_router.py`. That's the check KRT itself makes when it starts. No cargo is needed. If KRT's crate gets ahead of its last release, the script says so and fails, because that would need a source build.
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
- One judging run: `judge_route.sh node60.kicad_pcb`, with `KRT_PY` set to the venv. By default (`--krt-at reference`) it uses KRT at the reference run's commit (`e91017d1`), exported into the temporary folder with its v0.23.7 router binary. `~/Dev/KiCadRoutingTools` itself is never moved: other sessions use it, and something on the reference Mac pulls it every night (`git reflog` shows `pull --ff --recurse-submodules` on 10-30, 11-01, 11-02, 11-03 and 11-04). With the same node60-hw commit and the same KRT, a run must reproduce the reference exactly. On the Air it did: the same 330 blocking items and 113 open nets, twice. A run at KRT `87596863` gave 329, so a different KRT commit gives a different count. That's why the check holds only for the reference pair, node60-hw `b6d7085` with KRT `e91017d1`; with `--ref` or `--krt-at live`, the script shows the differences as information. The run writes `versions.txt` (host, node60-hw commit, judge script hash, KRT commit, router hash, KiCad) next to its results. Then `perf_report.py` reports this run beside the reference in [`reference/`](reference/).

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
| KRT | `origin/main` (reference run: `e91017d1`) | not pinned: tracks its latest commit |
| grid_router.so | the prebuilt matching the crate (reference: v0.23.7 macos-arm64, sha256 `4ef09467…`) | follows KRT |
| KRT's Python | CPython 3.12.16 (uv) | pinned |
| numpy, scipy, shapely, pillow | 2.5.4, 1.18.1, 2.2.0, 13.0.0 | pinned |
| klt-venv | the library's `setup_tools.sh` | not pinned here |
| Claude Code | 2.1.314 | recorded (it updates itself) |
| Repos | their current branches | not pinned (cloned at the default branch) |

KRT's `requirements.txt` (at `e91017d1` and `87596863`) also asks for `ortools>=9.15`, for its bus step. The Node60 judging flow never runs that step and the reference venv doesn't have it, so the pin leaves it out.

## Paths

The script **recreates the reference layout** instead of making paths configurable, because the judging scripts hard-code it: `~/Dev/KiCadRoutingTools`, `~/.cache/dropout/krt-venv`, `/Applications/KiCad/KiCad.app/...` and `/opt/homebrew/bin/kicad-cli`. Paths written with `~` work for any user name.

These absolute paths remain in the repo:

- `/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3`, KiCad's Python, in `judge_route.sh` and `judge_route_v1old.sh`, `nudge.sh`, and the run instructions of `prove_rules.py`, `draw_rule_areas.py`, `place_connectors.py`, `sync_footprint_fields.py`, `import_footprints.py`, `add_missing_footprints.py` and the skill's `SKILL.md`. Also `.../MacOS/kicad-cli`, as the fallback after `kicad-cli` on PATH, in `prove_rules.py`, `check_schematic.py`, `mcu_pinmap.py`, and the skill's `gate.py` and `grade_route.py`. The script installs KiCad there.
- `~/Dev/KiCadRoutingTools` is fixed (`KRT=`) in `judge_route.sh` and `judge_route_v1old.sh`. The setup script's verification points a temporary copy of `judge_route.sh` at its own KRT copy. The skill's `pose_search.py` takes `KRT_DIR`, and `gate.py` takes the plan's `krt`.
- **`/Users/karl`**, which breaks under any other user name:
  - `placement/2026-11-02-bars/plan.json` `krt_python`, read by the skill's `gate.py` unless `KRT_PY` is set. With another user name, set `KRT_PY=~/.cache/dropout/krt-venv/bin/python`.
  - `nudge.sh` (`cd /Users/karl/Dev/KiCadRoutingTools`, and `bosses.json` under `/Users/karl/Dev/node60-hw-place`) and the retired `route_open.sh`.
  - The `"board"` fields in `gate.json`, `baseline_rules.json`, `intent.json` and every `judge_*/rules*.json`. These are records of past runs, and nothing reads them.

The script warns when `$HOME` isn't `/Users/karl`.

## Running N judging variants at once

The router is single-threaded: about 94 % of a judging run is KRT's two route passes, each one core at 100 %. More cores don't make one run faster, but they run more variants in the same time. [`scripts/judge_batch.sh`](../judge_batch.sh) does this. It is written for the **M1 Ultra Mac Studio with 128 GB** (16 performance and 4 efficiency cores), which runs 14 judges at once:

```bash
cd ~/Dev/node60-hw
scripts/judge_batch.sh ~/Dev/node60-judge-runs/batch-01 variants.txt
```

`variants.txt` holds one run per line: a name, a board, and optional environment settings for `judge_route.sh`. Relative board paths are taken from the file's folder:

```
# name       board                         environment for judge_route.sh
base         ../node60.kicad_pcb
rings        ../node60.kicad_pcb           JUDGE_KEEP_RINGS=1
u401_west    u401_west.kicad_pcb
```

To run a set of boards with no extra settings, list them instead of a file: `scripts/judge_batch.sh DIR a.kicad_pcb b.kicad_pcb`. With `--repeat K`, each variant runs K times. At a fixed KRT commit the router gave identical results twice on the Air, so repeats are a check, not a way to measure spread. `-j N` overrides the number at once.

What the batch runner does:

- **Sizes the batch to the machine.** It starts min(performance cores, 0.8 × memory ÷ 7.4 GB) runs at once, and before each start it checks that the Mac has 7.4 GB free. One run peaks at 6.4–6.8 GB in the bulk `route` step and 5.4–7.3 GB in `route_p2` (the two runs on the Air; [`reference/timing.tsv`](reference/timing.tsv)), and runs started together peak together. 7.4 GB is that peak plus 10 %. Past this number the Mac swaps and every run slows.

  | Mac | P cores | Memory | At once | Limited by |
  |---|---:|---:|---:|---|
  | M3 MacBook Air (reference) | 4 | 24 GB | 2 | memory |
  | M1 Ultra Mac Studio | 16 | 64 GB | 7 | memory |
  | **M1 Ultra Mac Studio** | **16** | **128 GB** | **14** | memory, with 2 P cores and 4 E cores left for KiCad's grading step and the system |

- **Keeps the runs on the performance cores.** Runs start at normal priority, and `caffeinate` keeps the Mac from idle sleep until the batch ends. macOS can't pin a process to a core, and doesn't need to. Don't add `nice`, `taskpolicy -b` or a background QoS, which would push the runs onto the efficiency cores.
- **Shares nothing but read-only inputs.** Each run writes only to `DIR/<name>/`. After a run, KRT's checkout has nothing new except `py_router/__pycache__`, which Python writes safely from several processes. Variants that change the rules themselves (`node60.kicad_pro`, `node60.kicad_dru`) need their own checkout (`git worktree add`), because `judge_route.sh` copies the rules from the checkout it lives in. Run the batch from that checkout.
- **Records what judged each run.** `DIR/versions.txt` and each run's copy hold the host, the node60-hw commit, the judge script's hash, KRT's commit and `grid_router` version, and the Python. Each run's `env.txt` holds its settings. KRT tracks its latest commit, and something on the reference Mac pulls `~/Dev/KiCadRoutingTools` every night. So the runner records KRT's commit at the start and at the end, and warns when it moved during the batch. Compare only runs judged by the same node60-hw and KRT commits.
- **Ranks the results.** `DIR/summary.tsv` lists each variant's blocking count, open nets, wall time and peak memory, best first. `DIR/perf.md` is `perf_report.py` over every run.

Per-run speed on the Studio still needs measuring. One M1 Ultra core is slower than one M3 core, but the Studio has a fan and the Air doesn't, so the Air may slow down during a 36-minute run. Fourteen runs also share one memory system. The first batch's `summary.tsv` and `perf.md` will show the real numbers; compare them with [`reference/`](reference/).
