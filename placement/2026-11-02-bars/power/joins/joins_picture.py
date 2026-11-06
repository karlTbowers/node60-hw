#!/usr/bin/env python3
"""Pours, pads, tracks, vias and the open connections in a window, one panel per layer (Node60 power joins).

    $KPY joins_picture.py BOARD DRC.json OUT.png --box X0,Y0,X1,Y1 [--layers F.Cu,B.Cu] [--scale 20]
        [--nets 3V3_MAIN,GND,...]

Seen from above. Filled pours are tinted by net, pads grey (the --nets ones coloured), tracks dark, vias
dots, and each unconnected pair from DRC.json (kicad-cli pcb drc --format json) a red line on every
panel, so a join's two ends and what lies between them can be read off one picture.
"""
import argparse
import json
import re

import pcbnew
from PIL import Image, ImageDraw, ImageFont

PAL = [(70, 140, 220), (230, 140, 40), (60, 170, 90), (190, 80, 190), (200, 60, 60), (40, 170, 170),
       (150, 120, 60), (110, 110, 220)]


def font(n):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", n)
    except OSError:
        return ImageFont.load_default()


ap = argparse.ArgumentParser()
ap.add_argument("board"); ap.add_argument("drc"); ap.add_argument("out")
ap.add_argument("--box", required=True); ap.add_argument("--layers", default="F.Cu,B.Cu")
ap.add_argument("--scale", type=float, default=20.0); ap.add_argument("--nets", default="")
ap.add_argument("--opens", default="", help="draw only these nets' open pairs")
a = ap.parse_args()
b = pcbnew.LoadBoard(a.board)
X0, Y0, X1, Y1 = (float(v) for v in a.box.split(","))
S = a.scale; PAD = 14; TOP = 40
layers = [(n, b.GetLayerID(n)) for n in a.layers.split(",")]
PW, PH = int((X1 - X0) * S), int((Y1 - Y0) * S)
img = Image.new("RGB", (len(layers) * (PW + PAD) + PAD, PH + TOP + PAD), (250, 249, 245))
d = ImageDraw.Draw(img, "RGBA")
f, fs = font(14), font(10)
nets = [n for n in a.nets.split(",") if n]
col = {}


def ncol(net):
    for i, n in enumerate(nets):
        if net == n or net.endswith("/" + n):
            return PAL[i % len(PAL)]
    if net not in col:
        col[net] = PAL[(len(col) + len(nets)) % len(PAL)]
    return col[net]


def P(ox, x, y):
    return (ox + (x - X0) * S, TOP + (y - Y0) * S)


opens = []
for v in json.load(open(a.drc)).get("unconnected_items", []):
    it = v["items"]
    if len(it) == 2 and not any("TP" in i["description"] for i in it):
        nn = re.search(r"\[([^\]]+)\]", it[0]["description"]).group(1)
        if a.opens and not any(nn == m or nn.endswith("/" + m) for m in a.opens.split(",")):
            continue
        opens.append(((it[0]["pos"]["x"], it[0]["pos"]["y"]), (it[1]["pos"]["x"], it[1]["pos"]["y"]),
                      re.search(r"\[([^\]]+)\]", it[0]["description"]).group(1)))
for k, (lname, lid) in enumerate(layers):
    ox = PAD + k * (PW + PAD)
    d.text((ox, 8), f"{lname} (seen from above)", fill=(30, 30, 30), font=f)
    d.rectangle([ox, TOP, ox + PW, TOP + PH], outline=(200, 200, 200))
    for z in b.Zones():
        if z.GetIsRuleArea() or not z.IsOnLayer(lid):
            continue
        fp = z.GetFilledPolysList(lid)
        c = ncol(z.GetNetname())
        for i in range(fp.OutlineCount()):
            o = fp.Outline(i)
            pts = [P(ox, o.CPoint(j).x / 1e6, o.CPoint(j).y / 1e6) for j in range(o.PointCount())]
            if len(pts) > 2:
                d.polygon(pts, fill=c + (55,))
            for h in range(fp.HoleCount(i)):
                ho = fp.Hole(i, h)
                hp = [P(ox, ho.CPoint(j).x / 1e6, ho.CPoint(j).y / 1e6) for j in range(ho.PointCount())]
                if len(hp) > 2:
                    d.polygon(hp, fill=(250, 249, 245, 255))
    for fpr in b.GetFootprints():
        for p in fpr.Pads():
            if not p.IsOnLayer(lid):
                continue
            bb = p.GetBoundingBox()
            x0, y0, x1, y1 = bb.GetLeft() / 1e6, bb.GetTop() / 1e6, bb.GetRight() / 1e6, bb.GetBottom() / 1e6
            if x1 < X0 or x0 > X1 or y1 < Y0 or y0 > Y1:
                continue
            n = p.GetNetname()
            c = ncol(n) if any(n == m or n.endswith("/" + m) for m in nets) else (175, 172, 165)
            d.rectangle([P(ox, x0, y0), P(ox, x1, y1)], fill=c + (230,), outline=(90, 90, 90))
        r = fpr.GetPosition()
        if X0 <= r.x / 1e6 <= X1 and Y0 <= r.y / 1e6 <= Y1 and fpr.IsOnLayer(lid) and fpr.GetLayer() == lid:
            d.text(P(ox, r.x / 1e6 + 0.3, r.y / 1e6 + 0.3), fpr.GetReference(), fill=(20, 20, 20), font=fs)
    for t in b.GetTracks():
        n = t.GetNetname()
        hl = any(n == m or n.endswith("/" + m) for m in nets)
        if t.Type() == pcbnew.PCB_VIA_T:
            p = t.GetPosition(); x, y = p.x / 1e6, p.y / 1e6
            if X0 <= x <= X1 and Y0 <= y <= Y1:
                r = t.GetWidth(pcbnew.F_Cu) / 2e6 * S
                c = ncol(n) if hl else (40, 40, 40)
                q = P(ox, x, y); d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=c, outline=(0, 0, 0))
        elif t.GetLayer() == lid:
            w = max(1, int(t.GetWidth() / 1e6 * S))
            c = ncol(n) if hl else (80, 80, 80)
            d.line([P(ox, t.GetStart().x / 1e6, t.GetStart().y / 1e6), P(ox, t.GetEnd().x / 1e6, t.GetEnd().y / 1e6)], fill=c, width=w)
    for (p0, p1, n) in opens:
        if not (X0 <= p0[0] <= X1 and Y0 <= p0[1] <= Y1) and not (X0 <= p1[0] <= X1 and Y0 <= p1[1] <= Y1):
            continue
        d.line([P(ox, *p0), P(ox, *p1)], fill=(220, 20, 20), width=2)
        m = P(ox, (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
        d.text(m, n.split("/")[-1], fill=(200, 0, 0), font=fs)
    for gx in range(int(X0) + 1, int(X1) + 1):
        if gx % 2 == 0:
            d.text(P(ox, gx, Y0), str(gx), fill=(150, 150, 150), font=fs)
    for gy in range(int(Y0) + 1, int(Y1) + 1):
        if gy % 2 == 0:
            d.text(P(ox, X0, gy), str(gy), fill=(150, 150, 150), font=fs)
img.save(a.out)
print(a.out)
