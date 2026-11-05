#!/usr/bin/env python3
"""The T1S rule changes that go with the hand-routed line (D28): rules_t1s.py IN.kicad_dru OUT.kicad_dru

- "T1S 0.75 mm from other nets" no longer applies inside T1S_PINS_U501 (B.Cu at U501 pins 28-32 and just
  south): pin 29 (VDDA, 3V3_MAIN) sits 0.5 mm from pin 30 (TRXP), so the rule cannot hold at the pins.
- "T1S pairs coupled" (gap 0.14-0.16 mm) applies where the line is meant to be coupled: inside
  T1S_COUPLED_F (the trunk's middle on F.Cu) and T1S_COUPLED_IN2 (the taps' pair on In2). KiCad checks it on
  every parallel stretch of P and N however far apart (relay legs 2.5 mm apart, pin fan-outs).
- The PHY pair's skew limit becomes 4.5 mm: its crossing (FL501's P winding sits west, U501's P pin east)
  puts two through-board vias on P, 2 mm each in KiCad's length; the CMC pair keeps 0.5 mm.
"""
import sys

s = open(sys.argv[1]).read()
rep = [('''(condition "A.NetClass == 'T1S_100R' && A.Type != 'Pad' && B.NetClass != 'T1S_100R' && B.Type != 'Pad'")''',
        '''(condition "A.NetClass == 'T1S_100R' && A.Type != 'Pad' && B.NetClass != 'T1S_100R' && B.Type != 'Pad' && !A.intersectsArea('T1S_PINS_U501')")'''),
       ('''(rule "T1S pairs coupled"
	(condition "A.inDiffPair('/T1S*')")''', '''(rule "T1S pairs coupled"
	(condition "A.inDiffPair('/T1S*') && (A.intersectsArea('T1S_COUPLED_F') || A.intersectsArea('T1S_COUPLED_IN2'))")'''),
       ('''(rule "T1S pairs matched within 0.5 mm"
	(condition "A.inDiffPair('/T1S/T1S_CMC') || A.inDiffPair('/T1S/T1S_PHY')")
	(constraint skew (max 0.5mm) (within_diff_pairs)))''', '''(rule "T1S pairs matched within 0.5 mm"
	(condition "A.inDiffPair('/T1S/T1S_CMC')")
	(constraint skew (max 0.5mm) (within_diff_pairs)))

# The PHY pair crosses once (FL501's P winding west, U501's P pin east): P hops over N through two
# through-board vias, 2 mm each in KiCad's length, about 27 ps against a T1S bit of 80 ns (D28).
(rule "T1S PHY pair matched within 0.5 mm plus its crossing's two vias"
	(condition "A.inDiffPair('/T1S/T1S_PHY')")
	(constraint skew (max 4.5mm) (within_diff_pairs)))''')]
for a, b in rep:
    if b in s:
        continue
    assert a in s, a[:60]
    s = s.replace(a, b)
open(sys.argv[2], "w").write(s)
print(f"{sys.argv[2]}: T1S rules for the hand-routed line")
