#!/usr/bin/env python3
"""D20 pictures: the power entry between the two battery bosses, today and mirrored about x 155.
Run with KiCad's Python from the repo root (needs Pillow, which KiCad's Python has):

    $KPY placement/2026-11-02-bars/power/d20_picture.py OUTDIR

Moves the power parts on an in-memory copy of the board (nothing is saved), reads their pads and
bodies back, and draws the region between the bosses seen from above, pads coloured by net.
"""
import sys

import pcbnew
from PIL import Image, ImageDraw, ImageFont

M = pcbnew.ToMM
X0, Y0, X1, Y1 = 86.0, 54.0, 224.0, 116.0
S = 7.0
PAD, HEAD = 24, 70
NET_COL = {"VBAT_IN": (214, 120, 40), "VBAT_IN_DOWNSTREAM": (120, 120, 120), "VBAT_D": (196, 60, 60), "VBAT_Q2D": (140, 70, 160),
           "VBAT_PROT": (40, 120, 190)}
POWER = ("Q201", "Q202", "Q203", "Q204", "R201")
CONTEXT = ("U201", "U202", "K501", "U701", "C707", "R707", "RT701", "D201", "J910", "J901")

# option A: mirror about x 155 (centre of J910 at 102 and J901 at 208)
MIRROR = {"Q201": (127.0, 93.0, 0), "Q202": (183.0, 93.0, 180),
          "Q203": (141.0, 80.0, 0), "Q204": (169.0, 80.0, 180),
          "R201": (155.0, 86.5, None),               # rotated so F1 (VBAT_D) is south
          "U201": (155.0, 75.0, 0), "U202": (155.0, 96.5, -90)}


def place(b, poses):
    for ref, (x, y, rot) in poses.items():
        fp = b.FindFootprintByReference(ref)
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        if rot is not None:
            fp.SetOrientationDegrees(rot)
    r = b.FindFootprintByReference("R201")
    if "R201" in poses:
        for rot in (90, -90):
            r.SetOrientationDegrees(rot)
            f1 = next(p for p in r.Pads() if p.GetNetname().endswith("VBAT_D"))
            if M(f1.GetPosition().y) > M(r.GetPosition().y):
                break


def draw(b, out, title, note, extra=None, renamed=False):
    W, H = int((X1 - X0) * S) + 2 * PAD, int((Y1 - Y0) * S) + 2 * PAD + HEAD
    im = Image.new("RGB", (W, H), (250, 248, 243)); d = ImageDraw.Draw(im, "RGBA")
    try:
        f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 14)
        fb = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 17)
    except OSError:
        f = fb = ImageFont.load_default()
    P = lambda x, y: (PAD + (x - X0) * S, PAD + HEAD + (y - Y0) * S)
    d.text((PAD, 8), title, fill=(30, 30, 30), font=fb)
    d.text((PAD, 32), note, fill=(80, 80, 80), font=f)
    # busbars (on top, drawn as outlines) and the centre line
    for ref in ("BB901", "BB902"):
        bb = b.FindFootprintByReference(ref).GetBoundingBox(False)
        d.rectangle([P(M(bb.GetLeft()), M(bb.GetTop())), P(M(bb.GetRight()), M(bb.GetBottom()))],
                    fill=(200, 140, 60, 28) if ref == "BB901" else (90, 90, 90, 22),
                    outline=(150, 100, 40) if ref == "BB901" else (110, 110, 110), width=2)
    d.text(P(112, 107.2), "BB901 battery busbar (on top, on the spigots)", fill=(130, 85, 30), font=f)
    d.text(P(88, 57.5), "BB902 return busbar", fill=(100, 100, 100), font=f)
    for y in range(int(Y0), int(Y1), 3):
        d.line([P(155, y), P(155, y + 1.5)], fill=(60, 60, 60, 140), width=1)
    d.text(P(155.6, Y0 + 0.3), "x 155", fill=(60, 60, 60), font=f)
    if extra:
        extra(d, P, f)
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        if ref not in POWER + CONTEXT:
            continue
        bb = fp.GetBoundingBox(False)
        box = [P(M(bb.GetLeft()), M(bb.GetTop())), P(M(bb.GetRight()), M(bb.GetBottom()))]
        power = ref in POWER
        d.rectangle(box, fill=(255, 255, 255, 120) if power else (210, 210, 210, 90),
                    outline=(40, 40, 40) if power else (130, 130, 130), width=2 if power else 1)
        for p in fp.Pads():
            n = p.GetNetname().split("/")[-1]
            if renamed and n == "VBAT_IN_DOWNSTREAM":
                n = "VBAT_IN"
            if n in NET_COL and (power or ref in ("J910", "J901")):
                pb = p.GetBoundingBox()
                d.rectangle([P(M(pb.GetLeft()), M(pb.GetTop())), P(M(pb.GetRight()), M(pb.GetBottom()))],
                            fill=NET_COL[n] + (210,))
        cx, cy = M(fp.GetPosition().x), M(fp.GetPosition().y)
        lab = ref if ref not in ("C707", "R707", "RT701", "U701") else ""
        if lab:
            side = ref in ("U201", "U202", "K501")
            at = (P(M(bb.GetRight()), 0)[0] + 4, P(0, cy)[1] - 8) if side else (P(cx, cy)[0] - 16, P(0, M(bb.GetTop()))[1] - 17)
            d.text(at, lab,
                   fill=(20, 20, 20) if power else (90, 90, 90), font=fb if power else f)
    # legend
    lx = PAD
    for n, c in NET_COL.items():
        if renamed and n == "VBAT_IN_DOWNSTREAM":
            continue
        d.rectangle([lx, 52, lx + 14, 64], fill=c); d.text((lx + 19, 50), n, fill=(40, 40, 40), font=f)
        lx += 130 if n != "VBAT_IN_DOWNSTREAM" else 200
    im.save(out)


def main():
    out = sys.argv[1]
    b = pcbnew.LoadBoard("node60.kicad_pcb")
    draw(b, f"{out}/d20_now.png", "Today: the entry chain at J910's end",
         "VBAT_IN reaches the ideal-diode FETs from J910 only; J901 has no board copper (its current crosses the bar).")
    place(b, MIRROR)

    def arrows(d, P, f):
        for (xa, xb) in ((109, 121), (201, 189)):
            d.line([P(xa, 99.6), P(xb, 95)], fill=(214, 120, 40, 200), width=5)
    draw(b, f"{out}/d20_mirror.png", "Option A: mirrored about x 155",
         "Q201 fed from J910, Q202 from J901; both drain into R201 on the centre line; Q203/Q204 split VBAT_PROT west and east.",
         arrows, renamed=True)


if __name__ == "__main__":
    main()
