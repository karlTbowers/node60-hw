#!/usr/bin/env python3
"""Prove each D12 routing rule in node60.kicad_dru fires (ee-layout-rules: never trust a rule
that hasn't been seen to fire), and that its scope stops where it should.

Run with KiCad's Python from the repo root:

    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \\
        placement/2026-11-02-bars/rules/prove_rules.py [node60.kicad_pcb]

Each case copies the project (board, .kicad_pro, .kicad_dru, schematic not needed) to a scratch
folder, adds one deliberate item with pcbnew, runs `kicad-cli pcb drc` at every severity and
looks for the rule's name in a violation within 3 mm of the planted item. A "fires" case passes
when it is there; a "quiet" case (the control) passes when it isn't. Zone connection is not a DRC
check: that case fills a test pour and looks at the copper just off the pad's corner (solid
fills it, a thermal relief leaves the gap). Exit 0 when every case passes.
"""
import concurrent.futures as cf
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pcbnew

FM, TM = pcbnew.FromMM, pcbnew.ToMM
ROOT = os.getcwd()
BOARD = sys.argv[1] if len(sys.argv) > 1 else "node60.kicad_pcb"
KICAD_CLI = shutil.which("kicad-cli") or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"


def track(b, net, layer, x0, y0, x1, y1, w):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(FM(x0), FM(y0)))
    t.SetEnd(pcbnew.VECTOR2I(FM(x1), FM(y1)))
    t.SetWidth(FM(w))
    t.SetLayer(b.GetLayerID(layer))
    t.SetNet(b.FindNet(net))
    b.Add(t)


def via(b, net, x, y):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(FM(x), FM(y)))
    v.SetWidth(FM(0.45))
    v.SetDrill(FM(0.25))
    v.SetNet(b.FindNet(net))
    v.SetIsFree(True)          # else KiCad gives a via standing in a pour the pour's net on save
    b.Add(v)


def text(b, layer, x, y, h, stroke=0.12):
    t = pcbnew.PCB_TEXT(b)
    t.SetText("RULE TEST")
    t.SetLayer(b.GetLayerID(layer))
    t.SetPosition(pcbnew.VECTOR2I(FM(x), FM(y)))
    t.SetTextSize(pcbnew.VECTOR2I(FM(h), FM(h)))
    t.SetTextThickness(FM(stroke))
    b.Add(t)


def area(b, name, layer, x0, y0, x1, y1):
    """a rule area of the given name: the rules that name it (intersectsArea) see it like the board's own"""
    z = pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetZoneName(name)
    ls = pcbnew.LSET(); ls.AddLayer(b.GetLayerID(layer)); z.SetLayerSet(ls)
    for allow in (z.SetDoNotAllowTracks, z.SetDoNotAllowVias, z.SetDoNotAllowPads, z.SetDoNotAllowZoneFills, z.SetDoNotAllowFootprints):
        allow(False)
    o = z.Outline(); o.RemoveAllContours(); o.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        o.Append(FM(x), FM(y))
    b.Add(z)


def pour(b, net, layer, x0, y0, x1, y1):
    """a small copper pour of a net (unfilled: the disallow rule looks at the zone itself)"""
    z = pcbnew.ZONE(b); z.SetLayer(b.GetLayerID(layer)); z.SetNet(b.FindNet(net)); z.SetAssignedPriority(100)
    o = z.Outline(); o.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        o.Append(FM(x), FM(y))
    b.Add(z)


def clear(b, *nets):
    """the board's routed copper of these nets off the case's copy (since D28 the T1S line is routed)"""
    for t in list(b.GetTracks()):
        if t.GetNetname() in nets:
            b.Delete(t)


PHY = ("/T1S/T1S_PHY_P", "/T1S/T1S_PHY_N")
CMC = ("/T1S/T1S_CMC_P", "/T1S/T1S_CMC_N")


def cmc_pair(b, detour=0.0):
    """C511/C512 pad 1 to FL501's CMC pins (found by net: since D31 P is pin 3) on B.Cu, P with an optional
    sideways detour (skew), outward from the pair"""
    clear(b, *CMC)
    fl = next(f for f in b.GetFootprints() if f.GetReference() == "FL501")
    by_net = {p.GetNetname(): p.GetNumber() for p in fl.Pads()}
    (ax, ay), (bx, by) = [(TM(p.GetPosition().x), TM(p.GetPosition().y)) for p in (pad_of(b, "C511", "1"), pad_of(b, "FL501", by_net[CMC[0]]))]
    (cx, cy), (dx, dy) = [(TM(p.GetPosition().x), TM(p.GetPosition().y)) for p in (pad_of(b, "C512", "1"), pad_of(b, "FL501", by_net[CMC[1]]))]
    my = (ay + by) / 2
    out = detour if ax > cx else -detour
    track(b, CMC[0], "B.Cu", ax, ay, ax + out, my, 0.165); track(b, CMC[0], "B.Cu", ax + out, my, bx, by, 0.165)
    track(b, CMC[1], "B.Cu", cx, cy, dx, dy, 0.165)


def pad_of(b, ref, num):
    for fp in b.GetFootprints():
        if fp.GetReference() == ref:
            return next(p for p in fp.Pads() if p.GetNumber() == num)


def centre(b, ref):
    fp = next(f for f in b.GetFootprints() if f.GetReference() == ref)
    return TM(fp.GetPosition().x), TM(fp.GetPosition().y)


def phy_pair(b, detour=0.0, split=0.0):
    """FL501's PHY pins (P, N: found by net, since D31 P is pin 2) to U501 pins 30/31 on B.Cu: a straight
    pair, P with an optional sideways detour (skew), or the two lines run apart (uncoupled)"""
    clear(b, *PHY)
    fl = next(f for f in b.GetFootprints() if f.GetReference() == "FL501")
    by_net = {p.GetNetname(): p.GetNumber() for p in fl.Pads()}
    p1, p2 = pad_of(b, "FL501", by_net[PHY[0]]), pad_of(b, "FL501", by_net[PHY[1]])
    u30, u31 = pad_of(b, "U501", "30"), pad_of(b, "U501", "31")
    P = lambda p: (TM(p.GetPosition().x), TM(p.GetPosition().y))
    (ax, ay), (bx, by), (cx, cy), (dx, dy) = P(p1), P(p2), P(u30), P(u31)
    if detour:
        my = (ay + cy) / 2
        track(b, "/T1S/T1S_PHY_P", "B.Cu", ax, ay, ax - detour, my, 0.165)
        track(b, "/T1S/T1S_PHY_P", "B.Cu", ax - detour, my, cx, cy, 0.165)
    else:
        track(b, "/T1S/T1S_PHY_P", "B.Cu", ax, ay, ax - split, ay - 1.2, 0.165)
        track(b, "/T1S/T1S_PHY_P", "B.Cu", ax - split, ay - 1.2, cx, cy, 0.165)
    track(b, "/T1S/T1S_PHY_N", "B.Cu", bx, by, bx + split, by - 1.2, 0.165)
    track(b, "/T1S/T1S_PHY_N", "B.Cu", bx + split, by - 1.2, dx, dy, 0.165)


SDA = "/I2C0_TELEMETRY_SDA"
SCL = "/I2C0_TELEMETRY_SCL"
FREE = (95.0, 36.0)        # checked free of parts on B.Cu and In2/In3 (see the "free spot" case)


def free_strip(b, layer, x0, y0, x1, y1, length=6.5, margin=0.6):
    """the west end (x, y) of a horizontal strip of the given length inside the box with no track, via or pad of
    that layer within the margin: on a routed board the planted items need copper-free ground, since KiCad
    reports one violation per track and a short would hide the rule under test"""
    lid = b.GetLayerID(layer); boxes = []
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() == lid:
            bb = t.GetBoundingBox(); boxes.append((TM(bb.GetLeft()), TM(bb.GetTop()), TM(bb.GetRight()), TM(bb.GetBottom())))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.IsOnLayer(lid):
                bb = p.GetBoundingBox(); boxes.append((TM(bb.GetLeft()), TM(bb.GetTop()), TM(bb.GetRight()), TM(bb.GetBottom())))
    y = y0 + margin
    while y <= y1 - margin:
        x = x0 + margin
        while x + length <= x1 - margin:
            hit = [q for q in boxes if q[0] < x + length + margin and q[2] > x - margin and q[1] < y + margin and q[3] > y - margin]
            if not hit: return (round(x, 2), round(y, 2))
            x = max(q[2] for q in hit) + margin + 0.01
        y += 0.25
    raise SystemExit(f"no free strip on {layer} in {x0},{y0},{x1},{y1}")


_B0 = pcbnew.LoadBoard(os.path.join(ROOT, BOARD))
BAR_GND = free_strip(_B0, "F.Cu", 68.0, 61.6, 242.0, 79.6)        # F.Cu under the GND busbar (y 61.1-80.1)
BAR_VIN = free_strip(_B0, "F.Cu", 93.5, 91.0, 216.5, 108.5)       # F.Cu under the VBAT_IN busbar (y 90.1-109.1); B.Cu there for the control
BAR_VIN_B = free_strip(_B0, "B.Cu", 100.0, 100.0, 123.0, 107.0)
_e = next(z for z in _B0.Zones() if z.GetIsRuleArea() and z.GetZoneName() == "ESCAPE_U401").GetBoundingBox()
ESC_F = free_strip(_B0, "F.Cu", TM(_e.GetLeft()) + 0.3, TM(_e.GetTop()) + 0.3, TM(_e.GetRight()) - 0.3, TM(_e.GetBottom()) - 0.3, length=1.6, margin=0.45)   # inside U401's escape area on F.Cu

# (name, rule expected, fires?, where (x, y), function adding the item)
CASES = [
    # the busbar rules (D01; the GND bar's since D33 B, user 2026-11-12: signal tracks allowed under it on F.Cu)
    ("SDA track on F.Cu under the GND busbar (control, D33 B: a signal may run there; pours refilled)", "F.Cu under the GND busbar", False, BAR_GND,
     lambda b: track(b, SDA, "F.Cu", BAR_GND[0], BAR_GND[1], BAR_GND[0] + 6, BAR_GND[1], 0.15)),
    ("VBAT_PROT track on F.Cu under the GND busbar (class PWR_BATT; pours refilled)", "F.Cu under the GND busbar: no battery-net tracks", True, BAR_GND,
     lambda b: track(b, "VBAT_PROT", "F.Cu", BAR_GND[0], BAR_GND[1], BAR_GND[0] + 6, BAR_GND[1], 0.3)),
    ("RS_SENSE_P track on F.Cu under the GND busbar (battery potential, named in the rule; pours refilled)", "F.Cu under the GND busbar: no battery-net tracks", True, BAR_GND,
     lambda b: track(b, "/Power entry/RS_SENSE_P", "F.Cu", BAR_GND[0], BAR_GND[1], BAR_GND[0] + 6, BAR_GND[1], 0.15)),
    ("VBAT_FILT track on F.Cu under the GND busbar (named in the rule; pours refilled)", "F.Cu under the GND busbar: no battery-net tracks", True, BAR_GND,
     lambda b: track(b, "VBAT_FILT", "F.Cu", BAR_GND[0], BAR_GND[1], BAR_GND[0] + 6, BAR_GND[1], 0.3)),
    ("SDA pour on F.Cu under the GND busbar", "F.Cu under the GND busbar: no other net's pour", True, BAR_GND,
     lambda b: pour(b, SDA, "F.Cu", BAR_GND[0], BAR_GND[1] - 1, BAR_GND[0] + 6, BAR_GND[1] + 1)),
    ("SDA track on F.Cu under the VBAT_IN busbar (unchanged by D33; pours refilled)", "F.Cu under the VBAT_IN busbar", True, BAR_VIN,
     lambda b: track(b, SDA, "F.Cu", BAR_VIN[0], BAR_VIN[1], BAR_VIN[0] + 6, BAR_VIN[1], 0.15)),
    ("SDA track on B.Cu under the VBAT_IN busbar (control: the rule is F.Cu's; pours refilled)", "F.Cu under the VBAT_IN busbar", False, BAR_VIN_B,
     lambda b: track(b, SDA, "B.Cu", BAR_VIN_B[0], BAR_VIN_B[1], BAR_VIN_B[0] + 6, BAR_VIN_B[1], 0.15)),
    ("free spot: nothing fires on a 0.2 mm track", "Tracks under 0.15", False, FREE,
     lambda b: track(b, SDA, "B.Cu", FREE[0], FREE[1], FREE[0] + 6, FREE[1], 0.2)),
    ("0.1 mm track outside the escape areas", "Tracks under 0.15 mm only in the U401/U501 escape areas", True, FREE,
     lambda b: track(b, SDA, "B.Cu", FREE[0], FREE[1], FREE[0] + 6, FREE[1], 0.1)),
    # ESC_F: a copper-free 1.6 mm strip of F.Cu inside U401's escape area (found on the board as it is, routed or not)
    ("0.1 mm track inside ESCAPE_U401 (F.Cu)", "Tracks under 0.15", False, ESC_F,
     lambda b: track(b, SDA, "F.Cu", ESC_F[0], ESC_F[1], ESC_F[0] + 1.6, ESC_F[1], 0.1)),
    ("0.1 mm clearance inside ESCAPE_U401: no clearance error (pours refilled round the planted tracks)", "Escape areas", False, ESC_F,
     lambda b: (track(b, SDA, "F.Cu", ESC_F[0], ESC_F[1] - 0.1, ESC_F[0] + 1.6, ESC_F[1] - 0.1, 0.1), track(b, SCL, "F.Cu", ESC_F[0], ESC_F[1] + 0.1, ESC_F[0] + 1.6, ESC_F[1] + 0.1, 0.1))),
    ("0.1 mm clearance outside: netclass 0.15 fires", "clearance", True, FREE,
     lambda b: (track(b, SDA, "B.Cu", FREE[0], FREE[1], FREE[0] + 6, FREE[1], 0.2),
                track(b, SCL, "B.Cu", FREE[0], FREE[1] + 0.3, FREE[0] + 6, FREE[1] + 0.3, 0.2))),
    ("0.12 mm track on In2.Cu", "Inner 2 oz layers", True, FREE,
     lambda b: track(b, SDA, "In2.Cu", FREE[0], FREE[1], FREE[0] + 6, FREE[1], 0.12)),
    ("via on 1V5_CORE_SW", "No vias on the buck switch nodes", True, FREE,
     lambda b: via(b, "/Regulators/1V5_CORE_SW", FREE[0], FREE[1])),
    ("via on 3V3_MAIN (control)", "No vias on the buck switch nodes", False, FREE,
     lambda b: via(b, "3V3_MAIN", FREE[0], FREE[1])),
    ("FB track 0.5 mm from a SW track", "1V5_CORE_FB 1 mm", True, FREE,
     lambda b: (track(b, "/Regulators/1V5_CORE_FB", "B.Cu", FREE[0], FREE[1], FREE[0] + 6, FREE[1], 0.2),
                track(b, "/Regulators/1V5_CORE_SW", "B.Cu", FREE[0], FREE[1] + 0.7, FREE[0] + 6, FREE[1] + 0.7, 0.3))),
    ("VBAT_PROT track on B.Cu under Y401", "Under Y401", True, None,
     lambda b: track(b, "VBAT_PROT", "B.Cu", centre(b, "Y401")[0] - 1, centre(b, "Y401")[1],
                     centre(b, "Y401")[0] + 1, centre(b, "Y401")[1], 0.2)),
    ("VBAT_PROT track on In3.Cu under Y401 (plane layer, allowed)", "Under Y401", False, None,
     lambda b: track(b, "VBAT_PROT", "In3.Cu", centre(b, "Y401")[0] - 1, centre(b, "Y401")[1],
                     centre(b, "Y401")[0] + 1, centre(b, "Y401")[1], 0.2)),
    ("GND track on B.Cu under Y401 (allowed)", "Under Y401", False, None,
     lambda b: track(b, "GND", "B.Cu", centre(b, "Y401")[0] - 1, centre(b, "Y401")[1],
                     centre(b, "Y401")[0] + 1, centre(b, "Y401")[1], 0.2)),
    ("SDA via under Y501", "Under Y501", True, None,
     lambda b: via(b, SDA, *centre(b, "Y501"))),
    ("other-net track on In2.Cu 0.32 mm from J904 pin 1's hole, its unused inner copper removed", "Plated holes 0.35 mm", True, None,
     lambda b: (pad_of(b, "J904", "1").SetRemoveUnconnected(True), b.BuildConnectivity(),
                track(b, SDA, "In2.Cu", TM(pad_of(b, "J904", "1").GetPosition().x) + 0.925 + 0.32 + 0.1,
                     TM(pad_of(b, "J904", "1").GetPosition().y) - 3,
                     TM(pad_of(b, "J904", "1").GetPosition().x) + 0.925 + 0.32 + 0.1,
                     TM(pad_of(b, "J904", "1").GetPosition().y) + 3, 0.2))),
    ("0.8 mm text on F.Silkscreen", "Silk text 1.0 mm", True, FREE,
     lambda b: text(b, "F.Silkscreen", FREE[0] + 3, FREE[1], 0.8)),
    ("1.0 mm text on F.Silkscreen (control)", "Silk text 1.0 mm", False, FREE,
     lambda b: text(b, "F.Silkscreen", FREE[0] + 3, FREE[1], 1.0, 0.15)),
    ("T1S pair 6 mm side by side at 0.3 mm gap inside a T1S_COUPLED_F area", "T1S pairs coupled", True, FREE,
     lambda b: (area(b, "T1S_COUPLED_F", "B.Cu", FREE[0] - 1, FREE[1] - 1, FREE[0] + 7, FREE[1] + 1.5),
                track(b, "/T1S_P", "B.Cu", FREE[0], FREE[1], FREE[0] + 6, FREE[1], 0.165),
                track(b, "/T1S_N", "B.Cu", FREE[0], FREE[1] + 0.465, FREE[0] + 6, FREE[1] + 0.465, 0.165))),
    ("the same pair outside the T1S_COUPLED areas (control, D28: the gap is checked where the line is meant to be coupled)",
     "T1S pairs coupled", False, FREE,
     lambda b: (track(b, "/T1S_P", "B.Cu", FREE[0], FREE[1], FREE[0] + 6, FREE[1], 0.165),
                track(b, "/T1S_N", "B.Cu", FREE[0], FREE[1] + 0.465, FREE[0] + 6, FREE[1] + 0.465, 0.165))),
    ("trunk pair coupled at 0.15 mm, P 4 mm longer (control: the trunk's uncoupled length is not a DRC rule since D16)",
     "T1S PHY-side pairs", False, FREE,
     lambda b: (track(b, "/T1S_P", "B.Cu", FREE[0], FREE[1], FREE[0] + 10, FREE[1], 0.165),
                track(b, "/T1S_N", "B.Cu", FREE[0], FREE[1] + 0.315, FREE[0] + 6, FREE[1] + 0.315, 0.165))),
    ("PHY pair FL501 to U501, P about 2 mm longer by a detour (skew, pad to pad: KiCad measures"
     " skew only on tracks that reach the pads)", "T1S PHY pair matched within 0.5 mm", True, None,
     lambda b: phy_pair(b, detour=1.0)),
    ("PHY pair FL501 to U501 straight (control: no crossing since D31, so 0.5 mm holds)",
     "T1S PHY pair matched within 0.5 mm", False, None,
     lambda b: phy_pair(b)),
    ("CMC pair C511/C512 to FL501, P 2 mm longer by a detour (FL501)", "T1S pairs matched within 0.5 mm", True, None,
     lambda b: cmc_pair(b, detour=1.5)),
    ("PHY-side pair FL501 to U501 split 3 mm apart (uncoupled)", "T1S PHY-side pairs: 2 mm uncoupled", True, None,
     lambda b: phy_pair(b, split=3.0)),
    ("trunk J912 to J903 with 2.8 mm breakouts at each connector (control: no uncoupled or skew rule on the trunk)",
     "T1S PHY-side pairs", False, (155, 46),
     lambda b: (clear(b, "/T1S_P", "/T1S_N"), track(b, "/T1S_P", "F.Cu", 137.6, 46, 140.2, 45.85, 0.165), track(b, "/T1S_P", "F.Cu", 140.2, 45.85, 174.0, 45.85, 0.165),
                track(b, "/T1S_P", "F.Cu", 174.0, 45.85, 176.6, 46, 0.165),
                track(b, "/T1S_N", "F.Cu", 133.4, 46, 136.0, 46.165, 0.165), track(b, "/T1S_N", "F.Cu", 136.0, 46.165, 169.8, 46.165, 0.165),
                track(b, "/T1S_N", "F.Cu", 169.8, 46.165, 172.4, 46, 0.165))),
    ("T1S_P track 0.4 mm from an SDA track", "T1S 0.75 mm", True, FREE,
     lambda b: (track(b, "/T1S_P", "B.Cu", FREE[0], FREE[1], FREE[0] + 6, FREE[1], 0.165),
                track(b, SDA, "B.Cu", FREE[0], FREE[1] + 0.6, FREE[0] + 6, FREE[1] + 0.6, 0.2))),
    ("T1S_P track 0.4 mm from an SDA track inside a T1S_PINS_U501 area (control, D28: VDDA beside TRXP)", "T1S 0.75 mm", False, FREE,
     lambda b: (area(b, "T1S_PINS_U501", "B.Cu", FREE[0] - 1, FREE[1] - 1, FREE[0] + 7, FREE[1] + 1.5),
                track(b, "/T1S_P", "B.Cu", FREE[0], FREE[1], FREE[0] + 6, FREE[1], 0.165),
                track(b, SDA, "B.Cu", FREE[0], FREE[1] + 0.6, FREE[0] + 6, FREE[1] + 0.6, 0.2))),
    ("T1S_P_DROP track 0.4 mm from an SDA track (relay leg in the class)", "T1S 0.75 mm", True, FREE,
     lambda b: (track(b, "/T1S/T1S_P_DROP", "B.Cu", FREE[0], FREE[1], FREE[0] + 6, FREE[1], 0.165),
                track(b, SDA, "B.Cu", FREE[0], FREE[1] + 0.6, FREE[0] + 6, FREE[1] + 0.6, 0.2))),
    ("3V3_MAIN_SW track 5 mm from a T1S_N track", "Buck switch nodes 10 mm", True, FREE,
     lambda b: (track(b, "/T1S_N", "B.Cu", FREE[0], FREE[1], FREE[0] + 6, FREE[1], 0.165),
                track(b, "/Regulators/3V3_MAIN_SW", "B.Cu", FREE[0], FREE[1] + 5, FREE[0] + 6, FREE[1] + 5, 0.6))),
]


def run_case(i, case, src):
    name, rule, fires, where, add = case
    d = tempfile.mkdtemp(prefix=f"rule{i:02d}_")
    for ext in ("kicad_pro", "kicad_dru"):
        shutil.copy(os.path.join(ROOT, f"node60.{ext}"), os.path.join(d, f"node60.{ext}"))
    b = pcbnew.LoadBoard(src)
    add(b)
    if where is None:
        where = centre(b, "FL501") if "FL501" in name else centre(b, "Y401") if "Y401" in name else centre(b, "Y501") if "Y501" in name else \
            (TM(pad_of(b, "J904", "1").GetPosition().x) + 1.3, TM(pad_of(b, "J904", "1").GetPosition().y))
    path = os.path.join(d, "node60.kicad_pcb")
    b.Save(path)
    return name, rule, fires, where, path


def drc(path, refill=False):
    """refill: the case adds a via, which since the power shapes (2026-11-04) lands on plane copper;
    without a refill DRC reports the short and not the rule under test"""
    out = path + ".drc.json"
    subprocess.run([KICAD_CLI, "pcb", "drc", "--format", "json", "--units", "mm", "-o", out]
                   + (["--refill-zones"] if refill else []) + [path], capture_output=True)
    return json.load(open(out))


def near(v, where, r=3.0):
    if "Skew" in v["description"] or "uncoupled" in v["description"]:       # reported at the pair's ends
        r = 45.0
    for it in v.get("items", []):
        p = it.get("pos", {})
        if abs(p.get("x", 1e9) - where[0]) <= r + 6 and abs(p.get("y", 1e9) - where[1]) <= r + 6:
            return True
    return False


def zone_case(src):
    """R201 pad 1 (VBAT_D, PWR_BATT) should fill solid; C203 pad 2 (VBAT_PROT, an 0402) keep its relief."""
    results = []
    for ref, num, expect_solid in (("R201", "1", True), ("C203", "2", False)):
        b = pcbnew.LoadBoard(src)
        pad = pad_of(b, ref, num)
        layer = pcbnew.B_Cu if pad.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu
        bb = pad.GetBoundingBox()
        z = pcbnew.ZONE(b)
        z.SetLayer(layer)
        z.SetNet(pad.GetNet())
        z.SetAssignedPriority(100)
        o = z.Outline()
        o.NewOutline()
        m = FM(1.5)
        for x, y in ((bb.GetLeft() - m, bb.GetTop() - m), (bb.GetRight() + m, bb.GetTop() - m),
                     (bb.GetRight() + m, bb.GetBottom() + m), (bb.GetLeft() - m, bb.GetBottom() + m)):
            o.Append(int(x), int(y))
        b.Add(z)
        pcbnew.ZONE_FILLER(b).Fill([z])
        # just off each corner of the pad: solid fill reaches at least one (a routed track may stand beside another)
        fill = z.GetFilledPolysList(layer)
        filled = any(fill.Contains(pcbnew.VECTOR2I(x, y)) for x in (bb.GetLeft() - FM(0.12), bb.GetRight() + FM(0.12))
                     for y in (bb.GetTop() - FM(0.12), bb.GetBottom() + FM(0.12)))
        ok = filled == expect_solid
        results.append((f"zone fill at {ref} pad {num}: {'solid' if filled else 'relief'}",
                        "High-current pads solid", expect_solid, ok))
    return results


def t1s_pour_case(src):
    """A T1S via in an inner GND pour and in an outer SDA pour: on the outer layers the pour keeps 0.75 mm,
    on the inner ones it keeps the ordinary clearance (D28, the fourth change). Probed 0.6 mm from the via."""
    results = []
    for layer, net, expect_filled in (("In1.Cu", "GND", True), ("B.Cu", SDA, False)):
        b = pcbnew.LoadBoard(src)
        x, y = FREE[0] + 3, FREE[1]
        via(b, "/T1S_P", x, y)
        z = pcbnew.ZONE(b); z.SetLayer(b.GetLayerID(layer)); z.SetNet(b.FindNet(net)); z.SetAssignedPriority(100)
        o = z.Outline(); o.NewOutline()
        for dx, dy in ((-2, -2), (2, -2), (2, 2), (-2, 2)):
            o.Append(FM(x + dx), FM(y + dy))
        b.Add(z)
        pcbnew.ZONE_FILLER(b).Fill([z])
        filled = z.GetFilledPolysList(b.GetLayerID(layer)).Contains(pcbnew.VECTOR2I(FM(x + 0.6), FM(y)))
        results.append((f"{net} pour on {layer} round a T1S via: copper 0.6 mm from it {'yes' if filled else 'no'}",
                        "T1S 0.75 mm (pours on the outer layers only)", not expect_filled, filled == expect_filled))
    return results


def main():
    src = os.path.join(ROOT, BOARD)
    prepared = [run_case(i, c, src) for i, c in enumerate(CASES)]
    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        reports = list(ex.map(lambda p: drc(p[4], refill=" via " in f" {p[0]} " or "refilled" in p[0]), prepared))
    failed = 0
    for (name, rule, fires, where, path), rep in zip(prepared, reports):
        hits = [v for v in rep.get("violations", []) if rule in v["description"] and near(v, where)]
        ok = bool(hits) == fires
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {'fires' if fires else 'quiet'}  {name}  "
              f"[{hits[0]['description'][:90] if hits else 'no ' + repr(rule)}]")
    extra = zone_case(src) + t1s_pour_case(src)
    for name, rule, fires, ok in extra:
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {'fires' if fires else 'quiet'}  {name}  [{rule}]")
    print(f"{len(CASES) + len(extra) - failed} of {len(CASES) + len(extra)} cases pass")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
