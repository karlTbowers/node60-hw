#!/usr/bin/env python3
"""Labelled pictures for the passive-placement study (2026-11-12). Run with KiCad's Python:

    $KPY study_picture.py BOARD OUT.png --region X0,Y0,X1,Y1 [--layers In3.Cu.PWR,B.Cu] [--scale 14]
         [--title ".."] [--note "..;.."] [--nets N1,N2,..] [--hi R607,C607] [--moves moves.json] [--rats]

Seen from above. Filled copper of --layers tinted by net; pads of --nets coloured, others grey;
bottom-side parts drawn with a solid courtyard, top-side parts dashed; --hi parts ringed in red;
--moves draws an arrow from each moved part's old position (in the JSON) to where it is on BOARD;
--rats joins each --nets net's pads with a thin straight line (minimum spanning tree).
KiCad's Python reads the board (no Pillow there); the drawing runs under the KRT venv (DRAW_PY).
"""
import argparse, json, math, os, subprocess, sys, tempfile

DRAW_PY = os.environ.get("DRAW_PY", os.path.expanduser("~/.cache/dropout/krt-venv/bin/python"))
COL = {"3V3_MAIN": (205, 55, 45), "1V5_CORE": (40, 140, 70), "VBAT_PROT": (40, 110, 190), "VBAT_FILT": (130, 80, 170),
       "VDDAU_AON": (220, 150, 30), "GND": (128, 128, 128), "VBAT_IN": (20, 60, 130), "VBAT_D": (70, 150, 200),
       "VBAT_Q2D": (100, 170, 170)}
PAL = [(255, 127, 14), (44, 160, 44), (148, 103, 189), (140, 86, 75), (227, 119, 194), (23, 190, 207),
       (188, 189, 34), (90, 90, 200), (200, 90, 40), (0, 150, 120), (160, 60, 160), (110, 140, 30)]
BG = (250, 248, 243)


def short(n):
    return n.split("/")[-1]


def args():
    ap = argparse.ArgumentParser()
    ap.add_argument("board"); ap.add_argument("out")
    ap.add_argument("--region", default="40,30,270,140"); ap.add_argument("--layers", default="In3.Cu.PWR")
    ap.add_argument("--scale", type=float, default=14.0); ap.add_argument("--title", default="")
    ap.add_argument("--note", default=""); ap.add_argument("--nets", default="3V3_MAIN,GND")
    ap.add_argument("--hi", default=""); ap.add_argument("--moves", default=""); ap.add_argument("--rats", action="store_true")
    ap.add_argument("--nolabel", action="store_true"); ap.add_argument("--pins", default="")
    ap.add_argument("--scene", default="")
    ap.add_argument("--track-layers", default="", help="draw only tracks on these layers (default: all)")
    ap.add_argument("--allvias", action="store_true", help="draw other nets' vias as grey dots")
    return ap.parse_args()


def scene(a):
    import pcbnew
    M = pcbnew.ToMM
    X0, Y0, X1, Y1 = map(float, a.region.split(","))
    b = pcbnew.LoadBoard(a.board)
    sc = {"zones": [], "bars": [], "tracks": [], "vias": [], "fps": []}
    out = lambda bb: M(bb.GetRight()) < X0 or M(bb.GetLeft()) > X1 or M(bb.GetBottom()) < Y0 or M(bb.GetTop()) > Y1
    box = lambda bb: [M(bb.GetLeft()), M(bb.GetTop()), M(bb.GetRight()), M(bb.GetBottom())]
    for k, L in enumerate(a.layers.split(",")):
        lid = b.GetLayerID(L)
        for z in sorted((z for z in b.Zones() if not z.GetIsRuleArea() and z.IsOnLayer(lid)), key=lambda z: z.GetAssignedPriority()):
            n = short(z.GetNetname())
            if n == "GND" and L.split(".")[0] in ("F", "B"):
                continue                                  # the outer GND pours would tint everything
            ps = z.GetFilledPolysList(lid)
            for i in range(ps.OutlineCount()):
                o = ps.Outline(i)
                if out(o.BBox()) or o.PointCount() < 3:
                    continue
                sc["zones"].append({"k": k, "net": n, "pts": [[M(o.CPoint(j).x), M(o.CPoint(j).y)] for j in range(o.PointCount())]})
    for z in b.Zones():
        if z.GetIsRuleArea() and z.GetZoneName().startswith("BUSBAR"):
            sc["bars"].append({"name": z.GetZoneName(), "box": box(z.GetBoundingBox())})
    for t in b.GetTracks():
        n = short(t.GetNetname())
        if t.Type() == pcbnew.PCB_VIA_T:
            sc["vias"].append([n, M(t.GetPosition().x), M(t.GetPosition().y), M(t.GetWidth(pcbnew.F_Cu))])
        else:
            sc["tracks"].append([n, M(t.GetStart().x), M(t.GetStart().y), M(t.GetEnd().x), M(t.GetEnd().y), M(t.GetWidth()), t.GetLayerName()])
    for fp in b.GetFootprints():
        back = fp.IsFlipped()
        cy = fp.GetCourtyard(pcbnew.B_CrtYd if back else pcbnew.F_CrtYd)
        bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
        sc["fps"].append({"ref": fp.GetReference(), "x": M(fp.GetPosition().x), "y": M(fp.GetPosition().y), "back": back,
                          "box": box(bb), "pads": [[p.GetNumber(), short(p.GetNetname()), box(p.GetBoundingBox()),
                                                    M(p.GetPosition().x), M(p.GetPosition().y), p.GetNetname()] for p in fp.Pads()]})
    return sc


def draw(a, sc):
    from PIL import Image, ImageDraw, ImageFont
    X0, Y0, X1, Y1 = map(float, a.region.split(","))
    S, PAD = a.scale, 20
    notes = [n for n in a.note.split(";") if n]
    HEAD = 50 + 17 * len(notes)
    order = a.nets.split(",")
    def colour(n):
        if n in COL: return COL[n]
        return PAL[order.index(n) % len(PAL)] if n in order else (150, 150, 150)
    nets = set(order)
    W, H = int((X1 - X0) * S) + 2 * PAD, int((Y1 - Y0) * S) + 2 * PAD + HEAD + 44
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im, "RGBA")
    f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 12)
    fs = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 10)
    fb = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 16)
    P = lambda x, y: (PAD + (x - X0) * S, PAD + HEAD + (y - Y0) * S)
    inreg = lambda x, y, m=0: X0 - m <= x <= X1 + m and Y0 - m <= y <= Y1 + m
    outb = lambda bx: bx[2] < X0 or bx[0] > X1 or bx[3] < Y0 or bx[1] > Y1
    for z in sc["zones"]:
        n = z["net"]
        c = colour(n) if (n in nets or n in COL) else (170, 150, 120)
        d.polygon([P(*p) for p in z["pts"]], fill=c + ((95 if z["k"] == 0 else 55),))
    for z in sc["bars"]:
        bx = z["box"]
        d.rectangle([P(bx[0], bx[1]), P(bx[2], bx[3])], outline=(170, 120, 40, 255), width=2)
        if inreg(max(X0, bx[0]) + 1, max(Y0, bx[1]) + 0.3):
            d.text(P(max(X0, bx[0]) + 0.4, max(Y0, bx[1]) + 0.2), z["name"].replace("BUSBAR_", "busbar on top: "), fill=(150, 100, 30), font=fs)
    for n, x1, y1, x2, y2, w, L in sc["tracks"]:
        if not (inreg(x1, y1, 2) or inreg(x2, y2, 2)) or (a.track_layers and L not in a.track_layers.split(",")):
            continue
        c = colour(n) + (255,) if n in nets else (185, 180, 170, 255)
        d.line([P(x1, y1), P(x2, y2)], fill=c, width=max(1, int(w * S)))
    his = set(a.hi.split(",")) if a.hi else set()
    pinrefs = set(a.pins.split(",")) if a.pins else set()
    labels = []
    for fp in sc["fps"]:
        bx = fp["box"]; ref = fp["ref"]; back = fp["back"]
        if outb(bx):
            continue
        for num, n, pb, px, py, full in fp["pads"]:
            c = colour(n) if n in nets else None
            d.rectangle([P(pb[0], pb[1]), P(pb[2], pb[3])], fill=(c + (235,)) if c else (212, 206, 196, 210), outline=(80, 80, 80, 120))
            if ref in pinrefs:
                d.text(P(px - 0.2, py - 0.35), num, fill=(0, 0, 0), font=fs)
        if ref.startswith(("BB", "FID")):
            continue
        (xa, ya), (xb, yb) = P(bx[0], bx[1]), P(bx[2], bx[3])
        oc = (200, 20, 20, 255) if ref in his else ((70, 70, 70, 200) if back else (40, 90, 160, 220))
        if back or ref in his:
            d.rectangle([(xa, ya), (xb, yb)], outline=oc, width=3 if ref in his else 1)
        else:
            for q in range(int(xa), int(xb), 8):
                d.line([(q, ya), (min(q + 4, xb), ya)], fill=oc); d.line([(q, yb), (min(q + 4, xb), yb)], fill=oc)
            for q in range(int(ya), int(yb), 8):
                d.line([(xa, q), (xa, min(q + 4, yb))], fill=oc); d.line([(xb, q), (xb, min(q + 4, yb))], fill=oc)
        if not a.nolabel or ref in his:
            big = (bx[2] - bx[0]) > 4
            labels.append((ref, P(bx[0] + (0.3 if big else 0), bx[1] - (0 if big else 0.95)), ref in his))
    for n, x, y, w in sc["vias"]:
        if not inreg(x, y):
            continue
        if n not in nets or n == "GND":
            if a.allvias:
                d.ellipse([P(x - w / 2, y - w / 2), P(x + w / 2, y + w / 2)], outline=(120, 110, 100, 255), fill=(225, 220, 210, 255))
            continue
        r = max(w / 2, 3.0 / S)
        d.ellipse([P(x - r, y - r), P(x + r, y + r)], fill=colour(n) + (255,), outline=(255, 255, 255))
    if a.rats:
        for n in order:
            if n in COL:                                  # supply nets: their planes join them, a ratsnest would only clutter
                continue
            groups = {}                                   # one tree per full net name: SW_VDD is three nets, one a sheet
            for fp in sc["fps"]:
                if fp["y"] < 141:
                    for num, pn, pb, px, py, full in fp["pads"]:
                        if pn == n: groups.setdefault(full, []).append((px, py))
            for pts in groups.values():
                done, todo = [0], list(range(1, len(pts)))
                while todo:
                    dd, i, j = min((math.dist(pts[i], pts[j]), i, j) for i in done for j in todo)
                    d.line([P(*pts[i]), P(*pts[j])], fill=colour(n) + (170,), width=2)
                    done.append(j); todo.remove(j)
    if a.moves:
        mv = json.load(open(a.moves)); pos = {fp["ref"]: (fp["x"], fp["y"]) for fp in sc["fps"]}
        for ref, m in mv.items():
            if ref not in pos or "from" not in m:
                continue
            (x, y), (ox, oy) = pos[ref], m["from"][:2]
            if math.dist((x, y), (ox, oy)) < 0.3 or not (inreg(x, y) or inreg(ox, oy)):
                continue
            d.ellipse([P(ox - 0.5, oy - 0.5), P(ox + 0.5, oy + 0.5)], outline=(200, 20, 20, 255), width=2)
            d.line([P(ox, oy), P(x, y)], fill=(200, 20, 20, 150), width=2)
            if inreg(ox, oy): d.text(P(ox + 0.6, oy - 0.4), f"was {ref}", fill=(200, 20, 20), font=fs)
    for ref, (lx, ly), hi in labels:
        d.text((lx, ly), ref, fill=(200, 20, 20) if hi else (25, 25, 25), font=f if hi else fs)
    (rx0, ry0), (rx1, ry1) = P(X0, Y0), P(X1, Y1)
    for r in ([0, 0, W, ry0], [0, ry1, W, H], [0, 0, rx0, H], [rx1, 0, W, H]):   # mask what spills past the region
        d.rectangle(r, fill=BG + (255,))
    for ref, (lx, ly), hi in labels:
        if hi and ly < ry0: d.text((lx, ry0 + 2), ref, fill=(200, 20, 20), font=f)
    d.text((PAD, 8), a.title, fill=(30, 30, 30), font=fb)
    d.text((PAD, 30), f"seen from above; tinted copper: {a.layers.replace(',', ' + ')}; x {X0:g}-{X1:g}, y {Y0:g}-{Y1:g} mm; "
           "solid outline = bottom-side part, dashed = top-side", fill=(90, 90, 90), font=f)
    for i, n in enumerate(notes):
        d.text((PAD, 48 + 17 * i), n.strip(), fill=(60, 40, 20), font=f)
    d.rectangle([P(X0, Y0), P(X1, Y1)], outline=(60, 60, 60))
    x, yl = PAD, H - 40
    for n in order:
        c = colour(n); wdt = 30 + int(d.textlength(n, font=f))
        if x + wdt > W - PAD: x, yl = PAD, yl + 18
        d.rectangle([x, yl, x + 12, yl + 12], fill=c); d.text((x + 16, yl - 1), n, fill=(40, 40, 40), font=f)
        x += wdt
    im.save(a.out)
    print("written", a.out)


if __name__ == "__main__":
    a = args()
    if a.scene:
        draw(a, json.load(open(a.scene)))
    else:
        sc = scene(a)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as t:
            json.dump(sc, t)
        try:
            subprocess.run([DRAW_PY, os.path.abspath(__file__)] + sys.argv[1:] + ["--scene", t.name], check=True)
        finally:
            os.unlink(t.name)
