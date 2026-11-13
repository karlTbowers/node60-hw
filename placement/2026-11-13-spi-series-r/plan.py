#!/usr/bin/env python3
"""plan.py COPPER.json COURTYARDS.json OUT_SPEC.json [REF ...] -- finds a place for each SPI series resistor and the
copper that joins it, on the board's copper as exported (export_copper.py, export_courtyards.py). No part moves.

For each line (driver pad, receiver pad) the route is walked from the driver. A cut takes GAP mm of copper out of the
route at D mm from the driver; the 0402 goes on B.Cu at a free spot within REACH of the cut (pads and courtyard clear
of every other part and net); the driver's side of the route becomes the line's new stub net; mini_route.py (the
routing run's single-join router, plain mode) joins each loose end to its pad. The first cut that routes wins: the
resistor nearest its driver that the board has room for. Cuts stay on the driver's side of the line's first test
point where one is given (`before`), so the test point stays on the line as on the schematic.
Run with the Python that has shapely (KRT's venv). KiCad's DRC judges the result afterwards (build.sh)."""
import copy, heapq, json, math, os, subprocess, sys, collections
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely import prepared
HERE = os.path.dirname(os.path.abspath(__file__)); VPY = sys.executable
MINI = os.path.join(HERE, '..', '2026-11-12-route', 'mini_route.py')
PAD_DX, PAD_W, PAD_H, CY_L, CY_W = 0.455, 0.59, 0.60, 1.89, 0.99      # DropOut R_0402_1005Metric, read from R503
GAP = 0.9
# ref, line, stub net, driver, receiver, furthest cut (mm of copper from the driver: short of the line's first test
# point, so that stays on the line as on the schematic). Order as planned: each one sees the ones before it.
LINES = [
 ('R708', '/SPI5_SWITCH2_MISO', '/Outputs 3-4/SW_SDO', 'U701.14', 'U401.B13', 3.0),
 ('R608', '/SPI4_SWITCH1_MISO', '/Outputs 1-2/SW_SDO', 'U601.14', 'U401.C17', 2.3),               # TP603 at 5.8 mm
 ('R409', '/SPI4_SWITCH1_SCK', '/MCU and NVM/SPI4_SWITCH1_SCK_MCU', 'U401.D15', 'U601.16', 16.0),  # TP403 at 18.7
 ('R410', '/SPI4_SWITCH1_MOSI', '/MCU and NVM/SPI4_SWITCH1_MOSI_MCU', 'U401.C15', 'U601.13', 30.0),
 ('R411', '/SPI4_SWITCH1_CS_L', '/MCU and NVM/SPI4_SWITCH1_CS_L_MCU', 'U401.A14', 'U601.15', 30.0),
 ('R412', '/SPI5_SWITCH2_SCK', '/MCU and NVM/SPI5_SWITCH2_SCK_MCU', 'U401.A16', 'U701.16', 30.0),
 ('R413', '/SPI5_SWITCH2_MOSI', '/MCU and NVM/SPI5_SWITCH2_MOSI_MCU', 'U401.A15', 'U701.13', 16.5),  # TP414 at 17.7
 ('R415', '/SPI3_SWITCH3_SCK', '/MCU and NVM/SPI3_SWITCH3_SCK_MCU', 'U401.E14', 'U801.16', 17.2),   # TP417 at 17.6
 ('R416', '/SPI3_SWITCH3_MOSI', '/MCU and NVM/SPI3_SWITCH3_MOSI_MCU', 'U401.F14', 'U801.13', 15.4), # TP418 at 16.6
 ('R808', '/SPI3_SWITCH3_MISO', '/Outputs 5-6/SW_SDO', 'U801.14', 'U401.E15', 4.6),                # TP803 at 6.1
 ('R417', '/SPI3_SWITCH3_CS_L', '/MCU and NVM/SPI3_SWITCH3_CS_L_MCU', 'U401.G15', 'U801.15', 12.0), # TP420 at 14.3
 ('R418', '/MCU and NVM/SPI2_FLASH_SCK', '/MCU and NVM/SPI2_FLASH_SCK_MCU', 'U401.D2', 'U402.6', 17.4),  # in TP407's branch (18.6)
 ('R414', '/SPI5_SWITCH2_CS_L', '/MCU and NVM/SPI5_SWITCH2_CS_L_MCU', 'U401.G16', 'U701.15', 12.2)]  # TP416's branch leaves at 12.4; planned with REACH=4.5 PER_CUT=4
# this line runs 17 mm under U401 and its test point hangs on a branch that leaves it right after: the resistor goes into the branch
TP_BRANCH = {'R418': 'TP407.1'}
P = lambda o: Polygon(o['outer'], o['holes'])
T1S = lambda t: 'T1S_100R' in t.get('cls', '')

def graph(C, net):
    segs = [(i, t) for i, t in enumerate(C['tracks']) if t['net'] == net]; adj = collections.defaultdict(list)
    key = lambda p, l: (round(p[0], 3), round(p[1], 3), l)
    for i, t in segs:
        L = math.dist(t['a'], t['b']); a, b = key(t['a'], t['layer']), key(t['b'], t['layer'])
        adj[a].append((b, L, i)); adj[b].append((a, L, i))
    ks = list(adj)
    for v in C['vias']:
        if v['net'] == net:
            here = [k for k in ks if math.hypot(k[0] - v['x'], k[1] - v['y']) < 0.03]
            for k in here:
                for k2 in here:
                    if k != k2: adj[k].append((k2, 0, None))
    for i, k in enumerate(ks):
        for k2 in ks[i + 1:]:
            if k[2] == k2[2] and math.hypot(k[0] - k2[0], k[1] - k2[1]) < 0.06: adj[k].append((k2, 0, None)); adj[k2].append((k, 0, None))
    return adj
def pad(C, name):
    r, n = name.split('.'); return [p for p in C['pads'] if p['ref'] == r and p['num'] == n][0]
def node_at(adj, p):
    return min((k for k in adj if k[2] in p['layers']), key=lambda k: math.hypot(k[0] - p['x'], k[1] - p['y']))
def walk(C, net, drv, rcv):
    adj = graph(C, net); src, dst = node_at(adj, pad(C, drv)), node_at(adj, pad(C, rcv))
    dist = {src: 0}; prev = {}; h = [(0, src)]
    while h:
        d, k = heapq.heappop(h)
        if d > dist[k]: continue
        for k2, L, i in adj[k]:
            if d + L < dist.get(k2, 1e9): dist[k2] = d + L; prev[k2] = (k, i); heapq.heappush(h, (d + L, k2))
    path = []; k = dst
    while k != src: k0, i = prev[k]; path.append((k0, k, i)); k = k0
    path.reverse(); return [(a, b, i, dist[a]) for a, b, i in path if i is not None]

def remove(C, path, net, d, gap):
    """C with [d, d + gap] of copper taken out of `path`: the copy, the two loose ends, the deleted tracks and the shortened pieces"""
    C = dict(C, tracks=[dict(t) for t in C['tracks']], vias=[dict(v) for v in C['vias']], pads=list(C['pads']))
    ends = [None, None]; dele = []; add = []; kill = set()
    for a, b, i, d0 in path:
        t = C['tracks'][i]; L = math.dist(a[:2], b[:2])
        if d0 + L <= d or d0 >= d + gap or L == 0: continue
        at = lambda s: [round(a[0] + (b[0] - a[0]) * s / L, 4), round(a[1] + (b[1] - a[1]) * s / L, 4)]
        kill.add(i); dele.append({'seg': [*t['a'], *t['b']], 'layer': t['layer'], 'net': net})
        if d0 < d:
            e = at(d - d0); nt = dict(t, a=list(a[:2]), b=e); C['tracks'].append(nt); add.append(nt); ends[0] = e + [t['layer']]
        elif ends[0] is None: ends[0] = [a[0], a[1], t['layer']]
        if d0 + L > d + gap:
            e = at(d + gap - d0); nt = dict(t, a=e, b=list(b[:2])); C['tracks'].append(nt); add.append(nt); ends[1] = e + [t['layer']]
        else: ends[1] = [b[0], b[1], t['layer']]
    if None in ends: return None
    C['tracks'] = [t for i, t in enumerate(C['tracks']) if i not in kill]
    return C, ends, dele, add

def renet(C, net, stub, drv):
    """everything of the net still joined to the driver's pad goes to the stub net (in place)"""
    adj = graph(C, net); src = node_at(adj, pad(C, drv)); seen = {src}; st = [src]; ti = set()
    while st:
        k = st.pop()
        for k2, L, i in adj[k]:
            if i is not None: ti.add(i)
            if k2 not in seen: seen.add(k2); st.append(k2)
    for i in ti: C['tracks'][i]['net'] = stub
    vi = [j for j, v in enumerate(C['vias']) if v['net'] == net and any(math.hypot(k[0] - v['x'], k[1] - v['y']) < 0.03 for k in seen)]
    for j in vi: C['vias'][j] = dict(C['vias'][j], net=stub)
    dp = pad(C, drv); C['pads'][C['pads'].index(dp)] = dict(dp, net=stub)
    return len(ti), len(vi)

def cut(C, net, stub, drv, rcv, d, gap):
    """remove() on the route from driver to receiver, and the driver's side re-netted to the stub net"""
    r = remove(C, walk(C, net, drv, rcv), net, d, gap)
    if r is None: return None
    C, ends, dele, add = r
    nt, nv = renet(C, net, stub, drv)
    return C, ends, dele, add, nt, nv

def spots(C, CY, net, stub, mid, reach, ends):
    """free 0402 poses on B.Cu near `mid`, nearest first: (x, y, rot, swap). swap: pad 1 on the far side."""
    w = box(mid[0] - reach - 2, mid[1] - reach - 2, mid[0] + reach + 2, mid[1] + reach + 2)
    cu = []; t1 = []; own = {net: [], stub: []}
    for t in C['tracks']:
        if t['layer'] != 'B.Cu': continue
        g = LineString([t['a'], t['b']]).buffer(t['w'] / 2)
        if not g.intersects(w): continue
        (own[t['net']] if t['net'] in own else t1 if T1S(t) else cu).append(g)
    for v in C['vias']:
        g = Point(v['x'], v['y']).buffer(max(v['size'] / 2, v['drill'] / 2 + 0.05))
        if g.intersects(w): (own[v['net']] if v['net'] in own else t1 if T1S(v) else cu).append(g)
    for p in C['pads']:
        if 'B.Cu' in p['layers'] and abs(p['x'] - mid[0]) < reach + 8 and abs(p['y'] - mid[1]) < reach + 8:
            g = unary_union([P(o) for o in p['layers']['B.Cu']])
            if g.intersects(w): (own[p['net']] if p['net'] in own else t1 if T1S(p) else cu).append(g)
    for h in C['holes']:
        g = Point(h['x'], h['y']).buffer(h['d'] / 2 + 0.2)
        if g.intersects(w): cu.append(g)
    for z in C['zones']:      # another net's pour on B.Cu (not GND's, which retreats): leave it whole
        if z['layer'] == 'B.Cu' and z['net'] not in ('GND', net, stub):
            for o in z['fill']:
                g = P(o)
                if g.intersects(w): cu.append(g.buffer(-0.17))
    cy = [Polygon(o) for f in CY for o in f['B'] if abs(f['x'] - mid[0]) < 30 and abs(f['y'] - mid[1]) < 30]
    cy = unary_union([g for g in cy if g.intersects(w)]) if cy else Polygon()
    blk = unary_union([g.buffer(0.17) for g in cu] + [g.buffer(0.77) for g in t1]); bp = prepared.prep(blk); cyp = prepared.prep(cy)
    o_line = unary_union([g.buffer(0.17) for g in own[net]]) if own[net] else Polygon(); o_stub = unary_union([g.buffer(0.17) for g in own[stub]]) if own[stub] else Polygon()
    out = []; n = int(reach / 0.1)
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            x, y = round(mid[0] + i * 0.1, 2), round(mid[1] + j * 0.1, 2)
            if math.hypot(x - mid[0], y - mid[1]) > reach: continue
            for rot in (0, 90):
                ux, uy = (1, 0) if rot == 0 else (0, 1); pw, ph = (PAD_W, PAD_H) if rot == 0 else (PAD_H, PAD_W)
                pa = box(x - ux * PAD_DX - pw / 2, y - uy * PAD_DX - ph / 2, x - ux * PAD_DX + pw / 2, y - uy * PAD_DX + ph / 2)
                pb = box(x + ux * PAD_DX - pw / 2, y + uy * PAD_DX - ph / 2, x + ux * PAD_DX + pw / 2, y + uy * PAD_DX + ph / 2)
                c = box(x - (CY_L if rot == 0 else CY_W) / 2, y - (CY_W if rot == 0 else CY_L) / 2, x + (CY_L if rot == 0 else CY_W) / 2, y + (CY_W if rot == 0 else CY_L) / 2)
                if bp.intersects(pa) or bp.intersects(pb) or cyp.intersects(c): continue
                for swap in (0, 1):      # which pad takes the stub
                    ps, pl = (pb, pa) if swap else (pa, pb)
                    if ps.intersects(o_line) or pl.intersects(o_stub): continue
                    cs, cl = ps.centroid, pl.centroid
                    cost = math.hypot(cs.x - ends[0][0], cs.y - ends[0][1]) + math.hypot(cl.x - ends[1][0], cl.y - ends[1][1])
                    out.append((cost, x, y, rot, swap, [round(cs.x, 4), round(cs.y, 4)], [round(cl.x, 4), round(cl.y, 4)]))
    out.sort(); return out

def try_branch(C, CY, ref, net, stub, drv, rcv, tp, tmp, reach_extra=2.0, tries=40):
    """The line's first test point hangs on a branch that goes through a via to B.Cu and on to the pad. The line is
    detached where the branch leaves it, the branch's B.Cu run is taken out, and the 0402 goes between the branch's
    via and the test point: via -> pin 1, pin 2 -> test point, and the detached line -> pin 2. Best of `tries` spots."""
    pm, pt = walk(C, net, drv, rcv), walk(C, net, drv, tp); n = 0
    while pm[n][2] == pt[n][2]: n += 1
    C1, e0, dele, add = remove(C, pm, net, pm[n][3], GAP); island = e0[1]
    k = n                                   # the branch up to its first layer change stays; the rest goes
    while k < len(pt) and pt[k][0][2] == pt[n][0][2]: k += 1
    via = pt[k][0]; kill = {pt[j][2] for j in range(k, len(pt))}
    # indices in C1 differ from C's: match by geometry
    gone = [C['tracks'][i] for i in kill]; same = lambda t, g: t['layer'] == g['layer'] and t['a'] == g['a'] and t['b'] == g['b'] and t['net'] == g['net']
    C1['tracks'] = [t for t in C1['tracks'] if not any(same(t, g) for g in gone)]
    dele = dele + [{'seg': [*g['a'], *g['b']], 'layer': g['layer'], 'net': net} for g in gone]
    renet(C1, net, stub, drv); tpp = pad(C1, tp)
    start = [via[0], via[1], 'B.Cu']; goal = [tpp['x'], tpp['y'], 'B.Cu']
    mid = [(start[0] + goal[0]) / 2, (start[1] + goal[1]) / 2]; reach = math.dist(start[:2], goal[:2]) / 2 + reach_extra
    print(f'{ref}: in the branch to {tp} (leaves the line at {pm[n][3]:.1f} mm, via at {via[:2]}); the line is detached at {island}', flush=True)
    best = None; lastxy = []; tried = 0
    for cost, x, y, rot, swap, cs, cl in spots(C1, CY, net, stub, mid, reach, [start, goal]):
        if any(math.hypot(x - a, y - b) < 0.6 and rr == rot for a, b, rr in lastxy): continue
        lastxy.append((x, y, rot)); tried += 1
        C3 = dict(C1, pads=C1['pads'] + [rect_pad(ref, '1', stub, cs, rot), rect_pad(ref, '2', net, cl, rot)])
        L = ['B.Cu', 'F.Cu', 'In2.Cu']
        jobs = [{'net': stub, 'name': 'stub', 'from': start, 'to': cs + ['B.Cu'], 'layers': L, 'rip': False, 'margin': 3, 'via_cost': 25},
                {'net': net, 'name': 'tp', 'from': cl + ['B.Cu'], 'to': goal, 'layers': L, 'rip': False, 'margin': 3, 'via_cost': 25},
                {'net': net, 'name': 'island', 'from': island, 'to': cl + ['B.Cu'], 'layers': L + ([island[2]] if island[2] not in L else []), 'rip': False, 'margin': float(os.environ.get('IMARGIN', 3.5)), 'via_cost': 25}]
        json.dump(C3, open(tmp + '.copper.json', 'w')); json.dump(jobs, open(tmp + '.jobs.json', 'w'))
        o = subprocess.run([VPY, MINI, tmp + '.copper.json', tmp + '.jobs.json', tmp + '.out.json'], capture_output=True, text=True)
        res = json.load(open(tmp + '.out.json')) if o.returncode == 0 else {'failed': ['crash']}
        if os.environ.get('DEBUG'): print('  ', x, y, rot, swap, res['failed'], flush=True)
        if not res['failed']:
            mm = sum(math.dist(a, b) for t in res['tracks'] for a, b in zip(t['pts'], t['pts'][1:])); score = mm + 2 * len(res['vias'])
            if best is None or score < best[0]:
                C4 = dict(C3, tracks=list(C3['tracks']), vias=list(C3['vias']))
                for t in res['tracks']:
                    for a, b in zip(t['pts'], t['pts'][1:]): C4['tracks'].append({'layer': t['layer'], 'a': a, 'b': b, 'w': t['w'], 'net': t['net'], 'cls': 'Default'})
                for v in res['vias']: C4['vias'].append({'x': v['x'], 'y': v['y'], 'size': v['d'], 'drill': v['drill'], 'net': v['net'], 'cls': 'Default'})
                best = (score, C4, {'ref': ref, 'x': x, 'y': y, 'rot': rot, 'swap': swap, 'line': net, 'stub': stub, 'driver': drv, 'cut_at': round(pm[n][3], 2),
                                    'joins_mm': round(mm, 2), 'delete': dele, 'pieces': add, 'tracks': res['tracks'], 'vias': res['vias']})
        if tried >= tries: break
    if best is None: print(f'{ref}: no place in the branch', flush=True); return C, None
    s = best[2]; print(f"{ref}: 0402 at ({s['x']}, {s['y']}) rot {s['rot']}{' swapped' if s['swap'] else ''}, joins {s['joins_mm']} mm, {len(s['vias'])} via(s)", flush=True)
    return best[1], s

def rect_pad(ref, num, net, c, rot):
    w, h = (PAD_W, PAD_H) if rot == 0 else (PAD_H, PAD_W)
    return {'ref': ref, 'num': num, 'net': net, 'cls': 'Default', 'x': c[0], 'y': c[1],
            'layers': {'B.Cu': [{'outer': [[c[0] - w / 2, c[1] - h / 2], [c[0] + w / 2, c[1] - h / 2], [c[0] + w / 2, c[1] + h / 2], [c[0] - w / 2, c[1] + h / 2]], 'holes': []}]}}

def try_line(C, CY, ref, net, stub, drv, rcv, dmax, tmp, reach=float(os.environ.get('REACH', 2.5)), per_cut=int(os.environ.get('PER_CUT', 2)), step=0.3, dmin=float(os.environ.get('DMIN', 0.5)), tp=None):
    """every cut up to dmax, two spots each; the best by: copper from the driver to the cut + the joins' length + 2 mm per via"""
    d = dmin; best = None; pre = ([], []); island = None; C_in = C
    if tp:      # the resistor goes into the branch to test point `tp`: the line itself is detached where the branch leaves it
        pm, pt = walk(C, net, drv, rcv), walk(C, net, drv, tp); n = 0
        while pm[n][2] == pt[n][2]: n += 1
        C, e0, d0_, a0_ = remove(C, pm, net, pm[n][3], GAP); pre = (d0_, a0_); island = e0[1]; rcv = tp
        d = pm[n][3] + 0.2; dmax = pt[-1][3] + math.dist(pt[-1][0][:2], pt[-1][1][:2]) - GAP - 0.8
        print(f'{ref}: in the branch to {tp}, which leaves the line at {pm[n][3]:.1f} mm; the line is detached at {island}', flush=True)
    while d <= dmax and (best is None or d < best[0]):
        r = cut(C, net, stub, drv, rcv, d, GAP)
        if r:
            C2, ends, dele, add, nt, nv = r; dele = pre[0] + dele; add = pre[1] + add; mid = [(ends[0][0] + ends[1][0]) / 2, (ends[0][1] + ends[1][1]) / 2]
            sp = spots(C2, CY, net, stub, mid, reach, ends); tried = 0; lastxy = []
            for cost, x, y, rot, swap, cs, cl in sp:
                if any(math.hypot(x - a, y - b) < 0.45 and rr == rot for a, b, rr in lastxy): continue      # not the same spot again
                lastxy.append((x, y, rot)); tried += 1
                C3 = dict(C2, pads=C2['pads'] + [rect_pad(ref, '2' if swap else '1', stub, cs, rot), rect_pad(ref, '1' if swap else '2', net, cl, rot)])
                jobs = [{'net': stub, 'name': 'stub', 'from': ends[0], 'to': cs + ['B.Cu'], 'layers': ['B.Cu', 'F.Cu', 'In2.Cu'], 'rip': False, 'margin': float(os.environ.get('REACH', 2.5)), 'via_cost': 25},
                        {'net': net, 'name': 'line', 'from': cl + ['B.Cu'], 'to': ends[1], 'layers': ['B.Cu', 'F.Cu', 'In2.Cu'], 'rip': False, 'margin': float(os.environ.get('REACH', 2.5)), 'via_cost': 25}]
                if island: jobs.append({'net': net, 'name': 'island', 'from': island, 'to': cl + ['B.Cu'], 'layers': ['B.Cu', 'F.Cu', 'In2.Cu'], 'rip': False, 'margin': 3.0, 'via_cost': 25})
                for jb in jobs:      # an end on a layer the router is not given: add it
                    for e in (jb['from'], jb['to']):
                        if e[2] not in jb['layers']: jb['layers'].append(e[2])
                json.dump(C3, open(tmp + '.copper.json', 'w')); json.dump(jobs, open(tmp + '.jobs.json', 'w'))
                o = subprocess.run([VPY, MINI, tmp + '.copper.json', tmp + '.jobs.json', tmp + '.out.json'], capture_output=True, text=True)
                res = json.load(open(tmp + '.out.json')) if o.returncode == 0 else {'failed': ['crash ' + o.stderr[-200:]]}
                if not res['failed']:
                    mm = sum(math.dist(a, b) for t in res['tracks'] for a, b in zip(t['pts'], t['pts'][1:]))
                    score = d + mm + 2 * len(res['vias'])
                    if best is None or score < best[0]:
                        C4 = dict(C3, tracks=list(C3['tracks']), vias=list(C3['vias']))
                        for t in res['tracks']:
                            for a, b in zip(t['pts'], t['pts'][1:]): C4['tracks'].append({'layer': t['layer'], 'a': a, 'b': b, 'w': t['w'], 'net': t['net'], 'cls': 'Default'})
                        for v in res['vias']: C4['vias'].append({'x': v['x'], 'y': v['y'], 'size': v['d'], 'drill': v['drill'], 'net': v['net'], 'cls': 'Default'})
                        best = (score, C4, {'ref': ref, 'x': x, 'y': y, 'rot': rot, 'swap': swap, 'line': net, 'stub': stub, 'driver': drv, 'cut_at': round(d, 2),
                                            'joins_mm': round(mm, 2), 'delete': dele, 'pieces': add, 'tracks': res['tracks'], 'vias': res['vias']})
                if tried >= per_cut: break
        d += step
    if best is None: print(f'{ref}: no place within {dmax:.1f} mm', flush=True); return C_in, None
    s = best[2]; print(f"{ref}: cut at {s['cut_at']} mm, 0402 at ({s['x']}, {s['y']}) rot {s['rot']}{' swapped' if s['swap'] else ''}, joins {s['joins_mm']} mm, {len(s['vias'])} via(s)", flush=True)
    return best[1], s

if __name__ == '__main__':
    C = json.load(open(sys.argv[1])); CY = json.load(open(sys.argv[2])); out = sys.argv[3]; only = sys.argv[4:]
    spec = json.load(open(out)) if os.path.exists(out) and only else []
    done = {s['ref'] for s in spec}
    def court(s): w, h = (CY_L, CY_W) if s['rot'] == 0 else (CY_W, CY_L); return {'x': s['x'], 'y': s['y'], 'B': [[[s['x'] - w / 2, s['y'] - h / 2], [s['x'] + w / 2, s['y'] - h / 2], [s['x'] + w / 2, s['y'] + h / 2], [s['x'] - w / 2, s['y'] + h / 2]]], 'F': []}
    spec = []
    for p in os.environ.get('HAVE', '').split():      # plans already made on this copper: their courtyards count
        CY += [court(s) for s in json.load(open(p))]
    for ref, net, stub, drv, rcv, dmax in LINES:
        if only and ref not in only: continue
        dmax = float(os.environ.get('DMAX', dmax))
        if ref in TP_BRANCH and 'NO_TP' not in os.environ: C, s = try_branch(C, CY, ref, net, stub, drv, rcv, TP_BRANCH[ref], os.path.join(HERE, 'work', 'trial'))
        else: C, s = try_line(C, CY, ref, net, stub, drv, rcv, dmax, os.path.join(HERE, 'work', 'trial'))
        if s: spec.append(s); CY.append(court(s))
    json.dump(spec, open(out, 'w'), indent=1); json.dump(C, open(os.path.join(HERE, 'work', 'planned.copper.json'), 'w'))
