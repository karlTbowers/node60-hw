#!/bin/zsh
# build.sh IN.kicad_pcb OUT.kicad_pcb -- the whole run on a copy of main's board (264352a), each step judged by
# KiCad's DRC: N1/N3 (U501's pad vias, the re-laid RMII tracks, stubs), exact duplicates, N2 (via sizes), N6
# (return vias and stitching), N4 (reference text). The specs are the record: stitch.py and silk_place.py
# proposed n6_stitch.json and silk_place.json from the board as it stood after the steps before them.
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
H=${0:A:h}; T=${2:r}
$KPY $H/apply_fix.py $1 $H/specs/n1_u501.json $T.1.kicad_pcb 2>/dev/null
$KPY $H/dedupe_tracks.py $T.1.kicad_pcb $T.2.kicad_pcb 2>/dev/null | tail -1
$KPY $H/apply_fix.py $T.2.kicad_pcb $H/specs/n2_resize.json $H/specs/n6_stitch.json $T.3.kicad_pcb 2>/dev/null
$KPY $H/silk_apply.py $T.3.kicad_pcb $H/specs/silk_place.json $2 2>/dev/null
rm -f $T.[123].kicad_pcb
$H/drc.sh $2
