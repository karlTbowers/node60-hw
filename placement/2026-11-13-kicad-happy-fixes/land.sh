#!/bin/zsh
# land.sh FINAL.kicad_pcb BASE.kicad_pcb -- put the built board on the repo's node60.kicad_pcb: power_shapes.json
# brought in step (the new GND vias as a group, resized supply vias regrouped), the new supply vias locked,
# zones refilled by kicad-cli, node60.kicad_pro restored (pcbnew's save rewrites it).
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
H=${0:A:h}; ROOT=$(git -C $H rev-parse --show-toplevel); PS=$ROOT/placement/2026-11-02-bars/power/power_shapes.json; T=${1:r}
$KPY $ROOT/placement/2026-11-12-passives/dump_board.py $2 $T.base.dump.json 2>/dev/null | tail -1
$KPY $ROOT/placement/2026-11-12-passives/dump_board.py $1 $T.dump.json 2>/dev/null | tail -1
git -C $ROOT show HEAD:placement/2026-11-02-bars/power/power_shapes.json > $T.ps0.json
python3 $ROOT/placement/2026-11-12-route/land_spec.py $T.base.dump.json $T.dump.json $T.ps0.json $T.ps1.json "kicad-happy fixes (2026-11-13): U501 pad vias, return vias and stitching" GND
python3 $H/sync_spec_sizes.py $T.dump.json $T.ps1.json $PS
cp $1 $ROOT/node60.kicad_pcb
$KPY $ROOT/placement/2026-11-12-passives/lock_supply.py $ROOT/node60.kicad_pcb $PS 2>/dev/null | tail -1
git -C $ROOT checkout node60.kicad_pro
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb drc --refill-zones --save-board --severity-all --schematic-parity --format json -o $H/checks/kicad_drc.json $ROOT/node60.kicad_pcb | tail -3
git -C $ROOT status --short
