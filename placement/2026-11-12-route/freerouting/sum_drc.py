import json, sys, re, collections, os
PL = {"GND","3V3_MAIN","1V5_CORE","VBAT_PROT","VBAT_FILT","VDDAU_AON","/VBAT_IN","/Power entry/VBAT_D","/Power entry/VBAT_Q2D"} | {f"/OUT{i}" for i in range(1,7)}
verbose = sys.argv[1] == "-v"
for f in sys.argv[1+verbose:]:
    d = json.load(open(f)); ty = collections.Counter(v['type'] for v in d['violations'] if v['severity']=='error')
    sig = collections.Counter(); tp = pl = 0
    for u in d.get('unconnected_items', []):
        s = ' | '.join(i['description'] for i in u['items'])
        nets = set(re.findall(r'\[([^\]]+)\]', s))
        if re.search(r'of TP\d+', s): tp += 1
        elif nets & PL: pl += 1
        else: sig[sorted(nets)[0]] += 1
    print(f"{os.path.basename(f):22s} {os.path.getmtime(f):.0f} errors {sum(ty.values()):4d} {dict(ty)} | unconnected {len(d.get('unconnected_items',[]))}: TP {tp}, plane {pl}, signal {sum(sig.values())} in {len(sig)} nets")
    if verbose:
        for n,c in sorted(sig.items()): print("   ", c, n)
