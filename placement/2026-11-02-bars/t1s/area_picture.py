#!/usr/bin/env python3
"""Every copper item in a window, F.Cu and B.Cu side by side, T1S nets highlighted (Node60, T1S route).

    $KPY area_picture.py BOARD OUT.png --box X0,Y0,X1,Y1 [--title "..."]
Seen from above on both panels. Grey: other nets' pads; red: T1S_P side nets; blue: T1S_N side nets;
thin dark: other tracks; dots: vias (black other nets, coloured T1S); dashed: rule areas named UNDER_*/TRUNK*.
"""
import argparse
import pcbnew
from PIL import Image, ImageDraw, ImageFont

def font(n):
    for f in ("/System/Library/Fonts/Supplemental/Arial.ttf",):
        try: return ImageFont.truetype(f, n)
        except OSError: pass
    return ImageFont.load_default()

def col(net):
    if net in ("/T1S_P",) or net.endswith(("_P", "P_DROP", "P_END")) and "T1S" in net: return (210, 40, 40)
    if net in ("/T1S_N",) or net.endswith(("_N", "N_DROP", "N_END")) and "T1S" in net: return (30, 80, 210)
    return None

ap = argparse.ArgumentParser(); ap.add_argument("board"); ap.add_argument("out"); ap.add_argument("--box", default="130,38,180,70"); ap.add_argument("--title", default="")
ap.add_argument("--layers", default="F.Cu,B.Cu"); ap.add_argument("--scale", type=float, default=26.0)
a = ap.parse_args()
LAYERS = [(n, {"F.Cu": pcbnew.F_Cu, "In2.Cu": pcbnew.In2_Cu, "B.Cu": pcbnew.B_Cu}[n]) for n in a.layers.split(",")]
X0, Y0, X1, Y1 = (float(v) for v in a.box.split(","))
S = a.scale; PAD = 16; TOP = 50
PW = int((X1 - X0) * S)
W, H = len(LAYERS) * PW + (len(LAYERS) + 1) * PAD, int((Y1 - Y0) * S) + TOP + 20
im = Image.new("RGB", (W, H), (250, 248, 243)); d = ImageDraw.Draw(im)
b = pcbnew.LoadBoard(a.board)
M = pcbnew.ToMM
for k, (name, layer) in enumerate(LAYERS):
    panel = Image.new("RGB", (PW + 1, int((Y1 - Y0) * S) + 1), (250, 248, 243)); d = ImageDraw.Draw(panel)
    ox = PAD + k * (PW + PAD)
    d0 = ImageDraw.Draw(im); d0.text((ox, TOP - 22), name + " (seen from above)", fill=(20, 20, 20), font=font(18))
    P = lambda x, y: ((x - X0) * S, (y - Y0) * S)
    d.rectangle([P(X0, Y0), P(X1, Y1)], outline=(80, 80, 80))
    for gx in range(int(X0), int(X1) + 1, 5):
        d.line([P(gx, Y0), P(gx, Y1)], fill=(232, 228, 220)); d.text(P(gx + 0.1, Y0 + 0.1), str(gx), fill=(160, 160, 160), font=font(11))
    for gy in range(int(Y0), int(Y1) + 1, 5):
        d.line([P(X0, gy), P(X1, gy)], fill=(232, 228, 220)); d.text(P(X0 + 0.1, gy + 0.05), str(gy), fill=(160, 160, 160), font=font(11))
    for f in b.GetFootprints():
        for p in f.Pads():
            if not p.IsOnLayer(layer): continue
            bb = p.GetBoundingBox()
            x0, y0, x1, y1 = (M(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
            if x1 < X0 or x0 > X1 or y1 < Y0 or y0 > Y1: continue
            c = col(p.GetNetname())
            fill = tuple(min(255, v + 120) for v in c) if c else (205, 200, 190)
            if p.GetNetname() == "": fill = (235, 232, 226)
            if p.HasHole(): d.ellipse([P(x0, y0), P(x1, y1)], fill=fill, outline=(120, 120, 120))
            else: d.rectangle([P(x0, y0), P(x1, y1)], fill=fill, outline=(140, 135, 125))
        x, y = M(f.GetPosition().x), M(f.GetPosition().y)
        if X0 <= x <= X1 and Y0 <= y <= Y1 and ((layer == pcbnew.B_Cu) == f.IsFlipped()):
            d.text(P(x, y), f.GetReference(), fill=(0, 0, 0), font=font(12))
    for t in b.GetTracks():
        c = col(t.GetNetname())
        if t.Type() == pcbnew.PCB_VIA_T:
            x, y = M(t.GetPosition().x), M(t.GetPosition().y)
            if X0 <= x <= X1 and Y0 <= y <= Y1:
                q = P(x, y); r = M(t.GetWidth(pcbnew.F_Cu)) / 2 * S
                d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=c or (40, 40, 40))
            continue
        if t.GetLayer() != layer: continue
        w = max(1, int(M(t.GetWidth()) * S))
        d.line([P(M(t.GetStart().x), M(t.GetStart().y)), P(M(t.GetEnd().x), M(t.GetEnd().y))], fill=c or (90, 90, 90), width=w)
    for z in b.Zones():
        if z.GetIsRuleArea() and (z.GetZoneName().startswith(("UNDER_", "TRUNK"))) and z.IsOnLayer(layer):
            bb = z.GetBoundingBox()
            d.rectangle([P(M(bb.GetLeft()), M(bb.GetTop())), P(M(bb.GetRight()), M(bb.GetBottom()))], outline=(120, 120, 120))
    im.paste(panel, (ox, TOP))
d = ImageDraw.Draw(im)
d.text((PAD, 6), a.title, fill=(20, 20, 20), font=font(20))
im.save(a.out); print(a.out)
