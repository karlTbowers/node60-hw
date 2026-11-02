#!/bin/zsh
# nudge.sh DIR BOARD REF X Y METRIC LIMIT -- try poses round (X,Y) (+-4 mm, 1 mm steps, 4 rotations); keep the first with
# 0 floorplan errors, buildable, and METRIC (a python expression over m(ref,pad)->(x,y), boss(ref)) below LIMIT
D=$1; B=$2; REF=$3; X=$4; Y=$5; METRIC=$6; LIMIT=$7; BASE=${BASE:-$B}
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3   # pcbnew: the metric
KRT=${KRT_PY:?set KRT_PY to a Python with numpy, scipy, shapely}   # KRT tools
cd /Users/karl/Dev/KiCadRoutingTools; T=$D/nudge_$REF.kicad_pcb
for d in 0 1 2 3 4; do for dx in $(seq -$d 1 $d); do for dy in $(seq -$d 1 $d); do
  [ ${dx#-} -ne $d ] && [ ${dy#-} -ne $d ] && continue
  for r in 0 90 180 270; do
    x=$(python3 -c "print($X+$dx)"); y=$(python3 -c "print($Y+$dy)")
    $KRT -X utf8 py_placer/place_pose.py $B $T set $REF --near $x $y --rot $r --snap --radius 1 --intent $D/intent.json >/dev/null 2>&1 || continue
    v=$($KP - $T "$METRIC" 2>/dev/null <<'PY'
import sys,json,math,pcbnew
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM
def m(r,n):
    p=[p for p in b.FindFootprintByReference(r).Pads() if p.GetNumber()==n][0]; return (mm(p.GetPosition().x),mm(p.GetPosition().y))
bs=json.loads(open('/Users/karl/Dev/node60-hw-place/placement/2026-11-02-bars/bosses.json').readline())
def boss(r):
    f=b.FindFootprintByReference(r); c=f.GetCourtyard(f.GetLayer()==pcbnew.F_Cu and pcbnew.F_CrtYd or pcbnew.B_CrtYd).BBox()
    x0,y0,x1,y1=mm(c.GetLeft()),mm(c.GetTop()),mm(c.GetRight()),mm(c.GetBottom())
    return -min(math.hypot(max(x0-bx,0,bx-x1),max(y0-by,0,by-y1))-d/2 for bx,by,d,z,_ in bs)
print(eval(sys.argv[2]))
PY
)
    python3 -c "import sys; sys.exit(0 if float('$v')<$LIMIT else 1)" || continue
    fo=$($KRT -X utf8 py_tools/check_floorplan.py $T --intent $D/intent.json 2>&1)
    echo "$fo" | grep -q -E "cannot parse|Traceback|No module named" && { echo "floorplan check could not run"; exit 2; }
    e=$(echo "$fo" | grep -c "\[ERROR\]"); [ "$e" = 0 ] || continue
    $KRT -X utf8 py_tools/check_assembly.py $T --baseline $BASE 2>&1 | grep -q "VERDICT: buildable" || continue
    cp $T $B; rm -f $D/nudge_$REF.kicad_p*; echo "$REF kept at ~($x,$y) rot $r: metric $v"; exit 0
  done
done; done; done
rm -f $D/nudge_$REF.kicad_p*; echo "$REF: nothing found"
