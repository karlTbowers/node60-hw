#!/usr/bin/env python3
"""silk_new.py SILK.json OUT.json REF [REF ...] -- a place for the named references only (the new resistors and any
reference a new pad landed under), every other reference staying where it is and counting as taken. Uses the
bitmap and the candidate search of the fix run's silk_place.py (its definitions are run from its source, up to
its own placing loop); SILK.json from its silk_export.py. Needs numpy, scipy and PIL."""
import os, sys
H = os.path.dirname(os.path.abspath(__file__)); src = open(os.path.join(H, '..', '2026-11-13-kicad-happy-fixes', 'silk_place.py')).read()
refs = sys.argv[3:]; argv = sys.argv; sys.argv = argv[:2] + ['x']
exec(src[:src.index('out, fail = {}, []')].replace('float(sys.argv[3]) if len(sys.argv) > 3 else 6.0', '6.0'))
for f in D['fps']:      # the references that stay: their text boxes are taken
    if f['ref'] in refs or not f['visible'] or not f['on_silk']: continue
    tw, th = (f['tw'], f['th']) if int(round(f['tangle'])) % 180 == 0 else (f['th'], f['tw'])
    a = [int((f['tx'] - tw / 2 - 0.15 - X0) / PX), int((f['ty'] - th / 2 - 0.15 - Y0) / PX), int((f['tx'] + tw / 2 + 0.15 - X0) / PX) + 1, int((f['ty'] + th / 2 + 0.15 - Y0) / PX) + 1]
    occ[f['side']][max(a[1], 0):a[3], max(a[0], 0):a[2]] = True
out, fail = {}, []
for f in D['fps']:
    if f['ref'] not in refs: continue
    I = integral(occ[f['side']]); c = cands(f, I)
    if c is None or not len(c[0]): fail.append(f['ref']); continue
    i = int(np.argmin(c[0])); x, y, ang = float(c[1][i]), float(c[2][i]), int(c[3][i])
    out[f['ref']] = {'x': round(x, 3), 'y': round(y, 3), 'angle': ang, 'gap': round(float(c[4][i]), 2)}
    tw, th = (f['tw'], f['th']) if ang == 0 else (f['th'], f['tw'])
    a = [int((x - tw / 2 - 0.15 - X0) / PX), int((y - th / 2 - 0.15 - Y0) / PX), int((x + tw / 2 + 0.15 - X0) / PX) + 1, int((y + th / 2 + 0.15 - Y0) / PX) + 1]
    occ[f['side']][a[1]:a[3], a[0]:a[2]] = True
json.dump({'place': out, 'no_room': sorted(fail)}, open(argv[2], 'w'), indent=1)
print(len(out), 'placed', {k: v['gap'] for k, v in out.items()}, 'no room:', fail)
