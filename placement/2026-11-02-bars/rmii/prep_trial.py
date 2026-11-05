#!/usr/bin/env python3
"""A trial board for the RMII clock work (Node60, 2026-11-05).

    $KPY prep_trial.py BOARD OUT.kicad_pcb [--move REF=X,Y,ROT ...] [--to-bottom REF] [--strip]

--strip deletes every track and via of the RMII/MDIO nets and the three clock nets (the router
starts clean); --move sets a part's pose (its side unchanged). Zones are refilled.
"""
import sys

import pcbnew

NETS = ["/RMII0_T1S_TXD0", "/RMII0_T1S_TXD1", "/RMII0_T1S_TX_EN", "/RMII0_T1S_RXD0", "/RMII0_T1S_RXD1",
        "/RMII0_T1S_CRS_DV", "/RMII0_T1S_RX_ER", "/RMII0_T1S_REF_CLK", "/MDIO0_T1S_MDC", "/MDIO0_T1S_MDIO",
        "/T1S/T1S_OSC_OUT", "/T1S/T1S_REFCLK"]


def main():
    args = sys.argv[1:]
    b = pcbnew.LoadBoard(args[0])
    out = args[1]
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    n = 0
    if "--strip" in args:
        for t in list(b.GetTracks()):
            if t.GetNetname() in NETS:
                b.Delete(t); n += 1
    for i, a in enumerate(args):
        if a == "--move":
            ref, v = args[i + 1].split("=")
            x, y, r = (float(q) for q in v.split(","))
            f = fps[ref]
            if "--to-bottom" in args and args[args.index("--to-bottom") + 1] == ref and not f.IsFlipped():
                f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
            f.SetOrientationDegrees(r)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(out)
    print(f"{out}: {n} tracks/vias stripped")


if __name__ == "__main__":
    main()
