#!/usr/bin/env python3
"""fr_export.py BOARD OUT.dsn [--open-planes] -- a Specctra DSN of the board for Freerouting (trial, 2026-11-12). KiCad's Python.
BOARD is a scratch copy (it is changed and saved): run route_hook.py on it first for the T1S keep-outs.
- the parked test points are deleted (user: Freerouting may not know to disregard pads off the board);
- rule areas that forbid neither tracks nor vias are deleted: KiCad exports them as full keep-outs, which
  walled off U401's and U501's escape areas and the whole In2 signal window;
- the busbar areas forbid tracks (the custom rule "F.Cu under a busbar" is not in a DSN);
- UNDER_Y401/Y501 forbid vias (route_hook.py);
- --open-planes: Freerouting reads a tracks-not-allowed area as a full obstacle, vias included, so with the
  POWER_ONLY_* areas in the file it can place no via anywhere (run 1: 0 new vias). This deletes them and
  marks In3 a power layer instead (In1 and In4 already are), which Freerouting does not route on. In2 south
  of y 70 is then open to it: judge that with KiCad's DRC on the real board afterwards."""
import sys, re, pcbnew
openp = "--open-planes" in sys.argv
if openp: sys.argv.remove("--open-planes")
b = pcbnew.LoadBoard(sys.argv[1])
# pcbnew's Python objects go stale after a Remove: decide everything first, remove last
tps = [fp for fp in b.GetFootprints() if fp.GetReference().startswith("TP")]
drop = []
for z in b.Zones():
    if not z.GetIsRuleArea(): continue
    if z.GetZoneName().startswith("BUSBAR_"): z.SetDoNotAllowTracks(True)
    elif openp and z.GetZoneName().startswith("POWER_ONLY"): drop.append(z)
    elif not z.GetDoNotAllowTracks() and not z.GetDoNotAllowVias(): drop.append(z)
n, k = len(tps), len(drop)
for it in drop + tps: b.Remove(it)
b.Save(sys.argv[1])
b = pcbnew.LoadBoard(sys.argv[1])
print(f"{n} test points and {k} rule areas removed; dsn", pcbnew.ExportSpecctraDSN(b, sys.argv[2]))
if openp:
    t = open(sys.argv[2]).read()
    t, c = re.subn(r'(\(layer In3\.Cu[^\n]*\n\s*\(type )signal', r'\1power', t)
    open(sys.argv[2], "w").write(t); print("In3 marked power:", c)
