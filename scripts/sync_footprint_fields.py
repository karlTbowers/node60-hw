#!/usr/bin/env python3
"""Copy each symbol's fields and DNP flag from the schematic onto its footprint on the board.

What KiCad's Update PCB from Schematic does for fields, without the GUI and without touching
any position, pad, net or drawing. kicad-cli's schematic parity check (CI runs it) reports a
footprint that lacks a field its symbol has, or holds a different value: Manufacturer, MPN, the
distributor numbers, Datasheet, Description, Notes and so on. Added fields are hidden, on the
Fab layer of the footprint's side.

Run with KiCad's own Python (it provides the pcbnew module) from the repo root:

    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \\
        scripts/sync_footprint_fields.py .
    git checkout -- node60.kicad_pro    # pcbnew's save rewrites the project file with defaults

Left alone: Reference, Value and Footprint (Update PCB's job), and `ki_fp_filters`, which KiCad
reads as the footprint filter when it loads a footprint, so parity reports it missing whatever
the board holds (19 warnings on Node60, 2026-11-03). Parts with no footprint on the board
(C207 and L201 until they are chosen) are reported by parity, not here.
"""
import glob
import os
import re
import sys

import pcbnew

SKIP = {"Reference", "Value", "Footprint", "ki_fp_filters"}


def symbol_fields(root):
    """{reference: ({field: value}, dnp)} for every placed symbol, each sheet instance included."""
    out = {}
    for f in [os.path.join(root, "node60.kicad_sch")] + sorted(glob.glob(os.path.join(root, "sheets/*.kicad_sch"))):
        s = open(f).read()
        for m in re.finditer(r'\n\t\(symbol\n\t\t\(lib_id', s):
            blk = s[m.start():s.find("\n\t)", m.end())]
            props = {k: re.sub(r'\\(.)', r'\1', v)
                     for k, v in re.findall(r'\(property "([^"]+)" "((?:[^"\\]|\\.)*)"', blk)}
            dnp = re.search(r'\n\t\t\(dnp (yes|no)\)', blk)
            for ref in re.findall(r'\(reference "([^"]+)"\)', blk):
                out[ref] = ({k: v for k, v in props.items() if k not in SKIP},
                            dnp.group(1) == "yes" if dnp else None)
    return out


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    board_path = os.path.join(root, "node60.kicad_pcb")
    syms = symbol_fields(root)
    board = pcbnew.LoadBoard(board_path)
    added, changed, dnp_set = 0, 0, []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref not in syms:
            continue
        fields, dnp = syms[ref]
        for k, v in fields.items():
            if fp.HasField(k):
                if fp.GetFieldText(k) != v:
                    fp.SetField(k, v)
                    changed += 1
                continue
            fp.SetField(k, v)
            fld = fp.GetField(k)
            fld.SetVisible(False)
            fld.SetLayer(pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab)
            added += 1
        if dnp is not None and fp.IsDNP() != dnp:
            fp.SetDNP(dnp)
            dnp_set.append(f"{ref} DNP={'yes' if dnp else 'no'}")
    board.Save(board_path)
    print(f"{added} fields added, {changed} values changed, DNP: {', '.join(dnp_set) or 'no change'}")
    print("now: git checkout -- node60.kicad_pro (pcbnew's save rewrites it)")


if __name__ == "__main__":
    main()
