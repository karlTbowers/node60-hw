#!/usr/bin/env python3
"""Build the D29 decision page (3V3 into the power band) with its pictures embedded."""
import base64
import pathlib
import re

HERE = pathlib.Path(__file__).parent
css = re.search(r"<style>[\s\S]*?</style>", (HERE / "D28-t1s-route.html").read_text()).group(0)


def img(name, cap):
    b = base64.b64encode((HERE / "img" / name).read_bytes()).decode()
    return (f'<figure><button type="button" aria-label="Enlarge: {cap}"><img src="data:image/png;base64,{b}" alt="{cap}" loading="lazy"></button>'
            f"<figcaption>{cap}</figcaption></figure>")


page = f"""<title>3V3 into the power band</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo+Narrow:wght@600;700&family=JetBrains+Mono:wght@400;600;700&family=Source+Sans+3:wght@400;600&display=swap">
{css}
<div class="wrap">
<header>
  <div class="eyebrow"><b>D29</b><span>node60</span><span>Routing · Power</span><span>2026-11-05</span></div>
  <h1>Feed the power band's 3V3 loads from the In3 3V3 plane, widened into the margins nothing uses?</h1>
</header>

<section><h2>Why this is decided now</h2>
<p>Eleven parts in the power band need 3V3:</p>
<ul>
  <li><b>R601, R701, R801:</b> the 10 Ω into each output switch's VDD pin.</li>
  <li><b>R607, R707, R807:</b> the 10 kΩ NTC pull-ups.</li>
  <li><b>Power entry and sensing:</b> U202 (INA228), R211 with C215, and U203 (TMP175).</li>
</ul>
<p>D22 said 3V3 goes into the band "by hand tracks, alike for the six outputs". All the copper here is tracks on <b>F.Cu and B.Cu</b>, which is what those layers are for. But in the band, top and bottom are mostly taken already, and every inner layer is a plane:</p>
<ul>
  <li><b>No 3V3 plane in the band.</b> In3 is VBAT_PROT inside x 72–238, y 71–122, and In2 is VBAT_PROT south of y 70.</li>
  <li><b>The busbars' F.Cu areas take every other net's track.</b> The GND bar covers x 67–243, y 61–80, right across the 3V3 plane's edge. The VBAT_IN bar covers x 92–218, y 90–109.</li>
  <li><b>B.Cu carries the entry's VBAT pours and the six output pours.</b> A thin track through one cuts a slot across the current's path.</li>
</ul>
<p>Working this through turned up something bigger than 3V3: <b>each output switch's logic pins sit in a pocket</b>, enclosed by its two output pours on both F.Cu and B.Cu (first picture). That pocket holds VDD, SNS, DI, LHI, FLT and the four SPI pins, plus R601/R701/R801. Copper reaching it from the north has to cut through an output pour exactly where the current leaves pins 6–11 for the column to its connector.</p></section>

<section><h2>The pocket</h2><div class="gc">
{img("D29-cell.png", "The middle cell, U701. The dashed magenta box is the pocket; amber is OUT3 (west) and OUT4 (east). The pocket is closed to the north on both F.Cu and B.Cu and open only to the south, toward the connectors. In3 (bottom panel) is VBAT_PROT under the cell down to y 122 and free below it. Blue is option C's feed to R701: a via up from In3 at y 122.6, F.Cu north, a via down beside R701.")}
{img("D29-fastroute_cell.png", "The same cell on the placement judge's fast route. Its signal tracks cut OUT3's and OUT4's pours beside the pins. On that board the six outputs measure 2.33–4.66 mΩ, against 1.86–2.16 mΩ today.")}
</div></section>

<section><h2>Facts it rests on</h2><div class="facts">
<div class="fact"><span class="k">Output copper today</span><span class="v">OUT1/3/5 2.16, 2.16, 2.14 mΩ; OUT2/4/6 1.87, 1.86, 1.89 mΩ (switch pins to connector, 85 °C)</span><span class="s">power/copper_r.py, all four copper layers</span></div>
<div class="fact"><span class="k">Against the switch</span><span class="v">TPS2HCS08-Q1 is an 8 mΩ switch per channel, so the copper is about a fifth of each output's path. +0.5 mΩ is about +5 % of the path, or 0.05 W more per output at 10 A</span><span class="s">TI TPS2HCS08-Q1 data sheet title (8 mΩ, typical)</span></div>
<div class="fact"><span class="k">One track into a pocket</span><span class="v">A single 0.3 mm 3V3 track into U701's pocket from the north raised OUT3 to 2.93 mΩ (+36 %); the same track routed shortest raised it to 3.80 mΩ</span><span class="s">trunk_options.py, measured on copies</span></div>
<div class="fact"><span class="k">Signals too</span><span class="v">The fast route put 11–12 signal nets into each pocket (SPI ×4, FLT, SNS, DI, LHI, VDD, NTC); outputs 3.90, 4.66, 4.09, 2.98, 2.33, 2.68 mΩ</span><span class="s">judge_d28/s6, refilled</span></div>
<div class="fact"><span class="k">In3's margins</span><span class="v">Unassigned: x 40–72 and 238–270 south of the 3V3 plane, and the whole strip y 122–140 under the output connectors. The VBAT_PROT pour was cut to the band on 2026-11-04 (loss sweep)</span><span class="s">D17 A as amended, power_shapes.json</span></div>
<div class="fact"><span class="k">Tools</span><span class="v">power/joins/trunk_options.py (grid search on F.Cu and B.Cu from any legal plane via, pours costed or blocked), trunk_picture.py, trunk_to_spec.py; every option drawn on a copy of main by draw_power.py and judged by KiCad DRC</span><span class="s">layout/3v3-trunk branch</span></div>
</div></section>

<section><h2>Options for the pocket loads (R601, R701, R801)</h2><div class="options n2">
<article class="opt rec"><div class="opt-head"><span class="key">C</span><h3>Widen the In3 3V3 plane into the free margins</h3><span class="tag">Recommended</span></div>
<p>The In3 3V3 pour covers everything on In3 that isn't VBAT_PROT, the entry's pours or the 1V5 island: the old north plane plus the west and east margins and the strip under the connectors. It is one zone, and it fills as one piece.</p>
<p>Each pocket gets a via up from that strip at y 122.6, a short F.Cu run north, and a via down beside R601/R701/R801. That's <b>9.5 mm and 2 vias per cell, the same in all three</b>, and no output pour is crossed.</p>
<p>Measured on a copy: <b>all six outputs and the whole entry chain unchanged</b>, DRC 0 errors, and every 3V3 open in the band joined (157 → 148 opens; the only 3V3 one left is U501 pin 18, a dense join).</p>
<p>It changes a plane shape that D17/D22 left unassigned, so it needs your OK. A 3V3 plane under the connector strip faces In4 GND, which adds plane capacitance.</p></article>
<article class="opt"><div class="opt-head"><span class="key">B</span><h3>Cut back each output's F.Cu top strip</h3></div>
<p>Remove the 1.75 mm F.Cu strip (y 109.25–111) between each switch's pins and its column. That opens an F.Cu lane into every pocket over the B.Cu pour, for 3V3 <b>and</b> for the signals.</p>
<p>Cost, measured: every output +0.5 mΩ, still equal. OUT1/3/5 go from 2.16 to 2.67 mΩ and OUT2/4/6 from 1.87 to 2.32 mΩ.</p>
<p>Worth having in hand for the signals (below). For 3V3 alone, C costs nothing.</p></article>
<article class="opt"><div class="opt-head"><span class="key">A</span><h3>Cross the output pours</h3><span class="tag">Not recommended</span></div>
<p>The shortest tracks on F.Cu and B.Cu, straight into each pocket. One 3V3 track raised OUT3 to 2.93 mΩ, or 3.80 mΩ routed shortest, and the outputs are no longer equal.</p></article>
<article class="opt"><div class="opt-head"><span class="key">D</span><h3>Turn the three switches 180° (not worked up)</h3></div>
<p>The pins say why the pocket exists: OUT pins 6–11 face north, and logic pins 1–5 and 12–16 face south, toward the connectors. Turned round, OUT would face its connector and the logic pins would face the MCU.</p>
<p>That re-composes the approved output cell (pours, vias, caps, thermal), so I haven't costed it. Say if you want it worked up.</p></article>
</div></section>

<section><h2>The other loads</h2>
<div class="table"><table>
<tr><th>Load</th><th>Recommended feed</th><th>Length, vias</th><th>Alternative and its cost</th></tr>
<tr><td>R607, R807 (NTC pull-ups, west and east)</td><td>From the plane, on B.Cu across GND</td><td>5.0 mm, 1 · 36.2 mm, 1</td><td>none</td></tr>
<tr><td>R707 (middle NTC pull-up)</td><td>From R607's feed, on B.Cu south of J910's pour</td><td>81.5 mm, 0</td><td>Down the entry's centre column on B.Cu: 40.3 mm, but it slits VBAT_Q2D and VBAT_D. VBAT_Q2D goes from 0.144 to 0.174 mΩ (+21 %, about +0.1 W at 60 A)</td></tr>
<tr><td>R211 and C215</td><td>From R807's feed</td><td>43.3 mm, 2</td><td>Straight down from the plane: 22 mm, but it crosses the J901-to-Q202 VBAT_IN pour on B.Cu, raising it from 0.645 to 0.796 mΩ (+23 %)</td></tr>
<tr><td>U202 (INA228)</td><td>To the 3V3 plane via north of it</td><td>8.4 mm, 1</td><td>none</td></tr>
<tr><td>U203 (TMP175)</td><td>A via into the plane beside pad 8</td><td>1.4 mm, 1</td><td>none</td></tr>
</table></div>
{img("D29-bandC.png", "Option C over the whole band, F.Cu, B.Cu and In3. Coloured lines are the feeds; the dashed grey line is R707's short way through the power entry, not recommended. On In3, green is 3V3 and blue is VBAT_PROT.")}
</section>

<section><h2>What C does not settle: the signals</h2>
<p>Your hand route meets the same pocket. About ten signals per cell have to reach pins 1–5 and 12–16, and on F.Cu and B.Cu every way in from the north cuts an output pour. The fast route shows what that costs: outputs 2.33–4.66 mΩ, unequal.</p>
<p>The ways out are:</p>
<ul>
  <li><b>B:</b> cut back the F.Cu top strips, +0.5 mΩ per output, equal.</li>
  <li><b>South lanes:</b> come in from the south along the connector edge. That's long, 113–139 mm per cell for one net.</li>
  <li><b>D:</b> turn the switches round.</li>
</ul>
<p>I'd put this to you as its own decision, with the signal counts per cell, before you route the cells. C is right either way, because it keeps 3V3 out of whatever lane the signals get.</p></section>

<section class="answer"><h2>Your answer</h2><div class="opts"><span>C (with R707 from R607's feed, R211 from R807's)</span><span>C, but R707 through the entry</span><span>B</span><span>Work up D first</span></div>
<p>On C, I'll draw it on <code>layout/3v3-trunk</code> from <code>power_shapes.json</code> (the In3 zone plus nine named feeds), run CI's DRC, and open a PR. Then I'll write the signal-entry page.</p></section>

<footer>D29 · placement/2026-11-02-bars/decisions/D29-build.py · all numbers from copies of main 954efc8 judged by KiCad DRC with node60.kicad_dru; resistances at 85 °C from the filled copper</footer>
</div>
<div id="zoom" hidden><img alt=""></div>
<script>
const z = document.getElementById('zoom'), zi = z.querySelector('img');
document.querySelectorAll('figure button').forEach(b => b.addEventListener('click', () => {{ zi.src = b.querySelector('img').src; z.hidden = false; }}));
z.addEventListener('click', () => {{ z.hidden = true; }});
document.addEventListener('keydown', e => {{ if (e.key === 'Escape') z.hidden = true; }});
</script>
"""
(HERE / "D29-3v3-band.html").write_text(page)
print(HERE / "D29-3v3-band.html", len(page) // 1024, "KB")
