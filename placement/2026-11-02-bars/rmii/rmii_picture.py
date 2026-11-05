#!/usr/bin/env python3
"""Picture of the RMII link and its clock branches (Node60, D27). KiCad's Python (pcbnew + Pillow).

    $KPY rmii_picture.py BOARD OUT.png --title "..." [--sub "..."] [--box X0,Y0,X1,Y1] [--clock-only]

Seen from above. Pads grey, the RMII data and MDIO lines thin in their colours, the clock thick:
the PHY's branch (Y501 -> R503 -> U501 pin 27) red, the MCU's (Y501 -> R504 -> U401 U6) blue,
the oscillator's output green. Dots are vias; the dashed box is UNDER_Y501.
"""
import argparse

import pcbnew
from PIL import Image, ImageDraw, ImageFont

COL = {"/RMII0_T1S_TXD0": (31, 119, 180), "/RMII0_T1S_TXD1": (255, 127, 14), "/RMII0_T1S_TX_EN": (44, 160, 44),
       "/RMII0_T1S_RXD0": (214, 39, 40), "/RMII0_T1S_RXD1": (148, 103, 189), "/RMII0_T1S_CRS_DV": (140, 86, 75),
       "/RMII0_T1S_RX_ER": (227, 119, 194), "/MDIO0_T1S_MDC": (127, 127, 127), "/MDIO0_T1S_MDIO": (188, 189, 34)}
CLK = {"/T1S/T1S_REFCLK": (200, 30, 30), "/RMII0_T1S_REF_CLK": (20, 80, 200), "/T1S/T1S_OSC_OUT": (20, 150, 60)}


def font(n):
    for f in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf"):
        try:
            return ImageFont.truetype(f, n)
        except OSError:
            pass
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board"); ap.add_argument("out"); ap.add_argument("--title", default=""); ap.add_argument("--sub", default="")
    ap.add_argument("--box", default="145,33,210,60"); ap.add_argument("--clock-only", action="store_true")
    a = ap.parse_args()
    X0, Y0, X1, Y1 = (float(v) for v in a.box.split(","))
    S = 1400 / (X1 - X0)
    PAD, TOP = 20, 70
    W, H = int((X1 - X0) * S) + 2 * PAD, int((Y1 - Y0) * S) + TOP + 60
    im = Image.new("RGB", (W, H), (250, 248, 243)); d = ImageDraw.Draw(im)
    P = lambda x, y: (PAD + (x - X0) * S, TOP + (y - Y0) * S)
    d.rectangle([P(X0, Y0), P(X1, Y1)], outline=(60, 60, 60), width=1)
    b = pcbnew.LoadBoard(a.board)
    for f in b.GetFootprints():
        for p in f.Pads():
            bb = p.GetBoundingBox()
            x0, y0, x1, y1 = (pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
            if x1 < X0 or x0 > X1 or y1 < Y0 or y0 > Y1:
                continue
            c = (205, 200, 190)
            if p.GetNetname() in CLK:
                c = tuple(min(255, v + 90) for v in CLK[p.GetNetname()])
            d.rectangle([P(x0, y0), P(x1, y1)], fill=c, outline=(150, 145, 135))
        r = f.GetReference()
        if r in ("U501", "U401", "Y501", "R503", "R504", "C513", "J903", "Y401"):
            x, y = (pcbnew.ToMM(v) for v in (f.GetPosition().x, f.GetPosition().y))
            if X0 <= x <= X1 and Y0 <= y <= Y1:
                d.text(P(x + 0.6, y - 2.2), r, fill=(20, 20, 20), font=font(18))
    for z in b.Zones():
        if z.GetIsRuleArea() and z.GetZoneName() == "UNDER_Y501":
            bb = z.GetBoundingBox()
            x0, y0, x1, y1 = (pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
            for i in range(0, 40):
                t0, t1 = i / 40, (i + 0.5) / 40
                for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
                    d.line([P(ax + (bx - ax) * t0, ay + (by - ay) * t0), P(ax + (bx - ax) * t1, ay + (by - ay) * t1)], fill=(90, 90, 90), width=1)
    vias = []
    for t in b.GetTracks():
        n = t.GetNetname()
        c = CLK.get(n) or (None if a.clock_only or n not in COL else tuple(int(v * 0.45 + 250 * 0.55) for v in COL[n]))
        if c is None:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            vias.append((pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y), c)); continue
        w = 5 if n in CLK else 2
        d.line([P(pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y)), P(pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y))], fill=c, width=w)
    for x, y, c in vias:
        q = P(x, y); d.ellipse([q[0] - 5, q[1] - 5, q[0] + 5, q[1] + 5], fill=c, outline=(30, 30, 30))
    d.text((PAD, 12), a.title, fill=(20, 20, 20), font=font(24))
    d.text((PAD, 42), a.sub or f"seen from above; every copper layer drawn; dots are vias; x {X0:g}-{X1:g}, y {Y0:g}-{Y1:g} mm", fill=(90, 90, 90), font=font(16))
    x = PAD
    items = [("clock to the PHY (via R503)", CLK["/T1S/T1S_REFCLK"]), ("clock to the MCU (via R504)", CLK["/RMII0_T1S_REF_CLK"]),
             ("oscillator output", CLK["/T1S/T1S_OSC_OUT"])]
    if not a.clock_only:
        items.append(("RMII data and MDIO (pale)", (185, 185, 200)))
    for label, c in items:
        d.rectangle([x, H - 40, x + 22, H - 26], fill=c); d.text((x + 28, H - 43), label, fill=(30, 30, 30), font=font(17)); x += 330
    im.save(a.out)
    print(a.out)


if __name__ == "__main__":
    main()
