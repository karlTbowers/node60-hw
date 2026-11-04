#!/bin/zsh
# judge_batch.sh -- run many fast-route judging runs at once, one per performance core, as many as
# memory allows (made for the M1 Ultra Mac Studio, 16 P cores and 128 GB: 14 at once).
#
#   scripts/judge_batch.sh [options] BATCH_DIR VARIANTS_FILE
#   scripts/judge_batch.sh [options] BATCH_DIR BOARD.kicad_pcb [BOARD.kicad_pcb ...]
#
#   VARIANTS_FILE: one run per line, "name  board.kicad_pcb  [VAR=value ...]"; '#' starts a comment.
#   The VAR=value pairs go into that run's environment (judge_route.sh reads PLANE_NETS,
#   PLANE_LAYERS, LAYER_COSTS, JUDGE_KEEP_RINGS, PROFILE, ...). Relative board paths are taken
#   from the variants file's folder.
#
#   -j N          runs at once (default: min(P cores, 0.8 x memory / 7.4 GB); printed at the start)
#   --repeat K    run every variant K times (name.r1 ... name.rK): KRT isn't bit-for-bit repeatable,
#                 so repeats show the spread
#   --judge PATH  the judge script (default: placement/2026-11-02-bars/judge_route.sh in the git
#                 checkout you run this from, so its rules and .kicad_pro/.kicad_dru are that checkout's)
#
# Each run goes to BATCH_DIR/<name>/ (judge_route.sh's own outputs, plus run.out, versions.txt and
# env.txt). At the end: BATCH_DIR/summary.tsv (ranked by blocking count) and BATCH_DIR/perf.md.
# The runs share nothing but read-only inputs. Every run uses ~/Dev/KiCadRoutingTools as checked
# out; its commit is recorded before and after, and a change during the batch is reported.
emulate zsh
setopt pipe_fail no_unset
J=0 REPEAT=1 JUDGE=""
while [[ ${1:-} == -* ]]; do
  case $1 in
    -j) J=$2; shift ;;
    --repeat) REPEAT=$2; shift ;;
    --judge) JUDGE=$2; shift ;;
    -h|--help) sed -n '2,24p' $0; exit 0 ;;
    *) print -u2 "unknown option $1"; exit 2 ;;
  esac
  shift
done
(( $# >= 2 )) || { sed -n '2,24p' $0; exit 2; }
BATCH=${1:A}; shift
TOP=$(git rev-parse --show-toplevel 2>/dev/null) || { print -u2 "run this from a node60-hw checkout"; exit 2; }
[[ -z $JUDGE ]] && JUDGE=$TOP/placement/2026-11-02-bars/judge_route.sh
JUDGE=${JUDGE:A}
[[ -f $JUDGE ]] || { print -u2 "no judge script at $JUDGE"; exit 2; }
PERF=${JUDGE:h}/rules/perf_report.py
KRT=$HOME/Dev/KiCadRoutingTools
export KRT_PY=${KRT_PY:-$HOME/.cache/dropout/krt-venv/bin/python}
[[ -x $KRT_PY ]] || { print -u2 "KRT_PY $KRT_PY isn't there (scripts/setup-workstation.sh)"; exit 2; }

# --- the variants: names, boards, environments -------------------------------------------------
names=() boards=() envs=()
add() { local n=$1 b=$2; shift 2
  local k; for (( k = 1; k <= REPEAT; k++ )); do
    names+=( $([[ $REPEAT == 1 ]] && print $n || print $n.r$k) ); boards+=( ${b:A} ); envs+=( "$*" )
  done
}
if [[ $# == 1 && $1 != *.kicad_pcb ]]; then
  VF=${1:A}
  while read -r line; do
    line=${line%%\#*}; [[ -z ${line// } ]] && continue
    w=( ${=line} )
    b=${w[2]}; [[ $b == /* ]] || b=${VF:h}/$b
    add ${w[1]} $b ${w[3,-1]}
  done < $VF
else
  for b in "$@"; do add ${${b:t}%.kicad_pcb} $b; done
fi
(( ${#names} )) || { print -u2 "no variants"; exit 2; }
for b in $boards; do [[ -f $b ]] || { print -u2 "no board $b"; exit 2; }; done
[[ ${#${(u)names}} == ${#names} ]] || { print -u2 "variant names must be unique"; exit 2; }

# --- how many at once ------------------------------------------------------------------------
P=$(sysctl -n hw.perflevel0.physicalcpu)
MEM_MB=$(( $(sysctl -n hw.memsize) / 1048576 ))
RUN_MB=7400   # one run's peak (reference timing.tsv: 6.8 GB in route, up to 7.3 GB in route_p2) + 10 %
FIT=$(( MEM_MB * 8 / 10 / RUN_MB )); (( FIT < 1 )) && FIT=1
(( J > 0 )) || J=$(( P < FIT ? P : FIT ))
free_mb() {   # memory the system can hand out now: free + inactive + speculative + purgeable pages
  vm_stat | awk -v ps=$(pagesize) '/Pages (free|inactive|speculative|purgeable)/ {gsub("\\.","",$NF); n+=$NF} END {print int(n*ps/1048576)}'
}

mkdir -p $BATCH
krt_head() { git -C $KRT rev-parse HEAD 2>/dev/null || print unknown; }
KRT0=$(krt_head)
ROUTER=$(cd $KRT && $KRT_PY -c 'import sys; sys.path.insert(0, "rust_router"); import grid_router; print(grid_router.__version__)' 2>/dev/null || print '?')
{
  print "host\t$(hostname -s) $(sysctl -n hw.model) $(sysctl -n machdep.cpu.brand_string), $P P + $(sysctl -n hw.perflevel1.physicalcpu) E cores, $(( MEM_MB / 1024 )) GB"
  print "node60_commit\t$(git -C $TOP rev-parse HEAD)$([[ -n $(git -C $TOP status --porcelain -- ${JUDGE:h} $TOP/node60.kicad_pro $TOP/node60.kicad_dru 2>/dev/null) ]] && print ' (uncommitted changes in the judge folder or rules)')"
  print "judge\t$JUDGE  git blob $(git hash-object $JUDGE)"
  print "krt_commit\t$KRT0"
  print "grid_router\t$ROUTER  sha256 $(shasum -a 256 $KRT/rust_router/grid_router.so | cut -c1-12)"
  print "krt_python\t$KRT_PY"
  print "jobs\t$J at once, ${#names} runs, started $(date '+%Y-%m-%d %H:%M:%S')"
} > $BATCH/versions.txt
print "judge_batch: ${#names} runs, $J at once ($P P cores; $(( MEM_MB / 1024 )) GB fits $FIT at ${RUN_MB} MB each) -> $BATCH"
print "  KRT ${KRT0:0:8} (grid_router $ROUTER), judge ${JUDGE#$TOP/}"

# Keep the Mac awake (no idle sleep) while the batch runs. Don't nice the runs or give them a
# background QoS: macOS would move them to the efficiency cores.
caffeinate -i -w $$ &

typeset -A PIDS T0
start() {
  local i=$1 n=${names[$1]} out=$BATCH/${names[$1]}
  mkdir -p $out
  cp $BATCH/versions.txt $out/versions.txt
  print -l -- ${=envs[$i]} > $out/env.txt
  ( cd $TOP && env ${=envs[$i]} zsh $JUDGE ${boards[$i]} $out > $out/run.out 2>&1 ) &
  local pid=$!
  PIDS[$n]=$pid; T0[$n]=$(date +%s)
  print "  start  $n  ($(date +%H:%M:%S); ${envs[$i]:-no extra env})"
}
reap() {   # prints how many are still running
  local n
  for n in ${(k)PIDS}; do
    if ! kill -0 ${PIDS[$n]} 2>/dev/null; then
      wait ${PIDS[$n]} 2>/dev/null; local rc=$?
      print "  done   $n  $(( $(date +%s) - T0[$n] )) s, exit $rc$([[ -f $BATCH/$n/rules.json ]] || print ', no rules.json')"
      unset "PIDS[$n]"
    fi
  done
}
next=1
while (( next <= ${#names} || ${#PIDS} )); do
  reap
  if (( next <= ${#names} && ${#PIDS} < J )); then
    # Started runs climb to their peak over the first minutes; wait for room before adding one.
    if (( ${#PIDS} == 0 || $(free_mb) > RUN_MB )); then start $next; (( next++ )); sleep 2; continue; fi
  fi
  sleep 5
done

KRT1=$(krt_head)
[[ $KRT1 == $KRT0 ]] || print "  WARNING: ~/Dev/KiCadRoutingTools moved from ${KRT0:0:8} to ${KRT1:0:8} during the batch; runs that started after that used other router code"
print "krt_commit_end\t$KRT1" >> $BATCH/versions.txt

# --- summary ---------------------------------------------------------------------------------
python3 - $BATCH ${names} <<'PY'
import json, os, sys
batch, names = sys.argv[1], sys.argv[2:]
rows = []
for n in names:
    d = os.path.join(batch, n); r = {"name": n, "blocking": None, "open": None, "wall": None, "peak": None}
    try:
        j = json.load(open(os.path.join(d, "rules.json"))); r["blocking"] = j["blocking"]; r["open"] = len(j["open_nets"])
    except (OSError, ValueError, KeyError): pass
    try:
        t = [l.rstrip("\n").split("\t") for l in open(os.path.join(d, "timing.tsv"))][1:]
        r["wall"] = sum(float(x[1]) for x in t if x[0] != "TOTAL" and len(x) > 1 and x[1])
        r["peak"] = max(int(float(x[4])) for x in t if len(x) > 4 and x[4])
    except (OSError, ValueError): pass
    rows.append(r)
rows.sort(key=lambda r: (r["blocking"] is None, r["blocking"] or 0, r["open"] or 0))
f = lambda v: "-" if v is None else (f"{v:.0f}" if isinstance(v, float) else str(v))
with open(os.path.join(batch, "summary.tsv"), "w") as o:
    o.write("name\tblocking\topen_nets\twall_s\tpeak_mb\n")
    for r in rows: o.write("\t".join(f(r[k]) for k in ("name", "blocking", "open", "wall", "peak")) + "\n")
print("\n  %-28s %8s %9s %7s %8s" % ("variant", "blocking", "open nets", "wall s", "peak MB"))
for r in rows: print("  %-28s %8s %9s %7s %8s" % tuple(f(r[k]) for k in ("name", "blocking", "open", "wall", "peak")))
PY
[[ -f $PERF ]] && python3 $PERF $BATCH/${^names} --md $BATCH/perf.md >/dev/null 2>&1 && print "\n  per-step times: $BATCH/perf.md"
print "  summary: $BATCH/summary.tsv; versions: $BATCH/versions.txt"
