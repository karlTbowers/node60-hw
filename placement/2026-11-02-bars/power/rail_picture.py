#!/usr/bin/env python3
"""Pictures of the small rails' copper (D22, 2026-11-04): one region of the board seen from above,
pads coloured by net, and the filled copper of chosen layers tinted by net. Run with KiCad's Python:

    $KPY rail_picture.py BOARD OUT.png --region X0,Y0,X1,Y1 --layers In3.Cu[,B.Cu] [--scale 8]
                         [--title "..."] [--nets 3V3_MAIN,1V5_CORE,...]

Zones are drawn from their filled polygons (fill the board first); vias of the coloured nets are
dots, their stub tracks lines. Parts outside --nets are grey outlines.
"""
import argparse

import pcbnew
from PIL import Image, ImageDraw, ImageFont

M = pcbnew.ToMM
COL = {"3V3_MAIN": (200, 60, 50), "1V5_CORE": (40, 140, 70), "VBAT_PROT": (40, 110, 190), "VBAT_FILT": (130, 80, 170),
       "VDDAU_AON": (220, 150, 30), "GND": (120, 120, 120), "1V1_MCU_V11": (20, 160, 160),
       "3V3_MAIN_SW": (230, 60, 200), "1V5_CORE_SW": (230, 60, 200), "3V3_MAIN_REG": (240, 140, 120),
       "1V5_CORE_REG": (120, 200, 120), "3V3_MAIN_VCC": (250, 200, 60), "1V5_CORE_FB": (60, 60, 220), "INH": (180, 180, 60),
       "1V5_EN": (180, 180, 60)}


def short(n):
    return n.split("/")[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board"); ap.add_argument("out")
    ap.add_argument("--region", required=True); ap.add_argument("--layers", default="In3.Cu")
    ap.add_argument("--scale", type=float, default=8.0); ap.add_argument("--title", default="")
    ap.add_argument("--nets", default=",".join(COL))
    ap.add_argument("--labels", default="", help="refs to label")
    ap.add_argument("--pins", default="", help="refs whose pad numbers to print")
    ap.add_argument("--only-vias-in", default="", help="X0,Y0,X1,Y1: draw only the vias outside this rectangle (an edge ring)")
    a = ap.parse_args()
    X0, Y0, X1, Y1 = map(float, a.region.split(","))
    S, PAD, HEAD = a.scale, 20, 46
    nets = set(a.nets.split(","))
    b = pcbnew.LoadBoard(a.board)
    W, H = int((X1 - X0) * S) + 2 * PAD, int((Y1 - Y0) * S) + 2 * PAD + HEAD + 26
    im = Image.new("RGB", (W, H), (250, 248, 243)); d = ImageDraw.Draw(im, "RGBA")
    try:
        f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 12)
        fb = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 15)
    except OSError:
        f = fb = ImageFont.load_default()
    P = lambda x, y: (PAD + (x - X0) * S, PAD + HEAD + (y - Y0) * S)
    d.text((PAD, 8), a.title, fill=(30, 30, 30), font=fb)
    d.text((PAD, 28), f"seen from above; copper on {a.layers.replace(',', ' + ')}; x {X0:g}-{X1:g}, y {Y0:g}-{Y1:g} mm",
           fill=(90, 90, 90), font=f)
    d.rectangle([P(X0, Y0), P(X1, Y1)], outline=(60, 60, 60))
    for k, L in enumerate(a.layers.split(",")):
        lid = b.GetLayerID(L)
        alpha = 110 if k == 0 else 70
        for z in b.Zones():
            if z.GetIsRuleArea() or not z.IsOnLayer(lid) or short(z.GetNetname()) not in nets:
                continue
            c = COL.get(short(z.GetNetname()), (150, 150, 150))
            ps = z.GetFilledPolysList(lid)
            for i in range(ps.OutlineCount()):
                o = ps.Outline(i)
                pts = [P(M(o.CPoint(j).x), M(o.CPoint(j).y)) for j in range(o.PointCount())]
                if len(pts) > 2:
                    d.polygon(pts, fill=c + (alpha,))
                for h in range(ps.HoleCount(i)):
                    hh = ps.Hole(i, h)
                    hp = [P(M(hh.CPoint(j).x), M(hh.CPoint(j).y)) for j in range(hh.PointCount())]
                    if len(hp) > 2:
                        d.polygon(hp, fill=(250, 248, 243, 255))
    for fp in b.GetFootprints():
        bb = fp.GetBoundingBox(False)
        if M(bb.GetRight()) < X0 or M(bb.GetLeft()) > X1 or M(bb.GetBottom()) < Y0 or M(bb.GetTop()) > Y1:
            continue
        for p in fp.Pads():
            pb = p.GetBoundingBox()
            n = short(p.GetNetname())
            c = COL.get(n) if n in nets else None
            d.rectangle([P(M(pb.GetLeft()), M(pb.GetTop())), P(M(pb.GetRight()), M(pb.GetBottom()))],
                        fill=(c + (230,)) if c else (210, 205, 195, 200), outline=(80, 80, 80, 120))
        if fp.GetReference() in a.labels.split(","):
            x, y = M(fp.GetPosition().x), M(fp.GetPosition().y)
            d.text(P(x + 0.6, y - 1.6), fp.GetReference(), fill=(20, 20, 20), font=f)
        if a.pins and fp.GetReference() in a.pins.split(","):
            for p in fp.Pads():
                q = p.GetPosition()
                d.text(P(M(q.x) - 0.15, M(q.y) - 0.2), p.GetNumber(), fill=(0, 0, 0), font=f)
    for t in b.GetTracks():
        n = short(t.GetNetname())
        if n not in nets:
            continue
        c = COL.get(n, (150, 150, 150))
        if t.Type() == pcbnew.PCB_VIA_T:
            x, y, r = M(t.GetPosition().x), M(t.GetPosition().y), M(t.GetWidth()) / 2
            if a.only_vias_in:
                q0, q1, q2, q3 = map(float, a.only_vias_in.split(","))
                if q0 < x < q2 and q1 < y < q3:
                    continue
            if X0 <= x <= X1 and Y0 <= y <= Y1:
                rr = max(r, 3.5 / S)                         # at least a few pixels across at small scales
                d.ellipse([P(x - rr, y - rr), P(x + rr, y + rr)], fill=c + (255,), outline=(255, 255, 255))
        else:
            d.line([P(M(t.GetStart().x), M(t.GetStart().y)), P(M(t.GetEnd().x), M(t.GetEnd().y))], fill=c + (255,),
                   width=max(1, int(M(t.GetWidth()) * S)))
    x = PAD
    for n, c in COL.items():
        if n in nets:
            d.rectangle([x, H - 20, x + 12, H - 8], fill=c); d.text((x + 16, H - 21), n, fill=(40, 40, 40), font=f)
            x += 30 + int(d.textlength(n, font=f))
    im.save(a.out)
    print("written", a.out)


if __name__ == "__main__":
    main()
