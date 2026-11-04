#!/usr/bin/env python3
"""Where a fast-route judging run spends its time (user, 2026-11-03: find the design loop's
bottlenecks). Standard library only.

    python3 placement/2026-11-02-bars/rules/perf_report.py RUN_DIR [RUN_DIR ...] [--md OUT.md]

RUN_DIR is a judge_route.sh output folder. Steps run with PROFILE=<step,...> leave <step>.prof,
whose hottest functions (own time) are listed too. With `timing.tsv` (judge_route.sh times every step
since 2026-11-03) it reports per step: wall seconds, share of the run, CPU seconds (user + sys),
CPU use (CPU / wall; about 100 % is one core busy, over 100 % is several), and peak memory. Each
step's own timing keys from KRT's JSON_SUMMARY lines in chain.log (any numeric key with "time"
in its name) are listed under it, to show where inside a step the time goes.

Without timing.tsv (runs before the instrumentation) it falls back to the intermediate boards'
modification times: s1 = planes, s2 = all fan-outs and the decap pass's input, s3 = decap and
crystal, s4 = T1S pair and the PHY's first nets, s5 = bulk route, s6 = second pass, grade.txt =
grading. That is coarse (several steps share a file) and has no CPU or memory figures; it says so.
"""
import argparse
import json
import os
import re
import sys

CORES = os.cpu_count() or 1


def krt_times(chain):
    """{step: {key: seconds}} from JSON_SUMMARY lines inside each '== step:' block"""
    out, cur = {}, None
    if not os.path.exists(chain):
        return out
    for line in open(chain, errors="replace"):
        m = re.match(r"== ([^:]+): ", line)
        if m:
            cur = m.group(1)
            continue
        if cur and line.startswith(("JSON_SUMMARY: ", "JSON_SUMMARY_MIN: ")):
            try:
                d = json.loads(line.split(": ", 1)[1])
            except ValueError:
                continue
            stack = [("", d)]
            while stack:
                pre, x = stack.pop()
                if isinstance(x, dict):
                    for k, v in x.items():
                        key = f"{pre}{k}"
                        if isinstance(v, (int, float)) and not isinstance(v, bool) and "time" in k.lower():
                            out.setdefault(cur, {})[key] = max(v, out.get(cur, {}).get(key, 0))
                        elif isinstance(v, dict):
                            stack.append((key + ".", v))
    return out


def from_tsv(run):
    rows = []
    for line in open(os.path.join(run, "timing.tsv")):
        f = line.rstrip("\n").split("\t")
        if f[0] in ("step",) or len(f) < 2:
            continue
        num = lambda x: float(x) if x not in ("", None) else None
        rows.append(dict(step=f[0], wall=num(f[1]), user=num(f[2]) if len(f) > 2 else None,
                         sys=num(f[3]) if len(f) > 3 else None, rss=num(f[4]) if len(f) > 4 else None))
    return rows, "measured (timing.tsv)"


def from_mtimes(run):
    st = os.stat(run)
    t0 = getattr(st, "st_birthtime", None) or os.path.getmtime(os.path.join(run, "s0.kicad_pcb"))
    marks = [("prep (s0)", "s0.kicad_pcb"), ("planes (s1)", "s1.kicad_pcb"), ("fan-outs (s2)", "s2.kicad_pcb"),
             ("decap + crystal (s3)", "s3.kicad_pcb"), ("T1S pair + PHY first (s4)", "s4.kicad_pcb"),
             ("bulk route (s5)", "s5.kicad_pcb"), ("second pass (s6)", "s6_before_p3.kicad_pcb"),
             ("grade", "grade.txt")]
    rows, last = [], t0
    for name, f in marks:
        p = os.path.join(run, f)
        if f == "s6_before_p3.kicad_pcb" and not os.path.exists(p):
            p = os.path.join(run, "s6.kicad_pcb")
        if not os.path.exists(p):
            continue
        t = os.path.getmtime(p)
        rows.append(dict(step=name, wall=max(t - last, 0.0), user=None, sys=None, rss=None))
        last = t
    rows.append(dict(step="TOTAL", wall=last - t0, user=None, sys=None, rss=None))
    return rows, "estimated from file times (no CPU or memory figures)"


def report(run):
    rows, how = from_tsv(run) if os.path.exists(os.path.join(run, "timing.tsv")) else from_mtimes(run)
    steps = [r for r in rows if r["step"] != "TOTAL"]
    total = next((r["wall"] for r in rows if r["step"] == "TOTAL"), None) or sum(r["wall"] or 0 for r in steps)
    kt = krt_times(os.path.join(run, "chain.log"))
    out = [f"### {os.path.basename(os.path.normpath(run))}", "",
           f"{how}; {CORES} cores on this machine; run total {total / 60:.1f} min", "",
           "| step | wall | share | CPU s | CPU use | peak MB |", "|---|---:|---:|---:|---:|---:|"]
    for r in sorted(steps, key=lambda r: -(r["wall"] or 0)):
        cpu = (r["user"] or 0) + (r["sys"] or 0) if r["user"] is not None else None
        use = f"{100 * cpu / r['wall']:.0f} %" if cpu is not None and r["wall"] else ""
        out.append(f"| {r['step']} | {r['wall']:.0f} s | {100 * r['wall'] / total:.0f} % | "
                   f"{'' if cpu is None else f'{cpu:.0f}'} | {use} | {'' if r['rss'] is None else f'{r[chr(114)+chr(115)+chr(115)]:.0f}'} |")
    acc = sum(r["wall"] or 0 for r in steps)
    if total and acc < total * 0.98:
        out.append(f"| (outside the timed steps: board prep, file copies) | {total - acc:.0f} s | {100 * (total - acc) / total:.0f} % | | | |")
    inner = [(s, k, v) for s, d in kt.items() for k, v in d.items() if v >= 1]
    if inner:
        out += ["", "KRT's own timings inside steps (seconds, from JSON_SUMMARY):", ""]
        for s, k, v in sorted(inner, key=lambda x: -x[2])[:15]:
            out.append(f"- {s}: `{k}` {v:.1f}")
    for prof in sorted(f for f in os.listdir(run) if f.endswith(".prof")):
        out += ["", f"Hottest functions in {prof[:-5]} (cProfile, cumulative seconds; profiling slows a step by roughly 1.5x):", ""]
        out += profile_top(os.path.join(run, prof))
    return "\n".join(out)


def profile_top(path, n=15):
    """the n functions with the most own time, then the n with the most cumulative time (pstats)"""
    import pstats
    st = pstats.Stats(path)
    rows = []
    for (fn, line, name), (cc, nc, tt, ct, _) in st.stats.items():
        rows.append((tt, ct, nc, f"{os.path.relpath(fn, os.path.expanduser('~')) if fn.startswith('/') else fn}:{line} {name}"))
    lines = ["| own s | cumulative s | calls | function |", "|---:|---:|---:|---|"]
    for tt, ct, nc, where in sorted(rows, key=lambda r: -r[0])[:n]:
        lines.append(f"| {tt:.1f} | {ct:.1f} | {nc} | `{where}` |")
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--md", help="also write the report to this Markdown file")
    a = ap.parse_args()
    text = "\n\n".join(report(r) for r in a.runs if os.path.isdir(r))
    print(text)
    if a.md:
        open(a.md, "w").write(text + "\n")


if __name__ == "__main__":
    sys.exit(main())
