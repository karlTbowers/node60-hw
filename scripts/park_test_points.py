#!/usr/bin/env python3
"""Park the test points off the board while routing, and put them back (Node60, 2026-11-05).

    $KPY scripts/park_test_points.py park    BOARD PARKED.json [-o OUT]
    $KPY scripts/park_test_points.py restore BOARD PARKED.json [-o OUT]

User, 2026-11-05: test points may go wherever routing is easier; "pull the test points off the
board and not worry about them while routing. we can add them back later."

`park` moves every TP* footprint to a grid south of the outline (y 146 on), so the footprints stay
on the board file and schematic parity holds, and writes PARKED.json with each one's pose before
(x, y, rot, side). Copper at a test point: a track that ran through its pad (two tracks on one
layer ending in it) is closed with a straight segment between the two ends; a stub that ended in
it is deleted back to the first point that touches other copper (a via left behind in a plane
stays). `restore` puts each listed test point back at its recorded pose; its stubs are drawn
again by hand or by draw_power.py. The handbook's test points must be on the board before
routing sign-off.
"""
import argparse
import json

import pcbnew

GRID_X0, GRID_Y0, PITCH, PER_ROW = 45.0, 146.0, 3.5, 60


def mm(v):
    return round(pcbnew.ToMM(v), 4)


TOL = pcbnew.FromMM(0.01)


def at(b, net, pt, gone, reach=TOL):
    """The net's tracks whose copper end meets pt (within reach plus half their width), vias whose
    ring covers pt, and whether a pad covers pt."""
    tr, vi = [], []
    for t in b.GetTracks():
        if t.GetNetname() != net or t.m_Uuid.AsString() in gone:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            if (t.GetPosition() - pt).EuclideanNorm() <= t.GetWidth(pcbnew.F_Cu) / 2 + reach:
                vi.append(t)
        elif min((t.GetStart() - pt).EuclideanNorm(), (t.GetEnd() - pt).EuclideanNorm()) <= t.GetWidth() / 2 + reach:
            tr.append(t)
    pad = any(p.GetNetname() == net and p.HitTest(pt, TOL) for f in b.GetFootprints()
              if not f.GetReference().startswith("TP") for p in f.Pads())
    return tr, vi, pad


def far(t, pt):
    return t.GetEnd() if (t.GetStart() - pt).EuclideanNorm() < (t.GetEnd() - pt).EuclideanNorm() else t.GetStart()


def prune(b, net, items, gone):
    """Remove items (tracks with the end they enter by, or vias) and walk on while the copper is a
    plain stub: a bend with one more track, or a via with one more track; stop at a junction, a pad
    or a via that carries more."""
    n = 0
    work = list(items)
    while work:
        it, pt = work.pop()
        if it.m_Uuid.AsString() in gone:
            continue
        gone.add(it.m_Uuid.AsString()); n += 1
        if it.Type() == pcbnew.PCB_VIA_T:
            tr, vi, pad = at(b, net, it.GetPosition(), gone, it.GetWidth(pcbnew.F_Cu) / 2)
            if len(tr) == 1 and not pad:
                work.append((tr[0], it.GetPosition()))
            continue
        q = far(it, pt)
        tr, vi, pad = at(b, net, q, gone)
        if pad:
            continue
        if vi and not tr:
            v = vi[0]
            t2, _, _ = at(b, net, v.GetPosition(), gone, v.GetWidth(pcbnew.F_Cu) / 2)
            if len(t2) <= 1:
                work.append((v, v.GetPosition()))
            continue
        if len(tr) == 1 and not vi:
            work.append((tr[0], q))
    return n


def park(a):
    b = pcbnew.LoadBoard(a.board)
    tps = sorted([f for f in b.GetFootprints() if f.GetReference().startswith("TP")],
                 key=lambda f: int("".join(c for c in f.GetReference() if c.isdigit()) or 0))
    rec, closed, dropped, gone = {}, 0, 0, set()
    for i, f in enumerate(tps):
        pos = f.GetPosition()
        if mm(pos.y) >= GRID_Y0 - 1:
            continue                                   # already parked
        rec[f.GetReference()] = {"x": mm(pos.x), "y": mm(pos.y), "rot": f.GetOrientationDegrees(),
                                 "side": "B" if f.IsFlipped() else "F"}
        for p in f.Pads():
            net = p.GetNetname()
            ends, vias = [], []
            for t in b.GetTracks():
                if t.GetNetname() != net:
                    continue
                if t.Type() == pcbnew.PCB_VIA_T:
                    if p.HitTest(t.GetPosition(), TOL):
                        vias.append((t, t.GetPosition()))
                elif p.IsOnLayer(t.GetLayer()):
                    for e in (t.GetStart(), t.GetEnd()):
                        if p.HitTest(e, TOL):
                            ends.append((t, e))
            if len(ends) == 2 and not vias and ends[0][0].GetLayer() == ends[1][0].GetLayer():
                s = pcbnew.PCB_TRACK(b)                # a route through the pad: close it
                s.SetStart(ends[0][1]); s.SetEnd(ends[1][1]); s.SetLayer(ends[0][0].GetLayer())
                s.SetWidth(min(ends[0][0].GetWidth(), ends[1][0].GetWidth())); s.SetNet(ends[0][0].GetNet())
                b.Add(s); closed += 1
            elif ends or vias:
                dropped += prune(b, net, ends + vias, gone)
        f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(GRID_X0 + (i % PER_ROW) * PITCH),
                                      pcbnew.FromMM(GRID_Y0 + (i // PER_ROW) * PITCH)))
    for t in list(b.GetTracks()):
        if t.m_Uuid.AsString() in gone:
            b.Remove(t)
    old = {}
    try:
        old = json.load(open(a.parked))
    except (OSError, ValueError):
        pass
    old.update(rec)
    json.dump(old, open(a.parked, "w"), indent=1, sort_keys=True)
    b.Save(a.o or a.board)
    print(f"parked {len(rec)} test points ({closed} routes closed through a pad, {dropped} stub items deleted); poses in {a.parked}")


def restore(a):
    b = pcbnew.LoadBoard(a.board)
    rec = json.load(open(a.parked))
    for ref, p in rec.items():
        f = b.FindFootprintByReference(ref)
        if f is None:
            continue
        f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(p["x"]), pcbnew.FromMM(p["y"])))
        f.SetOrientationDegrees(p["rot"])
    b.Save(a.o or a.board)
    print(f"restored {len(rec)} test points")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["park", "restore"]); ap.add_argument("board"); ap.add_argument("parked")
    ap.add_argument("-o")
    a = ap.parse_args()
    park(a) if a.cmd == "park" else restore(a)
