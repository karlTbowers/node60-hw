#!/bin/zsh
# measure_r.sh BOARD JOBS.json OUT.tsv -- copper_r.py (85 C) for each supply path of JOBS (name, net, from, to).
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
R=${0:A:h:h}/2026-11-02-bars
: > $3
python3 -c "import json,sys;[print('\t'.join(j)) for j in json.load(open(sys.argv[1]))]" $2 | while IFS=$'\t' read name net from to; do
  v=$($KPY $R/power/copper_r.py $1 "$net" "$from" "$to" --temp 85 2>/dev/null | grep -Eo "[0-9.]+ mohm" | head -1)
  printf "%s\t%s\n" "$name" "$v" >> $3
done
