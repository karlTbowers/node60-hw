#!/usr/bin/env python3
"""Copy the tracks and vias of some nets from a router's board onto a real board (Node60, 2026-11-05).

    $KPY transplant_nets.py ROUTED.kicad_pcb REAL.kicad_pcb OUT.kicad_pcb NET [NET ...] [--lock]

The judge's boards (judge_route.sh) have the busbar footprints removed and ring pads redrawn for the
router, so DRC there is not evidence. This puts only the named nets' copper on the real board, refills
its zones and saves OUT; KiCad DRC with the board's own rules judges that. --lock locks what it adds.
"""
import sys

import pcbnew


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    lock = "--lock" in sys.argv
    src, dst = pcbnew.LoadBoard(args[0]), pcbnew.LoadBoard(args[1])
    nets = set(args[3:])
    n = nv = 0
    for t in src.GetTracks():
        if t.GetNetname() not in nets:
            continue
        net = dst.FindNet(t.GetNetname())
        if t.Type() == pcbnew.PCB_VIA_T:
            o = pcbnew.PCB_VIA(dst); o.SetPosition(t.GetPosition()); o.SetWidth(t.GetWidth()); o.SetDrill(t.GetDrill()); nv += 1
        elif t.Type() == pcbnew.PCB_ARC_T:
            o = pcbnew.PCB_ARC(dst); o.SetStart(t.GetStart()); o.SetMid(t.GetMid()); o.SetEnd(t.GetEnd())
            o.SetWidth(t.GetWidth()); o.SetLayer(t.GetLayer()); n += 1
        else:
            o = pcbnew.PCB_TRACK(dst); o.SetStart(t.GetStart()); o.SetEnd(t.GetEnd())
            o.SetWidth(t.GetWidth()); o.SetLayer(t.GetLayer()); n += 1
        o.SetNet(net); o.SetLocked(lock); dst.Add(o)
    pcbnew.ZONE_FILLER(dst).Fill(dst.Zones())
    dst.Save(args[2])
    print(f"{n} tracks, {nv} vias of {len(nets)} nets onto {args[2]}")


if __name__ == "__main__":
    main()
