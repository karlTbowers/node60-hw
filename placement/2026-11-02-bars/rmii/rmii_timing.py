#!/usr/bin/env python3
"""RMII timing from the routed copper (Node60, 2026-11-05).

    $KPY rmii_timing.py BOARD.kicad_pcb [--json OUT.json]

For each RMII and MDIO net: the copper path length from its U501 pin to its U401 ball (shortest path
over the net's tracks and vias, strap stubs not counted), per layer, with via barrels by depth; the
flight time at 6.0 ps/mm on F/B (microstrip) and 7.0 ps/mm inside (stripline); and the REF_CLK
branches from Y501's output to U501 pin 27 (through R503) and to U401 U6 (through R504).

Then the four RMII windows (REF_CLK 50 MHz, 20 ns), worst case from the datasheets:
  LAN8670 (Table 7-15): output valid 12 ns max, invalid 3 ns min; input setup 4 ns, hold 1.5 ns.
  S32K344 (data sheet Table 58, RMII): input setup 4 ns, hold 2 ns; output valid 15 ns max at
  25 pF, invalid 2 ns min.
  dclk = clock at U401 minus clock at U501 (positive when the MCU's branch is longer): each
  branch's flight time plus its series resistor's RC, 0.69 x 33 ohm x (trace C + input C); trace C
  0.12 pF/mm outside, 0.14 pF/mm inside (50 ohm); input C: U401 2-6 pF plus 2 pF package
  (S32K3xx data sheet, GPIO CIN), U501 3 pF (LAN8670 ICLK CIN, design max). Each window takes the
  worst dclk for it (dclk_hi with U401 at 8 pF, dclk_lo at 4 pF).
  TX setup = 20 - 15 - t_tx - dclk - 4      TX hold = 2 + t_tx + dclk - 1.5
  RX setup = 20 - 12 - t_rx + dclk - 4      RX hold = 3 + t_rx - dclk - 2
"""
import heapq, json, sys
from collections import defaultdict

import pcbnew

PS = {"F.Cu": 6.0, "B.Cu": 6.0}            # ps/mm; inner layers 7.0
Z = {"F.Cu": 0.0, "In1.Cu": 0.17, "In2.Cu": 0.79, "In3.Cu": 1.17, "In4.Cu": 1.79, "B.Cu": 2.0}
TX = ["/RMII0_T1S_TXD0", "/RMII0_T1S_TXD1", "/RMII0_T1S_TX_EN"]
RX = ["/RMII0_T1S_RXD0", "/RMII0_T1S_RXD1", "/RMII0_T1S_CRS_DV", "/RMII0_T1S_RX_ER"]
STD = {pcbnew.BOARD.GetStandardLayerName(i): i for i in range(pcbnew.PCB_LAYER_ID_COUNT)}
R_SER = 33.0                                 # R503, R504
MD = ["/MDIO0_T1S_MDC", "/MDIO0_T1S_MDIO"]


def mm(v):
    return round(pcbnew.ToMM(v), 4)


def graph(b, net):
    """Nodes (x, y, layer) in mm; edges carry (length mm, delay ps, kind). Copper joins where it
    touches: a track end or a via on another track (split there), a track end inside a via's ring,
    nodes inside one pad; vias join their layers through the barrel."""
    g = defaultdict(list)
    ids = list(b.GetEnabledLayers().CuStack())
    names = [pcbnew.BOARD.GetStandardLayerName(l) for l in ids]
    segs, vias = [], []
    for t in b.GetTracks():
        if t.GetNetname() != net:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            vias.append(((mm(t.GetPosition().x), mm(t.GetPosition().y)), pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2,
                         [n for i, n in zip(ids, names) if t.IsOnLayer(i)]))
        else:
            ln = pcbnew.BOARD.GetStandardLayerName(t.GetLayer())
            segs.append((ln, (mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y)),
                         pcbnew.ToMM(t.GetWidth()) / 2))

    def edge(n, m, L, kind):
        g[n].append((m, L, L * PS.get(n[2], 7.0) if kind != "via" else L * 7.0, kind))
        g[m].append((n, L, L * PS.get(n[2], 7.0) if kind != "via" else L * 7.0, kind))

    # touch points: (layer, x, y, reach) of every track end and via centre
    pts = [(ln, q, w) for ln, a, c, w in segs for q in (a, c)]
    pts += [(ln, p, r) for p, r, ls in vias for ln in ls]
    for ln, a, c, w in segs:
        dx, dy = c[0] - a[0], c[1] - a[1]
        L2 = dx * dx + dy * dy
        L = L2 ** 0.5
        stops = {0.0: a, 1.0: c}
        joins = []
        for pl, q, reach in pts:
            if pl != ln:
                continue
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / L2))
            x, y = a[0] + t * dx, a[1] + t * dy
            d = ((q[0] - x) ** 2 + (q[1] - y) ** 2) ** 0.5
            if d <= w + reach + 1e-3:
                stops[round(t, 6)] = (round(x, 4), round(y, 4))
                joins.append(((round(x, 4), round(y, 4)), q, d))
        ts = sorted(stops)
        for t0, t1 in zip(ts, ts[1:]):
            edge(stops[t0] + (ln,), stops[t1] + (ln,), (t1 - t0) * L, ln)
        for x, q, d in joins:
            if x + (ln,) != q + (ln,):
                edge(x + (ln,), q + (ln,), d, "join")
    for p, r, ls in vias:
        for a, c in zip(ls, ls[1:]):
            edge(p + (a,), p + (c,), abs(Z[a] - Z[c]), "via")
    for f in b.GetFootprints():
        for pd in f.Pads():
            if pd.GetNetname() != net:
                continue
            inside = [n for n in list(g) if pd.IsOnLayer(STD[n[2]]) and
                      pd.HitTest(pcbnew.VECTOR2I(pcbnew.FromMM(n[0]), pcbnew.FromMM(n[1])), pcbnew.FromMM(0.01))]
            for i, n in enumerate(inside):
                for m in inside[i + 1:]:
                    edge(n, m, 0.0, "join")
    return g


def pad_nodes(g, pad, b):
    """Graph nodes inside the pad's copper on its layers."""
    out = []
    for n in g:
        if pad.IsOnLayer(STD[n[2]]) and \
                pad.HitTest(pcbnew.VECTOR2I(pcbnew.FromMM(n[0]), pcbnew.FromMM(n[1]))):
            out.append(n)
    return out


def path(b, net, pa, pb):
    g = graph(b, net)
    src, dst = pad_nodes(g, pa, b), set(pad_nodes(g, pb, b))
    best = {s: 0.0 for s in src}
    info = {s: (0.0, defaultdict(float), frozenset()) for s in src}
    q = [(0.0, s) for s in src]
    while q:
        d, n = heapq.heappop(q)
        if d > best.get(n, 1e18):
            continue
        if n in dst:
            L, per, nv = info[n]
            return {"mm": round(L, 2), "ps": round(d, 1), "vias": len(nv),
                    "layers": {k: round(v, 2) for k, v in per.items()}}
        L, per, nv = info[n]
        for m, l, ps, kind in g[n]:
            if d + ps < best.get(m, 1e18):
                best[m] = d + ps
                p2 = defaultdict(float, per); p2["via" if kind == "via" else kind] += l
                info[m] = (L + l, p2, nv | {m[:2]} if kind == "via" else nv)
                heapq.heappush(q, (d + ps, m))
    return None


def pad(b, ref, num):
    return [p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num][0]


def main():
    b = pcbnew.LoadBoard(sys.argv[1])
    u501 = b.FindFootprintByReference("U501")
    u401 = b.FindFootprintByReference("U401")
    res = {"nets": {}}
    for net in TX + RX + MD:
        a = [p for p in u501.Pads() if p.GetNetname() == net][0]
        c = [p for p in u401.Pads() if p.GetNetname() == net][0]
        res["nets"][net.split("T1S_")[-1]] = path(b, net, a, c)
    # clock: Y501 pin 3 -> R503 pin 1, R503 pin 2 -> U501 27; Y501 3 -> R504 1, R504 2 -> U401 U6
    osc = "/T1S/T1S_OSC_OUT"
    y3 = pad(b, "Y501", "3")
    phy = [path(b, osc, y3, pad(b, "R503", "1")), path(b, "/T1S/T1S_REFCLK", pad(b, "R503", "2"), pad(b, "U501", "27"))]
    mcu = [path(b, osc, y3, pad(b, "R504", "1")), path(b, "/RMII0_T1S_REF_CLK", pad(b, "R504", "2"), pad(b, "U401", "U6"))]
    def est(parts, pads):
        out = []
        for p_, (pa, pb) in zip(parts, pads):
            if p_:
                out.append(p_)
            else:
                a, c = pa.GetPosition(), pb.GetPosition()
                L = pcbnew.ToMM(abs(a.x - c.x) + abs(a.y - c.y))
                out.append({"mm": round(L, 2), "ps": round(L * 6.0, 1), "vias": 0, "layers": {"B.Cu": L}, "estimated": True})
        return out
    phy = est(phy, [(y3, pad(b, "R503", "1")), (pad(b, "R503", "2"), pad(b, "U501", "27"))])
    mcu = est(mcu, [(y3, pad(b, "R504", "1")), (pad(b, "R504", "2"), pad(b, "U401", "U6"))])
    res["clk_phy"] = {"mm": round(sum(p["mm"] for p in phy if p) + 0.9, 2), "ps": round(sum(p["ps"] for p in phy if p), 1), "parts": phy}
    res["clk_mcu"] = {"mm": round(sum(p["mm"] for p in mcu if p) + 0.9, 2), "ps": round(sum(p["ps"] for p in mcu if p), 1), "parts": mcu}
    def rc(branch, cin):
        c = cin
        for p_ in branch["parts"]:
            for k, v in p_["layers"].items():
                if k in ("F.Cu", "B.Cu"):
                    c += 0.12 * v
                elif k not in ("via", "join"):
                    c += 0.14 * v
        return 0.69 * R_SER * c / 1000           # ohm x pF = ps; ns
    flight = (res["clk_mcu"]["ps"] - res["clk_phy"]["ps"]) / 1000
    rc_phy = rc(res["clk_phy"], 3.0)
    dclk_hi = flight + rc(res["clk_mcu"], 8.0) - rc_phy
    dclk_lo = flight + rc(res["clk_mcu"], 4.0) - rc_phy
    res["clk_flight_ns"] = round(flight, 3)
    res["dclk_hi_ns"], res["dclk_lo_ns"] = round(dclk_hi, 3), round(dclk_lo, 3)
    ttx = max(res["nets"][n.split("T1S_")[-1]]["ps"] for n in TX) / 1000
    ttx_min = min(res["nets"][n.split("T1S_")[-1]]["ps"] for n in TX) / 1000
    trx = max(res["nets"][n.split("T1S_")[-1]]["ps"] for n in RX) / 1000
    trx_min = min(res["nets"][n.split("T1S_")[-1]]["ps"] for n in RX) / 1000
    res["slack_ns"] = {
        "tx_setup": round(20 - 15 - ttx - dclk_hi - 4, 3),
        "tx_hold": round(2 + ttx_min + dclk_lo - 1.5, 3),
        "rx_setup": round(20 - 12 - trx + dclk_lo - 4, 3),
        "rx_hold": round(3 + trx_min - dclk_hi - 2, 3),
    }
    res["clk_mismatch_mm"] = round(res["clk_mcu"]["mm"] - res["clk_phy"]["mm"], 2)
    for k, v in res["nets"].items():
        print(f"{k:8s} {v['mm']:6.1f} mm {v['ps']:6.0f} ps  vias {v['vias']}  {v['layers']}")
    print(f"clk to PHY {res['clk_phy']['mm']:.1f} mm {res['clk_phy']['ps']:.0f} ps; to MCU {res['clk_mcu']['mm']:.1f} mm {res['clk_mcu']['ps']:.0f} ps; "
          f"mismatch {res['clk_mismatch_mm']:+.1f} mm (Microchip: within 13); dclk flight {flight*1000:.0f} ps, with RC {dclk_lo*1000:.0f}..{dclk_hi*1000:.0f} ps")
    print("slack ns", res["slack_ns"])
    if "--json" in sys.argv:
        json.dump(res, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)


if __name__ == "__main__":
    main()
