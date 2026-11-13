#!/usr/bin/env python3
"""rip_nets.py BOARD OUT NET [NET ...] [--keep-locked] -- delete every track and via of the named nets
(all of them, fan-out stubs too; --keep-locked leaves locked copper). KiCad's Python."""
import sys, pcbnew
a = [x for x in sys.argv[1:] if not x.startswith("--")]; keep = "--keep-locked" in sys.argv
b = pcbnew.LoadBoard(a[0]); nets = set(a[2:])
kill = [t for t in b.GetTracks() if t.GetNetname() in nets and not (keep and t.IsLocked())]
for t in kill: b.Delete(t)
b.Save(a[1]); print(f"ripped {len(kill)} items of {len(nets)} nets")
