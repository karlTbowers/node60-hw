#!/bin/zsh
# drc.sh BOARD [OUT.json] -- KiCad DRC with the board's own rules: zones refilled and saved back into BOARD, all
# severities, schematic parity; prints counts and every error. KiCad finds the project by the board's file
# name, so BOARD is judged as node60.kicad_pcb in a folder holding the committed node60.kicad_pro (pcbnew's
# Python save rewrites a .kicad_pro beside a board, so it is taken from git each time; set PRO=file to judge
# with another), node60.kicad_dru, the schematic and the library tables.
KC=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
ROOT=$(git -C ${0:A:h} rev-parse --show-toplevel); O=${2:-${1:r}.drc.json}; J=${1:A:h}/judge.$$
mkdir -p $J && cp $1 $J/node60.kicad_pcb
if [[ -n $PRO ]]; then cp $PRO $J/node60.kicad_pro; else git -C $ROOT show HEAD:node60.kicad_pro > $J/node60.kicad_pro; fi
cp $ROOT/node60.kicad_dru $ROOT/node60.kicad_sch $ROOT/fp-lib-table $ROOT/sym-lib-table $J/; ln -s $ROOT/sheets $J/sheets; ln -s $ROOT/lib $J/lib
$KC pcb drc --refill-zones --save-board --severity-all --schematic-parity --format json -o $O $J/node60.kicad_pcb >/dev/null 2>&1
cp $J/node60.kicad_pcb $1; rm -rf $J
python3 - $O <<'PY'
import json, sys, collections
d = json.load(open(sys.argv[1])); c = collections.Counter((v['severity'], v['type']) for v in d['violations'])
print(sorted(c.items()), "unconnected", len(d['unconnected_items']), "parity", len(d.get('schematic_parity', [])))
for v in d['violations']:
    if v['severity'] == 'error': print(" ", v['type'], v['description'][:60], [(i['description'][:60], i['pos']) for i in v['items']])
for v in d['unconnected_items'][:10]: print("  open", [(i['description'][:60], i['pos']) for i in v['items']])
PY
