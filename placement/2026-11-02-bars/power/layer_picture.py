#!/usr/bin/env python3
"""Draw a plane layer's signal policy on the board (D17 decision page pictures). Pillow only.

    python3 layer_picture.py GEO.json OUT.png --title "..." [--window X0,Y0,X1,Y1 ...] [--usage]
                             [--whole] [--one-plane]

GEO.json: {"parts": {ref: [x0, y0, x1, y1]}, "in2": [[i, j, count], ...]} (2.5 mm cells from the
board's west and north edges), exported from the board with pcbnew. The picture shows the outline
seen from above, the key parts, the VBAT_PROT current path (from Q203/Q204 to the three output
switches), the signal windows (cyan) and, with --usage, where a fast route put In2 tracks (red).
"""
import argparse
import json

from PIL import Image, ImageDraw, ImageFont

X0, Y0, X1, Y1 = 39.95, 29.95, 270.05, 140.05
S = 5.0                                   # pixels per mm
PAD = 40


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("geo"); ap.add_argument("out"); ap.add_argument("--title", default="")
    ap.add_argument("--window", action="append", default=[])
    ap.add_argument("--usage", action="store_true")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    g = json.load(open(a.geo))
    W, H = int((X1 - X0) * S) + 2 * PAD, int((Y1 - Y0) * S) + 2 * PAD + 110
    im = Image.new("RGB", (W, H), (250, 248, 243)); d = ImageDraw.Draw(im, "RGBA")
    try:
        f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 15)
        fb = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 18)
    except OSError:
        f = fb = ImageFont.load_default()
    P = lambda x, y: (PAD + (x - X0) * S, PAD + 100 + (y - Y0) * S)
    d.text((PAD, 8), a.title, fill=(30, 30, 30), font=fb)
    # the plane: solid VBAT_PROT copper tint, then windows cut out of it
    d.rectangle([P(X0, Y0), P(X1, Y1)], fill=(232, 214, 190), outline=(60, 60, 60), width=2)
    for w in a.window:
        x0, y0, x1, y1 = map(float, w.split(","))
        d.rectangle([P(x0, y0), P(x1, y1)], fill=(150, 215, 225, 200), outline=(20, 120, 140), width=2)
    if a.usage:
        for i, j, c in g["in2"]:
            x, y = X0 + i * 2.5, Y0 + j * 2.5
            al = min(220, 60 + c * 6)
            d.rectangle([P(x, y), P(x + 2.5, y + 2.5)], fill=(200, 30, 30, al))
    # current path: source (Q203/Q204 drains) to each switch's VBB
    q = g["parts"]["Q203"]; src = ((q[0] + q[2]) / 2, (q[1] + g["parts"]["Q204"][3]) / 2)
    for r in ("U601", "U701", "U801"):
        u = g["parts"][r]; dst = ((u[0] + u[2]) / 2, (u[1] + u[3]) / 2)
        d.line([P(*src), P(src[0], 104), P(dst[0], 104), P(*dst)], fill=(190, 90, 20, 230), width=7)
    for r, bb in g["parts"].items():
        col = (40, 40, 40) if r[0] in "UQRK" else (90, 90, 90)
        d.rectangle([P(bb[0], bb[1]), P(bb[2], bb[3])], outline=col, width=2)
        if r in ("U401", "U501", "U601", "U701", "U801", "Q203", "R201", "J910", "J901", "J911", "J902", "J903", "J912", "K501"):
            d.text((P(bb[0], bb[1])[0] + 3, P(bb[0], bb[1])[1] + 2), r, fill=col, font=f)
    # legend
    ly = H - 24
    for i, (c, t) in enumerate((((232, 214, 190), "VBAT_PROT plane copper"), ((150, 215, 225), "signal window (no pour)"),
                                ((190, 90, 20), "main VBAT_PROT current path"), ((200, 30, 30), "variant e's In2 tracks"))):
        if t.startswith("variant") and not a.usage:
            continue
        x = PAD + i * 260
        d.rectangle([x, ly, x + 18, ly + 14], fill=c); d.text((x + 24, ly - 1), t, fill=(40, 40, 40), font=f)
    if a.note:
        d.text((PAD + 4, PAD + 104), a.note, fill=(40, 40, 40), font=f)
    im.save(a.out)


if __name__ == "__main__":
    main()
