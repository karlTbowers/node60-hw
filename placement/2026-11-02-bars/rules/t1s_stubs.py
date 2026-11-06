#!/usr/bin/env python3
"""Measure Node60's T1S line: trunk, the PHY's stub, the relay legs, and what dangles past the
termination when the node is an end node (D16, 2026-11-03).

Run with KiCad's Python from the repo root:

    $KPY placement/2026-11-02-bars/rules/t1s_stubs.py [node60.kicad_pcb] [--estimate]

The line: J912 and J903 (pins 1 = T1S_P, 2 = T1S_N) are the trunk's two ends; the PHY taps it
through C511/C512 (DC block, pad 2 on the trunk net) -> FL501 -> U501 pins 30/31, and the relay
K501 taps it at pins 3/6 (its termination legs). Either connector may be the one a harness uses,
so each port is reported.

On a routed board every net's copper is a tree, so the distance from a branch pad C to the trunk
path between the connector pins A and B is (dAC + dBC - dAB) / 2, with d the routed path length
(tracks plus 2.0 mm per via, the board's thickness). Without copper on a net (or with
--estimate) it falls back to a pin-based estimate: the trunk a straight line at the connector
pins' y, the PHY's taps a vertical drop to each cap plus a via, both relay legs tapping the trunk on
K501's centre line (the routing plan) and then running to their pins, and straight lines pad to pad. The estimate
says so in its output.
"""
import argparse
import heapq
import math
from collections import defaultdict

import pcbnew

M = pcbnew.ToMM
VIA_MM = 2.0
# copper depth from F.Cu (JLC062012-1080, 2.0 mm): a via between two layers counts their distance
Z = {pcbnew.F_Cu: 0.0, pcbnew.In1_Cu: 0.17, pcbnew.In2_Cu: 0.79, pcbnew.In3_Cu: 1.17, pcbnew.In4_Cu: 1.79, pcbnew.B_Cu: 2.0}
NETS = {"P": ("/T1S_P", "/T1S/T1S_CMC_P", "/T1S/T1S_PHY_P", "1", "C511", "4", "1", "30", "3"),
        "N": ("/T1S_N", "/T1S/T1S_CMC_N", "/T1S/T1S_PHY_N", "2", "C512", "3", "2", "31", "6")}
# per line: trunk net, CMC net, PHY net, connector pin, DC-block cap, FL501 line pin, FL501 PHY pin,
# U501 pin, K501 pin


def pad(b, ref, num):
    fp = b.FindFootprintByReference(ref)
    return next(p for p in fp.Pads() if p.GetNumber() == num)


def xy(p):
    return M(p.GetPosition().x), M(p.GetPosition().y)


def graph(b, net):
    """nodes: (layer, x, y) rounded; edges: tracks, vias; pads joined to the copper they touch"""
    g = defaultdict(list)
    key = lambda l, x, y: (l, round(x, 3), round(y, 3))
    ends = []
    for t in b.GetTracks():
        if t.GetNetname() != net:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            x, y = xy(t)
            # every copper layer the via joins, each step weighted by its depth (F to B = VIA_MM, the
            # board's thickness): a tap that runs on In2 enters and leaves through part of the barrel
            stack = [l for l in b.GetEnabledLayers().CuStack() if t.IsOnLayer(l)]
            nodes = [key(l, x, y) for l in stack]
            for (l1, n1), (l2, n2) in zip(zip(stack, nodes), zip(stack[1:], nodes[1:])):
                w = abs(Z.get(l1, 0) - Z.get(l2, 0))
                g[n1].append((n2, w)); g[n2].append((n1, w))
            ends += [(n_, t) for n_ in nodes]
        else:
            s, e = t.GetStart(), t.GetEnd()
            a, c = key(t.GetLayer(), M(s.x), M(s.y)), key(t.GetLayer(), M(e.x), M(e.y))
            L = M(t.GetLength())
            g[a].append((c, L)); g[c].append((a, L))
            ends += [(a, t), (c, t)]
    # join coincident points on the same layer, and points inside a pad to that pad's node
    pads = [p for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname() == net]
    for p in pads:
        pn = ("pad", p.GetParentFootprint().GetReference(), p.GetNumber())
        for n, _ in ends:
            if p.IsOnLayer(n[0]) and p.HitTest(pcbnew.VECTOR2I(pcbnew.FromMM(n[1]), pcbnew.FromMM(n[2]))):
                g[pn].append((n, 0.0)); g[n].append((pn, 0.0))
    return g, bool(ends)


def dist(g, a, c):
    seen, q = {a: 0.0}, [(0.0, a)]
    while q:
        d, n = heapq.heappop(q)
        if n == c:
            return d
        if d > seen.get(n, 1e18):
            continue
        for m, w in g[n]:
            if d + w < seen.get(m, 1e18):
                seen[m] = d + w
                heapq.heappush(q, (d + w, m))
    return None


def by_net(b, ref, net, default):
    """the pad of ref on net (FL501's windings and K501's poles can swap, 2026-11-05), else default"""
    fp = b.FindFootprintByReference(ref)
    return next((p.GetNumber() for p in fp.Pads() if p.GetNetname() == net), default)


def measure(b, line, estimate):
    trunk, cmc, phy, jpin, cap, fl_line, fl_phy, upin, kpin = NETS[line]
    fl_line, fl_phy = by_net(b, "FL501", cmc, fl_line), by_net(b, "FL501", phy, fl_phy)
    kpin = by_net(b, "K501", trunk, kpin)
    A, B = pad(b, "J912", jpin), pad(b, "J903", jpin)
    C2, C1 = pad(b, cap, "2"), pad(b, cap, "1")
    K = pad(b, "K501", kpin)
    F_line, F_phy, U = pad(b, "FL501", fl_line), pad(b, "FL501", fl_phy), pad(b, "U501", upin)
    g, routed = graph(b, trunk)
    out = {}
    if routed and not estimate:
        n = lambda p: ("pad", p.GetParentFootprint().GetReference(), p.GetNumber())
        dAB, dAC, dBC = dist(g, n(A), n(B)), dist(g, n(A), n(C2)), dist(g, n(B), n(C2))
        dAK, dBK = dist(g, n(A), n(K)), dist(g, n(B), n(K))
        if None in (dAB, dAC, dBC, dAK, dBK):
            out["note"] = "trunk net not fully routed; estimate used"
        else:
            out.update(trunk=dAB, tap=(dAC + dBC - dAB) / 2, leg=(dAK + dBK - dAB) / 2,
                       # end node: the line dangles from the relay's tap to the unused connector
                       dangle_J912_used=dBK - (dAK + dBK - dAB) / 2, dangle_J903_used=dAK - (dAK + dBK - dAB) / 2)
            out["mode"] = "routed"
    if "mode" not in out:
        y = xy(A)[1]
        # both relay legs tap the trunk on the relay's centre line (the routing plan), then run to their pins
        kx = (xy(pad(b, "K501", "3"))[0] + xy(pad(b, "K501", "6"))[0]) / 2
        out.update(trunk=abs(xy(B)[0] - xy(A)[0]), tap=abs(xy(C2)[1] - y) + VIA_MM,
                   leg=abs(xy(K)[1] - y) + VIA_MM + abs(xy(K)[0] - kx),
                   dangle_J912_used=abs(xy(B)[0] - kx), dangle_J903_used=abs(kx - xy(A)[0]), mode="estimate")
    # cap, choke and the two short nets beyond them (routed length if routed, else straight)
    cap_len = math.dist(xy(C2), xy(C1))
    choke = math.dist(xy(F_line), xy(F_phy))
    rest = []
    for net, p, q in ((cmc, C1, F_line), (phy, F_phy, U)):
        gg, r = graph(b, net)
        nn = lambda pp: ("pad", pp.GetParentFootprint().GetReference(), pp.GetNumber())
        d = dist(gg, nn(p), nn(q)) if (r and not estimate) else None
        rest.append(d if d is not None else math.dist(xy(p), xy(q)))
    out["phy_stub"] = out["tap"] + cap_len + rest[0] + choke + rest[1]
    out["parts"] = dict(cap=cap_len, cap_to_choke=rest[0], choke=choke, choke_to_phy=rest[1])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board", nargs="?", default="node60.kicad_pcb")
    ap.add_argument("--estimate", action="store_true", help="pin-based estimate even where copper exists")
    a = ap.parse_args()
    b = pcbnew.LoadBoard(a.board)
    r = {k: measure(b, k, a.estimate) for k in ("P", "N")}
    print(f"T1S line on {a.board} ({r['P']['mode']}; lengths in mm, a via counted as {VIA_MM} mm)")
    rows = [("trunk J912 to J903", "trunk"), ("PHY stub: trunk to U501 pin", "phy_stub"),
            ("  of which the tap (trunk to cap)", "tap"), ("relay leg: trunk to K501 pin", "leg"),
            ("end node, J912 used: dangles past the relay", "dangle_J912_used"),
            ("end node, J903 used: dangles past the relay", "dangle_J903_used")]
    print(f"  {'':46s} {'P':>7s} {'N':>7s} {'P-N':>7s}")
    for label, k in rows:
        p, n = r["P"][k], r["N"][k]
        print(f"  {label:46s} {p:7.2f} {n:7.2f} {p - n:7.2f}")
    for k in ("P", "N"):
        if "note" in r[k]:
            print(f"  {k}: {r[k]['note']}")


if __name__ == "__main__":
    main()
