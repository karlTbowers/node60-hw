#!/usr/bin/env python3
"""apply_plan.py IN.kicad_pcb PLAN.json NETLIST.net OUT.kicad_pcb -- puts plan.py's resistors on the board (KiCad's Python).

For each entry: the footprint the netlist names, on B.Cu at the planned pose with pin 1 on the driver's side, linked
to its symbol and netted from the netlist; the planned pieces of the old route deleted and the shortened ones added;
the driver's pad and the copper still joined to it moved to the stub net; the joins' tracks and vias added. Every
other pad whose net the netlist changes is re-netted too. New copper is locked where the copper it replaces was."""
import json, math, os, re, sys
import pcbnew
F, M = pcbnew.FromMM, pcbnew.ToMM
src, plan_p, net_p, out = sys.argv[1:5]
ROOT = os.path.dirname(os.path.abspath(__file__)) + '/../..'
PAD_DX = 0.455

def netlist(path):
    s = open(path).read(); comps = {}; pins = {}
    for blk in s.split('\n\t\t(comp\n')[1:]:
        ref = re.search(r'\(ref "([^"]+)"\)', blk).group(1); fp = re.search(r'\(footprint "([^"]*)"\)', blk)
        st = re.findall(r'\(tstamps "([^"]+)"\)', blk)
        comps[ref] = {'footprint': fp.group(1) if fp else '', 'value': re.search(r'\(value "([^"]*)"\)', blk).group(1), 'path': st[0] + st[1] if len(st) >= 2 else None}
    for blk in re.split(r'\(net\s*\(code', s[s.find('(nets'):])[1:]:
        name = re.search(r'\(name "((?:[^"\\]|\\.)*)"\)', blk).group(1)
        for r, p in re.findall(r'\(node\s*\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', blk): pins[(r, p)] = name
    return comps, pins

comps, pins = netlist(net_p); plan = json.load(open(plan_p))
table = {n: u.replace('${KIPRJMOD}', ROOT) for n, u in re.findall(r'\(name "([^"]+)"\)\(type "[^"]+"\)\(uri "([^"]+)"\)', open(ROOT + '/fp-lib-table').read())}
loaded = {}
for e in plan:      # library footprints load before the board opens (pcbnew's wrappers go bad the other way round)
    lib, name = comps[e['ref']]['footprint'].split(':', 1); loaded[e['ref']] = pcbnew.FootprintLoad(table[lib], name); loaded[e['ref']].SetFPID(pcbnew.LIB_ID(lib, name))
b = pcbnew.LoadBoard(src)
lname = lambda l: b.GetLayerName(l).split('.PWR')[0].split('.GND')[0]
lid = {lname(l): l for l in b.GetEnabledLayers().Seq()}
def net(name):
    n = b.FindNet(name)
    if n is None: n = pcbnew.NETINFO_ITEM(b, name); b.Add(n)
    return n
close = lambda p, q, tol=0.003: abs(p[0] - q[0]) < tol and abs(p[1] - q[1]) < tol
xy = lambda v: (M(v.x), M(v.y))

for f in b.GetFootprints():      # pads the schematic moved to another net (the drivers' pads)
    for p in f.Pads():
        want = pins.get((f.GetReference(), p.GetNumber()))
        if want and p.GetNetname() != want: print(f'{f.GetReference()}.{p.GetNumber()}: {p.GetNetname()} -> {want}'); p.SetNet(net(want))

for e in plan:
    ref = e['ref']; fp = loaded[ref]; fp.SetReference(ref); fp.SetValue(comps[ref]['value']); fp.SetPath(pcbnew.KIID_PATH(comps[ref]['path'])); b.Add(fp)
    fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT); fp.SetPosition(pcbnew.VECTOR2I(F(e['x']), F(e['y'])))
    ux, uy = (1, 0) if e['rot'] == 0 else (0, 1); sgn = 1 if e['swap'] else -1
    want1 = (e['x'] + sgn * ux * PAD_DX, e['y'] + sgn * uy * PAD_DX)      # pin 1 (the stub's) on the driver's side
    for rot in (e['rot'], e['rot'] + 180):
        fp.SetOrientationDegrees(rot); p1 = [p for p in fp.Pads() if p.GetNumber() == '1'][0]
        if close(xy(p1.GetPosition()), want1, 0.01): break
    else: raise SystemExit(ref + ': pin 1 does not land where planned')
    for p in fp.Pads(): p.SetNet(net(pins[(ref, p.GetNumber())]))
    assert pins[(ref, '1')] == e['stub'] and pins[(ref, '2')] == e['line'], (ref, pins[(ref, '1')], pins[(ref, '2')])
    locked = False
    for d in e['delete']:
        hit = [t for t in b.GetTracks() if t.Type() != pcbnew.PCB_VIA_T and lname(t.GetLayer()) == d['layer'] and t.GetNetname() == d['net'] and
               ((close(xy(t.GetStart()), d['seg'][:2]) and close(xy(t.GetEnd()), d['seg'][2:])) or (close(xy(t.GetEnd()), d['seg'][:2]) and close(xy(t.GetStart()), d['seg'][2:])))]
        assert len(hit) == 1, (ref, d, len(hit))
        locked = locked or hit[0].IsLocked(); width = hit[0].GetWidth(); b.Remove(hit[0])
    def track(n, layer, w, a, c):
        if close(a, c, 0.0005): return
        t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(F(a[0]), F(a[1]))); t.SetEnd(pcbnew.VECTOR2I(F(c[0]), F(c[1])))
        t.SetLayer(lid[layer]); t.SetWidth(F(w)); t.SetNet(net(n)); t.SetLocked(locked); b.Add(t)
    for p in e['pieces']: track(e['line'], p['layer'], p['w'], p['a'], p['b'])      # re-netted with the rest of the driver's side below
    # the driver's side: the line's copper still joined to the driver's pad goes to the stub net
    r, n = e['driver'].split('.'); dp = [p for p in b.FindFootprintByReference(r).Pads() if p.GetNumber() == n][0]
    front = [(xy(dp.GetPosition()), None, 0.2)]; nt = nv = 0
    items = [t for t in b.GetTracks() if t.GetNetname() == e['line']]; used = set()
    while front:
        pt, layer, tol = front.pop()
        for i, t in enumerate(items):
            if i in used: continue
            if t.Type() == pcbnew.PCB_VIA_T:
                if close(xy(t.GetPosition()), pt, 0.03): used.add(i); t.SetNet(net(e['stub'])); nv += 1; front.append((xy(t.GetPosition()), None, 0.06))
            else:
                for a, c in ((t.GetStart(), t.GetEnd()), (t.GetEnd(), t.GetStart())):
                    if close(xy(a), pt, tol) and (layer is None or t.GetLayer() == layer):
                        used.add(i); t.SetNet(net(e['stub'])); nt += 1; front.append((xy(c), t.GetLayer(), 0.06)); break
    for t in e['tracks']:
        for a, c in zip(t['pts'], t['pts'][1:]): track(t['net'], t['layer'], t['w'], a, c)
    for v in e['vias']:
        via = pcbnew.PCB_VIA(b); via.SetPosition(pcbnew.VECTOR2I(F(v['x']), F(v['y']))); via.SetWidth(pcbnew.F_Cu, F(v['d'])); via.SetDrill(F(v['drill']))
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); via.SetNet(net(v['net'])); via.SetLocked(locked); b.Add(via)
    print(f"{ref}: at ({e['x']}, {e['y']}) rot {fp.GetOrientationDegrees():.0f}; stub {e['stub']}: {nt} tracks, {nv} vias re-netted; {len(e['tracks'])} join tracks, {len(e['vias'])} vias")
b.Save(out)
