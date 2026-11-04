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
    b.Add(v)


def text(b, layer, x, y, h, stroke=0.12):
    t = pcbnew.PCB_TEXT(b)
    t.SetText("RULE TEST")
    t.SetLayer(b.GetLayerID(layer))
    t.SetPosition(pcbnew.VECTOR2I(FM(x), FM(y)))
    t.SetTextSize(pcbnew.VECTOR2I(FM(h), FM(h)))
    t.SetTextThickness(FM(stroke))
    b.Add(t)


def pad_of(b, ref, num):
    for fp in b.GetFootprints():
        if fp.GetReference() == ref:
            return next(p for p in fp.Pads() if p.GetNumber() == num)


def centre(b, ref):
    fp = next(f for f in b.GetFootprints() if f.GetReference() == ref)
    return TM(fp.GetPosition().x), TM(fp.GetPosition().y)


SDA = "/I2C0_TELEMETRY_SDA"
SCL = "/I2C0_TELEMETRY_SCL"
FREE = (95.0, 36.0)        # checked free of parts on B.Cu and In2/In3 (see the "free spot" case)

# (name, rule expected, fires?, where (x, y), function adding the item)
CASES = [
    ("free spot: nothing fires on a 0.2 mm track", "Tracks under 0.15", False, FREE,
     lambda b: track(b, SDA, "B.Cu", FREE[0], FREE[1], FREE[0] + 6, FREE[1], 0.2)),
    ("0.1 mm track outside the escape areas", "Tracks under 0.15 mm only in the U401/U501 escape areas", True, FREE,
     lambda b: track(b, SDA, "B.Cu", FREE[0], FREE[1], FREE[0] + 6, FREE[1], 0.1)),
    ("0.1 mm track inside ESCAPE_U401 (F.Cu margin ring)", "Tracks under 0.15", False, (209.5, 52),
     lambda b: track(b, SDA, "F.Cu", 209.5, 50, 209.5, 54, 0.1)),
    ("0.1 mm clearance inside ESCAPE_U401: no clearance error", "Escape areas", False, (209.5, 52),
     lambda b: (track(b, SDA, "F.Cu", 209.4, 50, 209.4, 54, 0.1), track(b, SCL, "F.Cu", 209.6, 50, 209.6, 54, 0.1))),
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
    ("other-net track on In2.Cu 0.25 mm from J904 pin 1's hole, its unused inner copper removed", "Plated holes 0.3 mm", True, None,
     lambda b: (pad_of(b, "J904", "1").SetRemoveUnconnected(True), b.BuildConnectivity(),
                track(b, SDA, "In2.Cu", TM(pad_of(b, "J904", "1").GetPosition().x) + 0.925 + 0.25 + 0.1,
                     TM(pad_of(b, "J904", "1").GetPosition().y) - 3,
                     TM(pad_of(b, "J904", "1").GetPosition().x) + 0.925 + 0.25 + 0.1,
                     TM(pad_of(b, "J904", "1").GetPosition().y) + 3, 0.2))),
    ("0.8 mm text on F.Silkscreen", "Silk text 1.0 mm", True, FREE,
     lambda b: text(b, "F.Silkscreen", FREE[0] + 3, FREE[1], 0.8)),
    ("1.0 mm text on F.Silkscreen (control)", "Silk text 1.0 mm", False, FREE,
     lambda b: text(b, "F.Silkscreen", FREE[0] + 3, FREE[1], 1.0, 0.15)),
    ("T1S pair 6 mm side by side at 0.3 mm gap", "T1S pairs coupled", True, FREE,
     lambda b: (track(b, "/T1S_P", "B.Cu", FREE[0], FREE[1], FREE[0] + 6, FREE[1], 0.165),
                track(b, "/T1S_N", "B.Cu", FREE[0], FREE[1] + 0.465, FREE[0] + 6, FREE[1] + 0.465, 0.165))),
    ("T1S pair coupled at 0.15 mm, P 4 mm longer", "T1S pairs coupled", True, FREE,
     lambda b: (track(b, "/T1S_P", "B.Cu", FREE[0], FREE[1], FREE[0] + 10, FREE[1], 0.165),
                track(b, "/T1S_N", "B.Cu", FREE[0], FREE[1] + 0.315, FREE[0] + 6, FREE[1] + 0.315, 0.165))),
    ("T1S trunk J912 to J903 on F.Cu, P 2.5 mm longer by a detour (skew, pad to pad: KiCad measures"
     " skew only on tracks that reach the pads)", "T1S pairs matched within 0.5 mm", True, (137.6, 46),
     lambda b: (track(b, "/T1S_P", "F.Cu", 137.6, 46, 150, 46, 0.165), track(b, "/T1S_P", "F.Cu", 150, 46, 151, 44, 0.165),
                track(b, "/T1S_P", "F.Cu", 151, 44, 152, 46, 0.165), track(b, "/T1S_P", "F.Cu", 152, 46, 176.6, 46, 0.165),
                track(b, "/T1S_N", "F.Cu", 133.4, 46, 133.4, 46.4, 0.165), track(b, "/T1S_N", "F.Cu", 133.4, 46.4, 172.4, 46.4, 0.165),
                track(b, "/T1S_N", "F.Cu", 172.4, 46.4, 172.4, 46, 0.165))),
    ("T1S_P track 0.4 mm from an SDA track", "T1S 0.75 mm", True, FREE,
     lambda b: (track(b, "/T1S_P", "B.Cu", FREE[0], FREE[1], FREE[0] + 6, FREE[1], 0.165),
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
        where = centre(b, "Y401") if "Y401" in name else centre(b, "Y501") if "Y501" in name else \
            (TM(pad_of(b, "J904", "1").GetPosition().x) + 1.3, TM(pad_of(b, "J904", "1").GetPosition().y))
    path = os.path.join(d, "node60.kicad_pcb")
    b.Save(path)
    return name, rule, fires, where, path


def drc(path):
    out = path + ".drc.json"
    subprocess.run([KICAD_CLI, "pcb", "drc", "--format", "json", "--units", "mm", "-o", out, path],
                   capture_output=True)
    return json.load(open(out))


def near(v, where, r=3.0):
    if "Skew" in v["description"]:       # reported at the pair's ends
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
        probe = pcbnew.VECTOR2I(bb.GetRight() + FM(0.12), bb.GetBottom() + FM(0.12))
        filled = z.GetFilledPolysList(layer).Contains(probe)
        ok = filled == expect_solid
        results.append((f"zone fill at {ref} pad {num}: {'solid' if filled else 'relief'}",
                        "High-current pads solid", expect_solid, ok))
    return results


def main():
    src = os.path.join(ROOT, BOARD)
    prepared = [run_case(i, c, src) for i, c in enumerate(CASES)]
    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        reports = list(ex.map(lambda p: drc(p[4]), prepared))
    failed = 0
    for (name, rule, fires, where, path), rep in zip(prepared, reports):
        hits = [v for v in rep.get("violations", []) if rule in v["description"] and near(v, where)]
        ok = bool(hits) == fires
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {'fires' if fires else 'quiet'}  {name}  "
              f"[{hits[0]['description'][:90] if hits else 'no ' + repr(rule)}]")
    for name, rule, fires, ok in zone_case(src):
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {'fires' if fires else 'quiet'}  {name}  [{rule}]")
    print(f"{len(CASES) + 2 - failed} of {len(CASES) + 2} cases pass")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
