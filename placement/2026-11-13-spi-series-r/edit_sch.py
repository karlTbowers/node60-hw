#!/usr/bin/env python3
"""edit_sch.py -- adds the SPI series resistors to the schematic (decisions S01 to S03, decisions/log.md).

Run once on main's sheets (it refuses a sheet that already has R409 or R?08). Text edits only: KiCad's own
save is not involved, so nothing else on the sheets moves.

MCU sheet (p4): R409 to R418, 33 R, between U401's ball (new local net <NAME>_MCU) and the bus net <NAME>,
which keeps its name, its test point and its sheet pin. Output-switch sheet (p6 to p8, one file): R608 / R708 /
R808 between the switch's SDO pin (new local net SW_SDO) and the sheet's SDO port.
"""
import re, sys, uuid, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent)); import sx
ROOT = pathlib.Path(__file__).resolve().parents[2]
NS = uuid.UUID('6ff2ab56-1a9c-5e28-ac58-84e4785c9f14')
uid = lambda name: str(uuid.uuid5(NS, 'spi-series-r/' + name))
LIB = 'DropOut_Resistor:AC0402JR-0733RL'

def lib_symbol():
    s = (ROOT / 'sheets/t1s.kicad_sch').read_text(); t = sx.parse(s)
    for n in sx.kids(sx.kid(t, 'lib_symbols'), 'symbol'):
        if n[2] == LIB: a, b = sx.span(n); return s[a:b]

def template():
    """R401's block on the MCU sheet: the board's text layout for an upright passive. Fields from the 33 R part."""
    s = (ROOT / 'sheets/mcu-nvm.kicad_sch').read_text(); t = sx.parse(s)
    for n in t[1:]:
        if isinstance(n, list) and n[1] == 'symbol' and '(reference "R401")' in s[slice(*sx.span(n))]:
            a, b = sx.span(n); blk = s[a:b]
    blk = blk.replace('AC0402JR-0710KL', 'AC0402JR-0733RL').replace('"Value" "10k"', '"Value" "33R"')
    blk = blk.replace('10 kΩ', '33 Ω').replace('YAG3517CT-ND', 'YAG3543CT-ND')
    assert blk.count('33') >= 4
    return blk, (160.02, 260.35)

def resistor(key, x, y, paths_refs):
    blk, (x0, y0) = template()
    def mv(m): return '(at %s %s %s)' % (fmt(float(m[1]) - x0 + x), fmt(float(m[2]) - y0 + y), m[3])
    blk = re.sub(r'\(at ([-\d.]+) ([-\d.]+) (\d+)\)', mv, blk)
    n = iter(range(99))
    blk = re.sub(r'\(uuid "[^"]+"\)', lambda m: '(uuid "%s")' % uid('%s/%d' % (key, next(n))), blk)
    inst = ''.join('\n\t\t\t\t(path "%s"\n\t\t\t\t\t(reference "%s")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)' % pr for pr in paths_refs)
    blk = re.sub(r'\(project "node60".*\n\t\t\t\)', lambda m: '(project "node60"' + inst + '\n\t\t\t)', blk, flags=re.S)
    return '\t' + blk + '\n'
def fmt(v): return ('%.3f' % v).rstrip('0').rstrip('.')
def wire(key, x1, y1, x2, y2):
    return ('\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n'
            '\t\t(uuid "%s")\n\t)\n') % (fmt(x1), fmt(y1), fmt(x2), fmt(y2), uid(key))
def label(key, name, x, y, rot, just):
    return ('\t(label "%s"\n\t\t(at %s %s %d)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify %s)\n\t\t)\n'
            '\t\t(uuid "%s")\n\t)\n') % (name, fmt(x), fmt(y), rot, just, uid(key))
def hlabel(key, name, shape, x, y, rot, just):
    return ('\t(hierarchical_label "%s"\n\t\t(shape %s)\n\t\t(at %s %s %d)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n'
            '\t\t\t(justify %s)\n\t\t)\n\t\t(uuid "%s")\n\t)\n') % (name, shape, fmt(x), fmt(y), rot, just, uid(key))
def box(key, x0, y0, x1, y1, title, note):
    return ('\t(rectangle\n\t\t(start %s %s)\n\t\t(end %s %s)\n\t\t(stroke\n\t\t\t(width 0.254)\n\t\t\t(type dash)\n\t\t\t(color 132 132 132 1)\n\t\t)\n'
            '\t\t(fill\n\t\t\t(type none)\n\t\t)\n\t\t(uuid "%s")\n\t)\n' % (fmt(x0), fmt(y0), fmt(x1), fmt(y1), uid(key + '/box')) +
            '\t(text "%s"\n\t\t(exclude_from_sim no)\n\t\t(at %s %s 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.778 1.778)\n\t\t\t\t(thickness 0.3)\n\t\t\t\tbold\n\t\t\t)\n'
            '\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)\n' % (title, fmt(x0), fmt(y0 - 1.27), uid(key + '/title')) +
            '\t(text "%s"\n\t\t(exclude_from_sim no)\n\t\t(at %s %s 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n'
            '\t\t\t(justify left top)\n\t\t)\n\t\t(uuid "%s")\n\t)\n' % (note.replace('\n', '\\n'), fmt(x0 + 2.54), fmt(y0 + 2.54), uid(key + '/note')))

def relabel(s, kind, name, x, y, new):
    """The label of `kind` called `name` at (x, y) becomes a local label `new` on the same point."""
    t = sx.parse(s)
    for n in t[1:]:
        if isinstance(n, list) and n[1] == kind and n[2] == name:
            at = sx.kid(n, 'at')
            if abs(float(at[2]) - x) < 0.01 and abs(float(at[3]) - y) < 0.01:
                a, b = sx.span(n); rot = int(at[4])
                just = {0: 'left bottom', 180: 'right bottom'}[rot]
                u = sx.kid(n, 'uuid')[2]
                new_txt = label('x', new, x, y, rot, just).strip().replace(uid('x'), u)
                return s[:a] + new_txt + s[b:]
    raise SystemExit('no %s %s at %s %s' % (kind, name, x, y))

def move_label(s, kind, name, x, y, nx):
    t = sx.parse(s)
    for n in t[1:]:
        if isinstance(n, list) and n[1] == kind and n[2] == name:
            at = sx.kid(n, 'at')
            if abs(float(at[2]) - x) < 0.01 and abs(float(at[3]) - y) < 0.01:
                a, b = sx.span(at); return s[:a] + '(at %s %s %s)' % (fmt(nx), at[3], at[4]) + s[b:]
    raise SystemExit('no label to move')

def add(s, blocks, lib):
    if LIB not in s: s = s.replace('\t(lib_symbols\n', '\t(lib_symbols\n\t\t' + lib + '\n', 1)
    i = s.rindex('\t(embedded_fonts no)')
    return s[:i] + ''.join(blocks) + s[i:]

MCU_PATH = '/55f51841-30a3-4965-b848-b796f60054d0/0ad74954-de59-42a0-82d0-e554fbd19453'
SW_PATHS = ['/55f51841-30a3-4965-b848-b796f60054d0/' + u for u in
            ('ceecbbf6-496b-4919-aa4d-b8194f44838e', '68ca6db2-fb88-4c17-b54b-7131815c5345', '618ad5c3-1fe8-46d2-96b6-b9e1aa40313d')]
# ref, net, kind and position of the label at U401's ball
MCU = [('R409', 'SPI4_SWITCH1_SCK',  'hierarchical_label', 586.74, 114.3),
       ('R410', 'SPI4_SWITCH1_MOSI', 'hierarchical_label', 586.74, 111.76),
       ('R411', 'SPI4_SWITCH1_CS_L', 'hierarchical_label', 586.74, 109.22),
       ('R412', 'SPI5_SWITCH2_SCK',  'hierarchical_label', 472.44, 226.06),
       ('R413', 'SPI5_SWITCH2_MOSI', 'hierarchical_label', 472.44, 228.6),
       ('R414', 'SPI5_SWITCH2_CS_L', 'hierarchical_label', 436.88, 210.82),
       ('R415', 'SPI3_SWITCH3_SCK',  'hierarchical_label', 721.36, 233.68),
       ('R416', 'SPI3_SWITCH3_MOSI', 'hierarchical_label', 721.36, 238.76),
       ('R417', 'SPI3_SWITCH3_CS_L', 'hierarchical_label', 756.92, 200.66),
       ('R418', 'SPI2_FLASH_SCK',    'label',              586.74, 238.76)]
NOTE_MCU = ("One 33R at U401 on every SPI line the MCU drives toward an output switch (SCK, MOSI, CS_L), and on the log\n"
            "flash's SCK. TI's TPS2HCS08-Q1 data sheet (SLVSHR0, Figure 9-1 and Table 9-1) draws RSPI on all four lines:\n"
            "22R typical, optional, for EMI and transient limits; its SPI timing (6.6) is given with 220R. 33R is the board's\n"
            "series value (R503/R504). The switch's SDO has its resistor at the switch (R608/R708/R808, pages 6 to 8).\n"
            "<NET>_MCU is the stub from the ball to the resistor; <NET> keeps the line, its test point and its sheet pin.\n"
            "Place each resistor at its ball. Decisions S01 to S03, placement/2026-11-13-spi-series-r.")
NOTE_SW = ("RSPI on SDO, at the switch's pin (TI Figure 9-1, Table 9-1):\n33R as on the other three lines (MCU sheet).\n"
           "Open (S03): TI's RSDO 768R instead,\nfor its loss-of-ground case; same footprint.")

def main():
    lib = lib_symbol()
    p = ROOT / 'sheets/mcu-nvm.kicad_sch'; s = p.read_text()
    if '"R409"' in s: raise SystemExit('already applied')
    X0, Y, PITCH = 441.96, 480.06, 20.32
    blocks = [box('mcu', X0 - 10.16, Y - 58.42, X0 + 10 * PITCH, Y + 35.56, 'SPI series resistors at U401 (R409-R418)', NOTE_MCU)]
    for i, (ref, net, kind, lx, ly) in enumerate(MCU):
        if ref == 'R415':   # the MISO port sits one pin above: the stub's label goes 27.94 mm further out
            blocks.append(wire(ref + '/w0', lx, ly, lx - 27.94, ly)); s = move_label(s, kind, net, lx, ly, lx - 27.94)
            lx -= 27.94
        s = relabel(s, kind, net, lx, ly, net + '_MCU')
        x = X0 + i * PITCH
        blocks += [resistor(ref, x, Y, [(MCU_PATH, ref)]),
                   wire(ref + '/w1', x, Y - 6.35, x, Y - 3.81), wire(ref + '/w2', x, Y + 3.81, x, Y + 6.35),
                   label(ref + '/l1', net + '_MCU', x, Y - 6.35, 90, 'left bottom'),
                   label(ref + '/l2', net, x, Y + 6.35, 270, 'right bottom') if kind == 'label' else
                   hlabel(ref + '/l2', net, 'output', x, Y + 6.35, 270, 'right')]
    p.write_text(add(s, blocks, lib))

    p = ROOT / 'sheets/output-switch.kicad_sch'; s = p.read_text()
    s = relabel(s, 'hierarchical_label', 'SDO', 236.22, 170.18, 'SW_SDO')
    x, y = 304.8, 262.89
    blocks = [box('sw', x - 12.7, y - 29.21, x + 43.18, y + 17.78, 'SDO series resistor (R?08)', NOTE_SW),
              resistor('Rx08', x, y, [(pth, 'R%d08' % (6 + i)) for i, pth in enumerate(SW_PATHS)]),
              wire('Rx08/w1', x, y - 6.35, x, y - 3.81), wire('Rx08/w2', x, y + 3.81, x, y + 6.35),
              label('Rx08/l1', 'SW_SDO', x, y - 6.35, 90, 'left bottom'),
              hlabel('Rx08/l2', 'SDO', 'output', x, y + 6.35, 270, 'right')]
    p.write_text(add(s, blocks, lib))
main()
