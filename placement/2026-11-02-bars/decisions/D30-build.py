#!/usr/bin/env python3
"""Build the D30 decision page (signals into the output cells' pockets) with its pictures embedded."""
import base64
import pathlib
import re

HERE = pathlib.Path(__file__).parent
css = re.search(r"<style>[\s\S]*?</style>", (HERE / "D28-t1s-route.html").read_text()).group(0)


def img(name, cap):
    b = base64.b64encode((HERE / "img" / name).read_bytes()).decode()
    return (f'<figure><button type="button" aria-label="Enlarge: {cap}"><img src="data:image/png;base64,{b}" alt="{cap}" loading="lazy"></button>'
            f"<figcaption>{cap}</figcaption></figure>")


page = f"""<title>Signals into the output cells</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo+Narrow:wght@600;700&family=JetBrains+Mono:wght@400;600;700&family=Source+Sans+3:wght@400;600&display=swap">
{css}
<div class="wrap">
<header>
  <div class="eyebrow"><b>D30</b><span>node60</span><span>Placement · Output cells</span><span>2026-11-05</span></div>
  <h1>Work up turning the three output switches 180°, so their logic pins face the MCU?</h1>
</header>

<section><h2>Why this is decided now</h2>
<p>D29 found that each output switch's logic pins sit in a pocket. Its two output pours close the pocket to the north on F.Cu and B.Cu, and every inner layer is a plane there. D29 fed 3V3 from below, through In3.</p>
<p>The signals are the bigger part. Seven nets per cell have to reach U401's south rows:</p>
<ul>
  <li>CS, SCK, SDI and SDO;</li>
  <li>FLT and SNS (through R606/R706/R806);</li>
  <li>LHI, shared by all three cells.</li>
</ul>
<p>This page decides the cell's pour topology and orientation before you route the cells. It doesn't propose routes: pocket fan-out is your hand work, and my grid search couldn't route even the unconstrained case at the board's via and hole rules. No route lengths from it appear here.</p>
<p>The <b>middle cell is the hard case in every option</b>. On F.Cu, the VBAT_IN busbar's area sits right above it and takes every other net's track down to y 109.12. On B.Cu, the power entry's block sits above it.</p></section>

<section><h2>Today</h2><div class="gc">
{img("d30_now.png", "U701 today. The pocket is dashed magenta; pins are labelled. On F.Cu, the blue outline is the VBAT_IN bar's area and the amber strips are OUT3 and OUT4's top strips. On B.Cu, the OUT3 and OUT4 blocks run from the pins to the columns. Every way in from the north crosses one of them.")}
{img("d30_turned.png", "Option D on a copy: U701 turned 180°, footprint only, today's pours left as they are. Logic pins (SCK, CS, SDO, SDI, FLT, LHI) now face north. OUT pins face south over the column heads, OUT3's on the east and OUT4's on the west.")}
</div></section>

<section><h2>Facts it rests on</h2><div class="facts">
<div class="fact"><span class="k">Crossing costs</span><span class="v">One 0.3 mm track into U701's pocket from the north: OUT3 2.16 → 2.93 mΩ. The fast route's signals: outputs 3.90, 4.66, 4.09, 2.98, 2.33, 2.68 mΩ, against 2.16, 1.87, 2.16, 1.86, 2.14, 1.89 today</span><span class="s">copper_r.py, D29</span></div>
<div class="fact"><span class="k">Cutting the F.Cu strips (B)</span><span class="v">Every output +0.5 mΩ, still equal: OUT1/3/5 2.67 mΩ, OUT2/4/6 2.32 mΩ</span><span class="s">copper_r.py on a copy</span></div>
<div class="fact"><span class="k">B at the middle cell</span><span class="v">The B.Cu channel north of U701 (x 150.15–154.45) has 1,430 legal 0.35/0.40 mm via sites, but none at y ≥ 109.3. Each one's F.Cu side is inside the busbar's area, where no other net's track may run, so the cut strips can't be reached there</span><span class="s">plan_joins via rules on a copy with the strips cut</span></div>
<div class="fact"><span class="k">Turning 180°</span><span class="v">The OUT pins land at the south end, but on swapped sides: OUT3's at x 155.2 (nearer J907) and OUT4's at x 149.4 (nearer J906)</span><span class="s">U701 turned on a copy</span></div>
<div class="fact"><span class="k">Switch</span><span class="v">TPS2HCS08-Q1, 8 mΩ per channel (typical): the copper is about a fifth of each output's path</span><span class="s">TI data sheet title</span></div>
</div></section>

<section><h2>Options</h2><div class="options n2">
<article class="opt rec"><div class="opt-head"><span class="key">D</span><h3>Turn the switches 180° (work it up)</h3><span class="tag">Recommended</span></div>
<p>Each switch turns round. Its logic pins then face north into the B.Cu channel between the cell and the power entry, which carries only GND. Its OUT pins face south, straight onto the column heads, so the output path gets shorter. I haven't measured that DCR yet.</p>
<p><b>One catch:</b> turned, each switch's two channels sit on the far side from their own connectors. So each cell's two connectors swap channels in the schematic: J904/J905, J906/J907 and J908/J909 swap OUT numbers, or each output-switch sheet swaps its two channel labels. That changes the OUTn ↔ connector table and the firmware's channel map, so it's your call.</p>
<p><b>The work-up</b>, on a copy (D24, U302 turned with its cell mirrored, is the precedent):</p>
<ul>
  <li>Re-pose one cell and copy it to the other two.</li>
  <li>Move the pin-local passives: C603/C604, R602–R606 and their copies.</li>
  <li>Redraw the OUT blocks at the south end and their via fields.</li>
  <li>Check the hot loop to C601/C602 again.</li>
  <li>Re-measure the six DCRs.</li>
  <li>Redo D29's three pocket feeds: they can then come from the north.</li>
</ul>
<p>You'd get one more page with the turned cell measured before anything lands.</p></article>
<article class="opt"><div class="opt-head"><span class="key">B</span><h3>Cut back the outputs' F.Cu top strips</h3><span class="tag">Fallback</span></div>
<p>Every output gets +0.5 mΩ and stays equal. That opens an F.Cu lane over the B.Cu block for the <b>west and east cells</b>, which lie outside the busbar's x-range.</p>
<p>The <b>middle cell gains nothing</b>: no via south of the busbar's area reaches the lane. Its signals would still have to cross an output pour.</p></article>
<article class="opt"><div class="opt-head"><span class="key">X</span><h3>Cross the output pours</h3><span class="tag">Not recommended</span></div>
<p>This is what any route from the north does today. On the fast route's evidence it costs up to +2.8 mΩ, and the outputs end up unequal (2.33–4.66 mΩ). That breaks "six equal outputs".</p></article>
<article class="opt"><div class="opt-head"><span class="key">S</span><h3>In from the south, along the connector edge</h3><span class="tag">Not recommended</span></div>
<p>No output pour is crossed. Measured only for one 3V3 net: 113–139 mm per cell before the pocket's own fan-out. Seven signals per cell from the MCU in the north-east would mean runs round most of the board, and the west cell's longest of all.</p></article>
</div></section>

<section class="answer"><h2>Your answer</h2><div class="opts"><span>D: work it up (connector swap OK in principle)</span><span>B</span><span>X</span><span>Something else</span></div>
<p>On D, I'll turn U701 on a copy, re-pose its cell, redraw its pours, measure, copy it to U601 and U801, and bring the result on its own page with pictures, the DCR table and the schematic change spelled out. Nothing lands on main until you answer that page.</p></section>

<footer>D30 · placement/2026-11-02-bars/decisions/D30-build.py · measured on copies of main 011bcc7 (KiCad DRC with node60.kicad_dru; resistances at 85 °C from the filled copper)</footer>
</div>
<div id="zoom" hidden><img alt=""></div>
<script>
const z = document.getElementById('zoom'), zi = z.querySelector('img');
document.querySelectorAll('figure button').forEach(b => b.addEventListener('click', () => {{ zi.src = b.querySelector('img').src; z.hidden = false; }}));
z.addEventListener('click', () => {{ z.hidden = true; }});
document.addEventListener('keydown', e => {{ if (e.key === 'Escape') z.hidden = true; }});
</script>
"""
(HERE / "D30-pocket-signals.html").write_text(page)
print(HERE / "D30-pocket-signals.html", len(page) // 1024, "KB")
