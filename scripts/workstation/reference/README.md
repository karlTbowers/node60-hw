# Reference judging run

`judge_route.sh node60.kicad_pcb` at node60-hw `b6d7085193df990d04e49bf4cd03ee5e9f5c3683` (`placement/routing-readiness`, 2026-11-03), run on 2026-11-03 on the reference Mac. The run had the machine to itself, with `KRT_PY=~/.cache/dropout/krt-venv/bin/python` and the environment in [`../pins.env`](../pins.env).

| | |
|---|---|
| Mac | MacBook Air Mac15,13, Apple M3, 4 performance + 4 efficiency cores, 24 GB |
| macOS | 26.4 (25E246); on battery, Low Power Mode off (the Air has no fan, so a long run may throttle) |
| Wall time | 2160 s (36.0 min): `route` 1297 s and `route_p2` 729 s are 94 % of it, each one core at 100 % |
| Peak memory | 6769 MB (`route`) |
| Result | blocking 330, of which 297 unconnected items in 113 open nets, plus D12 rule hits (`grade.txt`) |

The high blocking count is this commit's real result under the D12 routing rules. The branch's own D12 runs show the same order (`judge_d12` 379, `judge_d12_win` 372, `judge_v1cmp` 400). It is not a broken run.

Files: `versions.txt` (what judged it, in the format the setup script writes); `timing.tsv` and `rules.json` as the run wrote them; `grade.txt` with KiCad's log noise filtered out; `chain.log` cut down to the step headers and the timing keys of KRT's `JSON_SUMMARY` lines. That is all `perf_report.py` reads, and its report from this folder is identical to the one from the full 4.9 MB log. Paths are shortened to `<export>` and `<out>`.

Repeated on 2026-11-04 by the setup script with the same node60-hw commit and the same KRT commit: 330 blocking (2101 s), then 329 (2363 s). A run with KRT at `87596863` also gave 329. All four runs had the same 113 open nets; the 329s have one clearance violation fewer. So KRT isn't bit-for-bit repeatable, and the setup script accepts a blocking count within max(2, 1 %) when the open nets are identical.
