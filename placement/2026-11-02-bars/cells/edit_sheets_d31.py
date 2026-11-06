#!/usr/bin/env python3
"""The two schematic edits D31 lands (user: "Land both", 2026-11-06). Run from the repo root; idempotent.

1. sheets/output-switch.kicad_sch (placed three times): the hierarchical labels OUT_A (by C605, on the
   first channel's pins 6-8) and OUT_B (by C606, on pins 9-11) swap texts. Turned 180 degrees, each switch's
   first channel sits on the east, at the connector that carries OUT_B; the test points' own OUT_A/OUT_B
   labels stay, so each test point stays on its output.
2. sheets/t1s.kicad_sch: FL501 is mirrored about its horizontal axis (its wires meet the other winding:
   PHY_P on pin 2, CMC_P on pin 3); on K501 the T1S_P and T1S_N labels on the COM1/COM2 wires swap, and the
   pole labels swap with them (P_DROP/N_DROP, P_END/N_END), so P is on pole 2 (pins 5-7) with R518/R519,
   N on pole 1 with R516/R517. K501's coil pins (1 S+, 8 R+) are untouched: the relay latches by polarity.
"""
import re

def swap_labels(path, kind, a, b):
    """swap the texts of label (kind, name, x, y) a and b; a and b are (name, x, y)"""
    s = open(path).read()
    def find(name, x, y):
        m = re.search(r'\(' + kind + r' "' + re.escape(name) + r'"(\s*(?:\(shape \w+\)\s*)?\(at ' + re.escape(x) + " " + re.escape(y) + r' )', s)
        return m
    ma, mb = find(*a), find(*b)
    if not ma and find(b[0], a[1], a[2]) and find(a[0], b[1], b[2]):
        print(f"{path}: {a[0]} / {b[0]} already swapped")
        return
    assert ma and mb, (a, b)
    tok = "@@SWAP@@"
    s = s[:ma.start()] + f'({kind} "{tok}"' + ma.group(1) + s[ma.end():]
    mb = find(*b)
    s = s[:mb.start()] + f'({kind} "{a[0]}"' + mb.group(1) + s[mb.end():]
    s = s.replace(f'({kind} "{tok}"', f'({kind} "{b[0]}"', 1)
    open(path, "w").write(s)
    print(f"{path}: {a[0]} at ({a[1]}, {a[2]}) <-> {b[0]} at ({b[1]}, {b[2]})")


def mirror_symbol(path, ref, axis):
    s = open(path).read()
    starts = [m.start() for m in re.finditer(r'\n\t\(symbol\n', s)]
    for i, st in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(s)
        blk = s[st:end]
        if re.search(r'\(reference "' + ref + '"', blk):
            if "(mirror " in blk.split("(property")[0]:
                print(f"{path}: {ref} already mirrored")
                return
            new = re.sub(r'(\n\t\t\(at [-\d.]+ [-\d.]+ [-\d.]+\))', r'\1\n\t\t(mirror ' + axis + ')', blk, count=1)
            s = s[:st] + new + s[end:]
            open(path, "w").write(s)
            print(f"{path}: {ref} mirrored ({axis})")
            return
    raise SystemExit(f"{ref} not found")


swap_labels("sheets/output-switch.kicad_sch", "hierarchical_label", ("OUT_A", "322.58", "142.24"), ("OUT_B", "322.58", "160.02"))
mirror_symbol("sheets/t1s.kicad_sch", "FL501", "x")
swap_labels("sheets/t1s.kicad_sch", "label", ("T1S_P", "548.64", "200.66"), ("T1S_N", "548.64", "195.58"))
swap_labels("sheets/t1s.kicad_sch", "label", ("T1S_P_DROP", "466.09", "176.53"), ("T1S_N_DROP", "509.27", "172.72"))
swap_labels("sheets/t1s.kicad_sch", "label", ("T1S_P_END", "483.87", "172.72"), ("T1S_N_END", "514.35", "176.53"))
