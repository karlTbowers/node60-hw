#!/bin/zsh
# measure_paths.sh BOARD -- the supply-path table of REPORT.md for one board (zones filled): copper_r.py at
# 85 C. VBAT_IN J901 to Q202, VBAT_Q2D and VBAT_PROT on all six layers; the outer-layer paths of r_jobs.json
# (J910 to Q201, VBAT_D, OUT1-6) on F.Cu and B.Cu only, as the report's "Before" column was measured.
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
W=${0:A:h}; R=${W:h}/2026-11-02-bars; L=F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu
r() { $KPY $R/power/copper_r.py "$@" --temp 85 2>/dev/null | grep -Eo "[0-9.]+ mohm" | head -1 }
echo "VBAT_IN J901 to Q202 (all layers)\t$(r $1 /VBAT_IN J901:1 Q202:3,4,5,6,7,8 --layers $L)"
echo "VBAT_Q2D R201 to Q203+Q204 (all layers)\t$(r $1 '/Power entry/VBAT_Q2D' R201:4 Q203:9+Q204:9 --layers $L)"
echo "VBAT_D Q201+Q202 to R201 (all layers)\t$(r $1 '/Power entry/VBAT_D' Q201:9+Q202:9 R201:1 --layers $L)"
echo "VBAT_IN J910 to Q201 (all layers)\t$(r $1 /VBAT_IN J910:1 Q201:3,4,5,6,7,8 --layers $L)"
python3 -c "import json,sys;[print('\t'.join(j)) for j in json.load(open(sys.argv[1])) if 'VBAT_PROT' not in j[0] and 'J901' not in j[0] and 'Q2D' not in j[0]]" $W/r_jobs.json | while IFS=$'\t' read name net from to; do
  echo "$name (outer layers)\t$(r $1 "$net" "$from" "$to")"
done
$KPY $R/power/copper_r.py $1 VBAT_PROT Q203:3,4,5,6,7,8+Q204:3,4,5,6,7,8 U601:17@20+U701:17@20+U801:17@20 --temp 85 --layers $L 2>/dev/null | grep -E "drop|loads|loss|W" | grep -v "Debug\|assert" | tail -5
