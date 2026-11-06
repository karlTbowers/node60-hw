#!/usr/bin/env python3
"""Swap FL501's windings and K501's poles on a board's pads, as the schematic change will (Node60, 2026-11-05).

    $KPY swap_pins.py BOARD OUT

User (2026-11-05): swap the pinout on FL501 and K501 so the PHY pair needs no crossing. Today every part
south of the trunk has P on the west and only U501 has TRXP (pin 30) east of TRXN (pin 31), so the PHY pair
crosses once (P over N through two vias). With P on FL501's other winding (pins 2/3 instead of 1/4) and on
K501's other pole (COM2/RST2/SET2, pins 6/7/5, instead of COM1/RST1/SET1, pins 3/2/4), P is east along the
whole chain and runs straight into pin 30. The coil pins (1 S+, 8 R+) stay: the relay latches by polarity.
On the schematic, FL501 is mirrored about its horizontal axis (its wires then meet the other winding) and
K501's two poles' labels swap. This script does the same on the pads, so a trial can be drawn before the
schematic is edited.
"""
import sys

import pcbnew

SWAP = {"FL501": [("1", "2"), ("3", "4")], "K501": [("2", "7"), ("3", "6"), ("4", "5")]}
b = pcbnew.LoadBoard(sys.argv[1])
for ref, pairs in SWAP.items():
    f = b.FindFootprintByReference(ref)
    pads = {p.GetNumber(): p for p in f.Pads()}
    for a, z in pairs:
        na, nz = pads[a].GetNet(), pads[z].GetNet()
        pads[a].SetNet(nz); pads[z].SetNet(na)
        print(f"{ref} pad {a}: {nz.GetNetname()}   pad {z}: {na.GetNetname()}")
b.Save(sys.argv[2])
