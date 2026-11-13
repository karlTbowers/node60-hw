#!/bin/zsh
# view.sh BOARD OUT.png X0 Y0 X1 Y1 LAYERS [DPI] -- a picture of a board window (mm, board coordinates) on the given layers.
zmodload zsh/mathfunc; KC=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli; T=$(mktemp -d)
$KC pcb export pdf --mode-single -l "$7" --black-and-white=false -o $T/a.pdf $1 >/dev/null 2>&1 || $KC pcb export pdf -l "$7" -o $T/a.pdf $1 >/dev/null 2>&1
D=${8:-600}; s=$((D/25.4))
pdftoppm -r $D -x $(( int($3*s) )) -y $(( int($4*s) )) -W $(( int(($5-$3)*s) )) -H $(( int(($6-$4)*s) )) -png $T/a.pdf ${2:r} 2>/dev/null
mv ${2:r}-1.png $2 2>/dev/null || mv ${2:r}-*.png $2; rm -rf $T
