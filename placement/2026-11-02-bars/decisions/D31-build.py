#!/usr/bin/env python3
"""Build the D31 decision page (output switches turned; FL501/K501 swapped) with its pictures embedded."""
import base64
import pathlib
import re

HERE = pathlib.Path(__file__).parent
css = re.search(r"<style>[\s\S]*?</style>", (HERE / "D28-t1s-route.html").read_text()).group(0)


def img(name, cap):
    b = base64.b64encode((HERE / "img" / name).read_bytes()).decode()
    return (f'<figure><button type="button" aria-label="Enlarge: {cap}"><img src="data:image/png;base64,{b}" alt="{cap}" loading="lazy"></button>'
            f"<figcaption>{cap}</figcaption></figure>")


page = f"""<title>Turned switches, swapped T1S pins</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo+Narrow:wght@600;700&family=JetBrains+Mono:wght@400;600;700&family=Source+Sans+3:wght@400;600&display=swap">
{css}
<div class="wrap">
<header>
  <div class="eyebrow"><b>D31</b><span>node60</span><span>Placement · Schematic</span><span>2026-11-06</span></div>
  <h1>Land the turned output switches and the FL501/K501 swap, with the two schematic edits they need?</h1>
</header>

<section><h2>Why this is decided now</h2>
<p>You chose D30 D: work up turning the three output switches 180°. You also asked to swap FL501's and K501's pinout on the schematic so the PHY pair needs no crossing.</p>
<p>Both are worked up on copies of main and measured. Nothing is on main yet. Each needs a schematic edit, and the schematic and the board land together, so <code>--schematic-parity</code> stays clean.</p></section>

<section class="part"><h2 class="ph">1 · The output switches turned 180°</h2><div class="gc">
{img("d31_cell_today.png", "U701 today: the logic pins face south into the pocket, and the OUT blocks at the chip's north end close it off.")}
{img("d31_cell_turned.png", "U701 turned, on a copy, with its parts and pours redrawn. The logic pins and their parts face north into a channel that carries only GND on B.Cu, and the OUT blocks sit at the chip's south end, on the column heads.")}
</div>
<div class="table"><table>
<tr><th>Measured on the copy</th><th>Today</th><th>Turned</th></tr>
<tr><td>Output copper DCR, OUT1–OUT6 (85 °C)</td><td>2.16, 1.87, 2.16, 1.86, 2.14, 1.89 mΩ (spread 0.30)</td><td><b>1.65, 1.69, 1.63, 1.70, 1.63, 1.67 mΩ</b> (spread 0.07)</td></tr>
<tr><td>Fast route: signal nets that cut an output pour</td><td>9 (each into its own cell's pocket); outputs 2.33–4.66 mΩ</td><td>2, both through-runs: SW_LHI (shared by all three cells) and SPI4 MISO (west cell) passing the middle cell. Four outputs stay at 1.67–1.72 mΩ</td></tr>
<tr><td>Hot loop: CVBB1 (C601) pad 1 to the VBB pad, pad 2 to GND pin 1</td><td>0.45 / 4.48 mm</td><td>0.45 / 4.48 mm (turns with the chip)</td></tr>
<tr><td>DRC (KiCad, node60.kicad_dru)</td><td>0 errors</td><td>0 errors; every power and GND join in the cells closed again</td></tr>
</table></div>
<h3>What moves</h3>
<ul>
  <li><b>Turned with each switch</b>, about its centre: CVBB1 (C601, still over the VBB pad on F.Cu), the VDD decap (C603), CSNS (C604), the first output's cap (C605), and R601–R606 with their copies.</li>
  <li><b>C606</b> goes to the mirror image of C605's new place, beside its own pins.</li>
  <li><b>Unchanged:</b> the NTC group (C607, R607, RT601), the VBB bulk cap C602 (now between the two new OUT blocks), and the parked test points.</li>
  <li><b>Output pours:</b> the B.Cu blocks move from y 104.5–111 to 112.2–118.7, and the F.Cu strips from 109.25–111 to 112.2–113.95. The columns to the connectors stay.</li>
  <li><b>Joins:</b> D29's three pocket feeds go. R601/R701/R801 now take 3V3 from R607/R707/R807's line, 16 mm each.</li>
</ul>
<h3>The schematic edit</h3>
<p>Turned, each switch's first channel (pins 6–8) sits on the east and its second (pins 9–11) on the west. So in <code>sheets/output-switch.kicad_sch</code> (one file, placed three times), the two channels swap hierarchical labels: pins 6–8 go to <code>OUT_B</code> and pins 9–11 to <code>OUT_A</code>.</p>
<p>The connectors keep their OUT numbers: OUT1 is still J904. But OUT1, OUT3 and OUT5 are now driven by each switch's second channel, so the firmware's channel map changes. I'll note it in <code>mcu-config.yaml</code>.</p></section>

<section class="part"><h2 class="ph">2 · FL501 and K501 swapped (you asked)</h2><div class="gc">
{img("d31_t1s_today.png", "Today. P (red) is west of N (blue) from the trunk's taps through C511, FL501 and K501. U501's TRXP (pin 30) is east of TRXN, so the PHY pair crosses, with P hopping over N through two vias.")}
{img("d31_t1s_swapped.png", "Swapped, on a copy: P on FL501's other winding and K501's other pole, C511 and C512 change sides, and the taps' vias swap. P is east along the whole chain and runs straight into TRXP.")}
</div>
<div class="table"><table>
<tr><th>Measured on the copy (t1s_stubs.py, routed copper; P / N)</th><th>Today</th><th>Swapped</th></tr>
<tr><td>Trunk J912 to J903</td><td>38.9 / 38.9 mm</td><td>38.9 / 38.9 mm</td></tr>
<tr><td>PHY stub: trunk to U501</td><td>28.6 / 25.6 mm</td><td><b>24.6 / 25.6 mm</b></td></tr>
<tr><td>Relay leg: trunk to K501</td><td>23.7 / 24.7 mm</td><td>23.9 / 24.9 mm</td></tr>
<tr><td>End node, J912 used / J903 used: dangle past the relay</td><td>28.5 / 21.6 · 10.4 / 17.3 mm</td><td>27.7 / 22.4 · 11.2 / 16.5 mm</td></tr>
<tr><td>Vias on the PHY pair</td><td>2 (the crossing)</td><td><b>0</b></td></tr>
<tr><td>PHY pair skew rule</td><td>4.5 mm (0.5 plus the crossing's two vias, D28)</td><td><b>back to 0.5 mm</b>; DRC passes with it</td></tr>
<tr><td>DRC; T1S nets open</td><td>0 errors</td><td>0 errors; every T1S line, cap, choke, relay and termination net joined (only your six strap and IRQ nets open, as today)</td></tr>
<tr><td>RMII windows</td><td>TX setup 0.59, hold 0.69 ns</td><td>TX setup 0.60, hold 0.69, RX setup 3.32, hold 1.37 ns (TXD0 re-routed, 62.3 mm)</td></tr>
</table></div>
<h3>What changes</h3>
<ul>
  <li><b>Schematic (<code>sheets/t1s.kicad_sch</code>):</b>
    <ul>
      <li>FL501 is mirrored about its horizontal axis. Its wires stay and meet the other winding: PHY_P on pin 2, CMC_P on pin 3.</li>
      <li>On K501, the <code>T1S_P</code> and <code>T1S_N</code> labels swap between COM1 and COM2. The pole labels swap too (<code>P_DROP</code>↔<code>N_DROP</code>, <code>P_END</code>↔<code>N_END</code>), so P's resistors are the ones on pole 2: R518 and R519 become P's, R516 and R517 N's.</li>
      <li>K501's coil pins stay where they are. The relay latches by coil polarity, so swapping them would swap set and reset.</li>
    </ul></li>
  <li><b>Board:</b>
    <ul>
      <li>C511 (P) moves east and C512 west.</li>
      <li>The taps' vias swap: N's north of the trunk at x 149.0, P's south at 149.815.</li>
      <li>The line, TERM_CT, the coil and drive lines are routed again by the existing scripts.</li>
    </ul></li>
  <li><b>Polarity:</b> TRXP and TRXN at U501, and P and N at both connectors, are unchanged, so the LAN8670's topology discovery is unaffected.</li>
</ul></section>

<section class="answer"><h2>Your answer</h2><div class="opts"><span>Land both</span><span>Land 1 only</span><span>Land 2 only</span><span>Something else</span></div>
<p>On "land both", the steps are:</p>
<ul>
  <li>Edit both sheets.</li>
  <li>Apply the turn and the swap to <code>node60.kicad_pcb</code>, from <code>turn_cells.py</code>, <code>spec_t1s.py swap</code> and <code>power_shapes.json</code>, with the pads' nets taken from the edited schematic.</li>
  <li>Re-run the routing scripts.</li>
  <li>Run CI's DRC with <code>--schematic-parity</code>, <code>prove_rules.py</code>, the stub, RMII and DCR measurements, and update the pose tables and records.</li>
  <li>Open one PR.</li>
</ul></section>

<footer>D31 · placement/2026-11-02-bars/decisions/D31-build.py · copies of main 011bcc7; cells/turn_cells.py, t1s/swap_pins.py, spec_t1s.py swap; KiCad DRC with node60.kicad_dru; resistances at 85 °C from the filled copper</footer>
</div>
<div id="zoom" hidden><img alt=""></div>
<script>
const z = document.getElementById('zoom'), zi = z.querySelector('img');
document.querySelectorAll('figure button').forEach(b => b.addEventListener('click', () => {{ zi.src = b.querySelector('img').src; z.hidden = false; }}));
z.addEventListener('click', () => {{ z.hidden = true; }});
document.addEventListener('keydown', e => {{ if (e.key === 'Escape') z.hidden = true; }});
</script>
"""
(HERE / "D31-turn-and-swap.html").write_text(page)
print(HERE / "D31-turn-and-swap.html", len(page) // 1024, "KB")
