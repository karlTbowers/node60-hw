#!/usr/bin/env python3
"""drc_pairs.py REPORT.json -- errors of a KiCad DRC report by type and net pair, and the unconnected items
that involve no test point."""
import json, sys, re, collections
d = json.load(open(sys.argv[1]))
pairs = collections.Counter(); where = {}
for v in d['violations']:
    if v['severity'] != 'error': continue
    nets = tuple(sorted(set(re.findall(r'\[([^\]]+)\]', ' '.join(i['description'] for i in v['items'])))))
    pairs[(v['type'], nets)] += 1; where.setdefault((v['type'], nets), v['items'][0]['pos'])
for k, n in sorted(pairs.items(), key=lambda x: -x[1]): print(n, k, where[k], )
tp = 0
for u in d.get('unconnected_items', []):
    s = ' | '.join(i['description'] for i in u['items'])
    if re.search(r'of TP\d+', s): tp += 1
    else: print('  open:', s[:140], u['items'][0]['pos'])
print('unconnected', len(d.get('unconnected_items', [])), 'of which at a test point', tp)
