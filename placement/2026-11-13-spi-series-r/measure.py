#!/usr/bin/env python3
"""measure.py BOARD -- each SPI series resistor: where it stands, the copper on its stub net (driver's pad to pin 1:
length, layers, vias) and on the line beyond it (all copper of the line net, test-point branches included)."""
import sys, collections, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); M = pcbnew.ToMM
def net_cu(n):
    L = collections.Counter(); v = 0
    for t in b.GetTracks():
        if t.GetNetname() == n:
            if t.Type() == pcbnew.PCB_VIA_T: v += 1
            else: L[b.GetLayerName(t.GetLayer()).split('.PWR')[0].split('.GND')[0]] += M(t.GetLength())
    return sum(L.values()), v, ' '.join('%s %.1f' % kv for kv in sorted(L.items()))
print('| Ref | Stub net (driver) | Line | At (mm) | Stub copper | Stub vias | Line copper | Line vias |\n|---|---|---|---|---:|---:|---:|---:|')
for f in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
    r = f.GetReference()
    if r in ('R409 R410 R411 R412 R413 R414 R415 R416 R417 R418 R608 R708 R808').split():
        p = {q.GetNumber(): q.GetNetname() for q in f.Pads()}; s = net_cu(p['1']); l = net_cu(p['2'])
        drv = [g.GetReference() + '.' + q.GetNumber() for g in b.GetFootprints() for q in g.Pads() if q.GetNetname() == p['1'] and g.GetReference() != r]
        print('| %s | `%s` (%s) | `%s` | %.2f, %.2f, %.0f° | %.1f mm (%s) | %d | %.1f mm | %d |' % (r, p['1'].split('/')[-1], ', '.join(drv), p['2'].split('/')[-1], M(f.GetPosition().x), M(f.GetPosition().y), f.GetOrientationDegrees() % 360, s[0], s[2], s[1], l[0], l[1]))
