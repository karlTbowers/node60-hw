#!/usr/bin/env python3
"""BGA escape budget, read-only (pcb-placement skill). Run with KiCad's Python (pcbnew).

Counts, for one ball-grid part on a placed board, what its escape needs and what the
board gives it: pitch, pad, ball classes per ring, tracks per channel, whether a via fits
between four balls, the signal layers the escape needs against the layers available,
and whether anything over the ball field takes vias or a layer away. That last check is
the one Node60 needed: the annealer put U401 under a busbar, where `node60.kicad_dru`
allows no other-net via, so its balls had no through via and one routing layer; the
first fast route left 9 nets open there.

    $KPY escape_budget.py BOARD.kicad_pcb --ref U401 --track 0.1 --space 0.1 --via 0.45 \
        --plane-nets 'GND,VBAT_PROT' --signal-layers F.Cu,In2.Cu,In3.Cu,B.Cu [--json OUT]

`--rules` defaults to the board's sibling `.kicad_dru`. Exit 1 when the escape needs
more layers than it has, or when a rule or keep-out area covers balls; 0 otherwise.
"""
import argparse
import collections
import fnmatch
import json
import math
import os
import re
import sys

import pcbnew


def mm(v):
    return pcbnew.ToMM(v)


def blocking_areas(board, rules_text, blocks=("via", "track")):
    """Areas over which another net's via or track is not allowed: name -> (zone, why, exempt nets).

    `blocks` names what the caller asks about: an area is returned only when it forbids one of
    them, so a via question (`blocks=("via",)`) never sees an area that forbids only tracks (Node60's
    busbar rules since decision D01). A rule's exempt nets are the ones its condition names with
    `A.NetName != '...'`."""
    out = {}
    for z in board.Zones():
        if not z.GetIsRuleArea():
            continue
        name = z.GetZoneName()
        layers = ",".join(board.GetLayerName(l) for l in z.GetLayerSet().Seq())
        if z.GetDoNotAllowVias() and "via" in blocks:
            out[name] = (z, f"native keep-out: no vias ({layers})", set())
        elif z.GetDoNotAllowTracks() and "track" in blocks:
            out[name] = (z, f"native keep-out: no tracks ({layers})", set())
    text = "\n".join(l for l in rules_text.splitlines() if not l.lstrip().startswith("#"))
    starts = [m.start() for m in re.finditer(r"\(rule\b", text)] + [len(text)]
    for rule in (text[s:e] for s, e in zip(starts, starts[1:])):
        for name in re.findall(r"intersectsArea\('([^']+)'\)", rule):
            dis = re.search(r"\(constraint disallow ([^)]*)\)", rule)
            if not dis:
                continue
            items = dis.group(1).split()
            lay = re.search(r'\(layer "([^"]+)"\)', rule)
            zone = next((z for z in board.Zones() if z.GetIsRuleArea() and z.GetZoneName() == name), None)
            if zone is not None and any(k in items for k in blocks):
                title = re.search(r'\(rule\s+"([^"]+)"', rule)
                what = "no other-net via" if "via" in items else "no other-net track"
                where = f" on {lay.group(1)}" if lay else ""
                out[name] = (zone, f"rule '{title.group(1) if title else name}': {what}{where}"
                             + (" (a through via crosses every layer)" if "via" in items else ""),
                             {n.lstrip("/") for n in re.findall(r"A\.NetName\s*!=\s*'([^']+)'", rule)})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("--ref", required=True)
    ap.add_argument("--track", type=float, required=True, help="escape track width, mm")
    ap.add_argument("--space", type=float, required=True, help="escape clearance, mm")
    ap.add_argument("--via", type=float, required=True, help="escape via pad diameter, mm")
    ap.add_argument("--plane-nets", default="GND", help="comma-separated globs of nets that go to a plane")
    ap.add_argument("--signal-layers", help="comma-separated layers the escape may use (default: all copper)")
    ap.add_argument("--rules", help="the board's .kicad_dru (default: sibling)")
    ap.add_argument("--json")
    a = ap.parse_args()

    board = pcbnew.LoadBoard(a.board)
    fp = board.FindFootprintByReference(a.ref)
    if fp is None:
        print(f"ERROR: {a.ref} not on the board", file=sys.stderr)
        return 2
    rules_path = a.rules or os.path.splitext(a.board)[0] + ".kicad_dru"
    rules_text = open(rules_path).read() if os.path.exists(rules_path) else ""
    planes = [g.strip() for g in a.plane_nets.split(",") if g.strip()]

    pads = list(fp.Pads())
    rel = [(mm(p.GetFPRelativePosition().x), mm(p.GetFPRelativePosition().y)) for p in pads]
    d = min(math.hypot(x1 - x2, y1 - y2) for i, (x1, y1) in enumerate(rel) for (x2, y2) in rel[i + 1:])
    pitch = round(d, 3)
    pad_d = round(min(mm(p.GetSizeX()) for p in pads), 3)
    xs = sorted({round(x / pitch) for x, _ in rel})
    ys = sorted({round(y / pitch) for _, y in rel})
    cols, rows = xs[-1] - xs[0] + 1, ys[-1] - ys[0] + 1

    rings = collections.defaultdict(collections.Counter)
    ball_ring = {}
    for p, (x, y) in zip(pads, rel):
        i, j = round(x / pitch) - xs[0], round(y / pitch) - ys[0]
        ring = min(i, j, cols - 1 - i, rows - 1 - j) + 1
        net = p.GetNetname()
        if not net or net.startswith("unconnected-"):
            cls = "nc"
        elif any(fnmatch.fnmatchcase(net, g) or fnmatch.fnmatchcase(net.lstrip("/"), g) for g in planes):
            cls = "plane"
        else:
            cls = "signal"
        rings[ring][cls] += 1
        ball_ring[p.GetNumber()] = (ring, cls, p)

    gap = pitch - pad_d
    per_channel = max(0, math.floor((gap - a.space) / (a.track + a.space)))
    diag = pitch * math.sqrt(2) - pad_d
    via_fits = a.via + 2 * a.space <= diag
    deepest = max((r for r, c in rings.items() if c["signal"]), default=0)
    rings_per_layer = per_channel + 1
    need = math.ceil(deepest / rings_per_layer) if deepest else 0

    all_layers = [board.GetStandardLayerName(l) for l in board.GetEnabledLayers().CuStack()]
    sig = a.signal_layers.split(",") if a.signal_layers else all_layers

    covered = {}
    for name, (zone, why, exempt) in blocking_areas(board, rules_text, blocks=("via",)).items():
        hit = [n for n, (_, cls, p) in ball_ring.items()
               if zone.Outline().Contains(p.GetPosition()) and cls != "nc"
               and p.GetNetname().lstrip("/") not in exempt]
        if hit:
            covered[name] = {"why": why, "balls": len(hit), "of": len(pads)}

    report = {
        "ref": a.ref, "side": fp.GetLayerName(), "pitch_mm": pitch, "pad_mm": pad_d,
        "grid": f"{cols} x {rows}", "balls": len(pads),
        "rings": {r: dict(c) for r, c in sorted(rings.items())},
        "deepest_signal_ring": deepest,
        "tracks_per_channel": per_channel, "via_between_balls": via_fits,
        "rings_per_layer": rings_per_layer, "signal_layers_needed": need,
        "signal_layers_available": sig, "covered_by": covered,
    }
    print(f"{a.ref} on {fp.GetLayerName()}: {len(pads)} balls, {cols} x {rows} grid, pitch {pitch} mm, pad {pad_d} mm")
    print("ring  signal  plane  nc")
    for r, c in sorted(rings.items()):
        print(f"{r:4}  {c['signal']:6}  {c['plane']:5}  {c['nc']:3}")
    print(f"channel gap {gap:.3f} mm -> {per_channel} track(s) of {a.track} at {a.space} space between balls")
    print(f"diagonal gap {diag:.3f} mm -> a {a.via} mm via between four balls: {'fits' if via_fits else 'does NOT fit'}")
    print(f"deepest signal ring {deepest}, {rings_per_layer} ring(s) per layer -> {need} signal layer(s) needed;"
          f" {len(sig)} available ({', '.join(sig)})")
    fail = need > len(sig)
    if fail:
        print("ERROR: the escape needs more signal layers than the layer plan gives it")
    if not via_fits and deepest > rings_per_layer:
        print("WARN: no via between balls: inner rings need via-in-pad or a finer via (a decision)")
    for name, c in covered.items():
        print(f"ERROR: {name} covers {c['balls']} of {c['of']} balls: {c['why']}")
        fail = True
    if a.json:
        json.dump(report, open(a.json, "w"), indent=2)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
