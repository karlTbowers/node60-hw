# Decision log: routing run, 2026-11-12

The user asked (2026-11-12) to finish routing everything, then put the test points back, and later
said: "for this session - i approve all of your recommendations. dont stop and wait for me. just
record what decisions were made so i can review later if i want." and "you have my permission to
slightly trim power shapes if you need the area to run signals and there is no other way to do it."
Every decision below was taken by Claude under that approval unless it says otherwise. Each one says
how to undo it.

| Id | Decision | Taken? | Why | Where it is | To undo |
|---|---|---|---|---|---|
| D34-1 | Draw the In2 signal window (north of y 70) and the power-only keep-outs on In1, In2 south, In3 and In4 on the board again | Yes, on main | Decision D17 A (user, 2026-11-04) put them there; commit `111fb0e` (2026-11-05) lost them, because `scripts/draw_rule_areas.py` redraws them only when given `--window` and `--power-only` and was run without. Since then every router run laid signals on In2 through the power band | `node60.kicad_pcb` rule areas `SIGNAL_WINDOW_In2Cu_1`, `POWER_ONLY_*`; `prep.sh` | Run `draw_rule_areas.py node60.kicad_pcb` without the flags |
| D34-2 | Rip the two relay-termination drive lines (`/T1S_TERM_END`, `/T1S_TERM_DROP`, routed 2026-11-05) and lay them again | Yes, on main | They passed on both sides of MCU ball E1, so SPI2_FLASH_CS_L could never leave the ball field. The router laid them again clear of it | `prep.sh`; the lines on main are the bulk route's | Restore them from commit `794e299`'s board |
| D34-3 | T1S block: R501 turned 180 degrees, C509 moved 0.25 mm east, C509's VDDAU_AON via moved into its pad at (158.1, 47.45), pin 25's track narrowed to 0.2 mm, R501's GND pad joined to C510's | Yes, on main | U501 pin 26 (RBIAS) had no way to R501: the REFCLK via and C509 left 0.4 mm, and R501's RBIAS pad was on the far side of its GND pad | `hand/h0.json`, `blocks/t1s.poses.json`, `power_shapes.json` | Revert those entries; RBIAS is then open again |
| D34-4 | U201's VBAT_D joins: pin 6's plane via moved from (150.025, 74.825) to (150.9, 73.8); pin 22 gets its own plane via at (152.75, 78.5); the two tracks that tied pins 6, 22 and 24 together on B.Cu deleted | Yes, on main | The joins of 2026-11-05 caged pins 1 to 5 and pin 23 (a track down the chip's west side and a U round pin 23). All three pins still reach the VBAT_D planes on In2 and In3 | `hand/h0.json`, `power_shapes.json` | Restore the "Power join VBAT_D: U201.*" groups from the spec at `794e299` |
| D34-5 | 1V5_CORE_FB drawn by hand; the 1V5 switch-node stub now starts at the north end of U303 pin 7 | Yes, on main | The rule "1V5_CORE_FB 1 mm from the switch nodes" cannot be met by a track leaving pin 5 at its centre: pins 5 and 7 are 1.0 mm apart | `hand/h0.json`, `power_shapes.json` | Revert; the feedback net is then unrouted |
| D34-6 | Five nets pre-routed by `mini_route.py` before the bulk route: T1S_RBIAS, SPI2_FLASH_CS_L, NTC_RSENSE, 1V5_EN, VDDAU_AON_REG | Yes, on main | KiCadRoutingTools leaves these open in every run. All five pass DRC with the board's own rules | `hand/h1.jobs.json`, `hand/h1.json` | `rip_nets.py` on those nets |
| D34-7 | The full routed attempt is NOT landed on main | Decided: keep it off main | It leaves 30 items unconnected and reaches the middle cell and U201 by cutting the outer-layer power pours: see REPORT.md, "What the route cost the power paths". That is more than the slight trim the user allowed | Branch `layout/route-attempt-6layer` holds it (board, spec, block tables) | Merge that branch if the cost is acceptable |
| D34-8 | Test points: put back on the routed attempt only (62 of 62 placed, 55 joined); they stay parked on main | Yes | They are placed on the routed copper, so they belong with it. On main's board, still unrouted in the band, they would be in the router's way again | `place_test_points.py`, `hand/test_points.json` (attempt branch) | none needed |
| D33 | Allow mask-covered signal tracks on F.Cu under the GND busbar (not battery nets, not pours; the VBAT_IN bar unchanged) | **No: recommended, not taken** | It needs an edit to `node60.kicad_dru`, the file that judges the route, and the session's safety check stopped Claude from changing it. It is the user's to make. Decision page D33 has the case | Page: see REPORT.md | not applicable |
| - | Re-placing U201's divider resistors R204 to R207 in pin order | No | Only needed if D33 is refused: with F.Cu open under the GND bar the crossings there need no part to move | REPORT.md, "U201" | not applicable |

Tool changes made on the way (all in the repo):

- `scripts/draw_power.py`: a locked stub longer than 2 mm no longer stacks on a redraw (merged with D32).
- `placement/2026-11-02-bars/judge_route.sh`: three optional switches, off by default: `S0_HOOK` (a script run
  on the router's copy), `KEEP_DECAPS=1` (leave U401's caps where the board has them) and `ROUTE_NETS`
  (the bulk passes' net patterns).
- Not changed: `node60.kicad_dru`, `node60.kicad_pro`.
