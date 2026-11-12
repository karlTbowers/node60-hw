#!/bin/zsh
# land_d32.sh -- D32 "I and H" onto node60.kicad_pcb (user, 2026-11-12), from the repo root, KiCad closed.
# The attempts are applied to a copy of main's board (build.sh), power_shapes.json is brought in step with
# that board (land_spec.py), the study's supply copper is locked and redrawn from the spec (draw_power.py:
# the spec, not the board, is the source), and the board is written back. node60.kicad_pro is not touched.
# The block tables (out_6x, out_34, out_8x, t1s, and the new mcu_pullups and u203_parts) were edited by hand
# from block_poses.py extract; block_poses.py check must report 0 parts off their pose afterwards.
set -e
S=placement/2026-11-12-passives; R=placement/2026-11-02-bars
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
A=$S/attempts
$S/build.sh d32-land $A/01-tmp175-home.json $A/02-east-feed.json $A/03b-i2c-pullups-stair.json $A/04-irq-pullup.json \
   $A/05-ntc-to-mcu.json $A/06-phy-strap.json $A/08-no-3v3-into-cells.json $A/10-tvs-pour.json
mkdir -p $S/land
$KPY $S/dump_board.py node60.kicad_pcb $S/data/main.json 2>/dev/null | tail -1
$KPY $S/dump_board.py $S/boards/d32-land.kicad_pcb $S/data/d32-land.json 2>/dev/null | tail -1
python3 $S/land_spec.py $S/data/main.json $S/data/d32-land.json $R/power/power_shapes.json $S/land/power_shapes.json
python3 ~/Dev/KiCadRoutingTools/py_router/copy_board.py $S/boards/d32-land.kicad_pcb $S/land/t.kicad_pcb >/dev/null
$KPY $S/lock_supply.py $S/land/t.kicad_pcb $S/land/power_shapes.json 2>/dev/null | tail -1
$KPY scripts/draw_power.py $S/land/t.kicad_pcb $S/land/power_shapes.json 2>/dev/null | grep -E "SHORT|NO SITE" || true
kicad-cli pcb drc --refill-zones --save-board -o /dev/null $S/land/t.kicad_pcb >/dev/null 2>&1 || true
cp $S/land/power_shapes.json $R/power/power_shapes.json
cp $S/land/t.kicad_pcb node60.kicad_pcb
echo "node60.kicad_pcb and power_shapes.json written"
