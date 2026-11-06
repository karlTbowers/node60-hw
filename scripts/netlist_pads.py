#!/usr/bin/env python3
"""Pad-to-net map from a KiCad netlist (kicad-cli sch export netlist --format kicadsexpr).

    python3 scripts/netlist_pads.py NETLIST.net [--json OUT.json] [--diff OTHER.net] [--grep REGEX]

Prints or writes {"REF.PIN": "net name"}. --diff lists every pad whose net differs between the two
netlists (a schematic edit's effect on the board, before the board is touched); --grep limits the
listing to nets matching REGEX.
"""
import json
import re
import sys


def parse(path):
    s = open(path).read()
    i = s.find("(nets")
    out = {}
    for blk in re.split(r"\(net\s*\(code", s[i:])[1:]:
        name = re.search(r'\(name "((?:[^"\\]|\\.)*)"\)', blk).group(1)
        for ref, pin in re.findall(r'\(node\s*\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', blk):
            out[f"{ref}.{pin}"] = name
    return out


def main():
    a = sys.argv[1:]
    m = parse(a[0])
    if "--diff" in a:
        o = parse(a[a.index("--diff") + 1])
        rx = re.compile(a[a.index("--grep") + 1]) if "--grep" in a else None
        for k in sorted(set(m) | set(o), key=lambda k: (re.sub(r"\d+$", "", k.split(".")[0]), k)):
            if m.get(k) != o.get(k) and (not rx or rx.search(m.get(k, "") + " " + o.get(k, ""))):
                print(f"{k:12s} {o.get(k)!s:28s} -> {m.get(k)}")
        return
    if "--json" in a:
        json.dump(m, open(a[a.index("--json") + 1], "w"), indent=1, sort_keys=True)
        print(f"{len(m)} pads")
    else:
        for k in sorted(m):
            print(k, m[k])


if __name__ == "__main__":
    main()
