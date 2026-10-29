#!/usr/bin/env python3
"""Write the S32K344 (U401) pin map that the docs site's MCU pinout page draws.

  python3 scripts/mcu_pinmap.py            (run from the repo root; rewrites the JSON)
  python3 scripts/mcu_pinmap.py --check    (exit 1 if the committed JSON is out of date)

Inputs:
  - the schematic, through `kicad-cli sch export netlist`: the net on every U401 ball and
    what else sits on that net (external pull resistors, test points, other ICs);
  - the library pin table lib/dropout-kicad-library/parts/S32K344EHT1MMMST/pins.csv: every
    ball's port name and alternate functions (generated from NXP's IOMUX table).

Output: docs/src/data/mcu-pins.json. Committed, because the docs build has no kicad-cli.
Firmware settings (function, pull, edge, initial state) live in docs/src/data/mcu-config.yaml;
the docs build checks them against this file.

"Available" interfaces: an unused peripheral instance whose required signals can each go on a
different free ball (a ball with no net). Partly used instances list their spare signals.
"""
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

REF = "U401"
PINS = "lib/dropout-kicad-library/parts/S32K344EHT1MMMST/pins.csv"
OUT = "docs/src/data/mcu-pins.json"
ROWS = "ABCDEFGHJKLMNPRTU"
RAILS = {"3V3_MAIN", "VDDAU_AON", "1V5_CORE", "VBAT_PROT"}

# Interface kinds: instance pattern, required signals (one set must fit), optional signals.
KINDS = [
    ("LPUART", r"LPUART(\d+)_", [["TX", "RX"]], ["CTS", "RTS"]),
    ("LPSPI", r"LPSPI(\d+)_", [["SCK", "SIN", "SOUT", "PCS"]], []),
    ("LPI2C", r"LPI2C(\d+)_", [["SCL", "SDA"]], ["SCLS", "SDAS", "HREQ"]),
    ("CAN", r"CAN(\d+)_", [["TX", "RX"]], []),
    ("QuadSPI", r"QuadSPI()_", [["SCKFA", "PCSFA", "IOFA0", "IOFA1"]], ["IOFA2", "IOFA3"]),
    ("SAI", r"SAI(\d+)_", [["BCLK", "SYNC", "D0"]], ["MCLK", "D1", "D2", "D3"]),
]
# Pooled resources: count the free balls that offer each channel.
POOLS = [
    ("ADC", r"^(ADC\d)_"),
    ("eMIOS", r"^eMIOS_(\d)_CH"),
    ("FlexIO", r"^FXIO_(D)\d+"),
    ("EIRQ", r"^(EIRQ)\["),
    ("WKPU", r"^(WKPU)\["),
    ("CMP", r"^(CMP\d)_"),
    ("LCU", r"^(LCU\d)_"),
    ("TRGMUX", r"^(TRGMUX)_"),
]


def kicad_cli():
    for c in ("kicad-cli", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"):
        if subprocess.run(["which", c], capture_output=True).returncode == 0 or os.path.exists(c):
            return c
    sys.exit("mcu_pinmap: kicad-cli not found")


def netlist():
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "net.xml")
        subprocess.run([kicad_cli(), "sch", "export", "netlist", "--format", "kicadxml",
                        "-o", out, "node60.kicad_sch"], check=True, capture_output=True)
        return ET.parse(out)


def short(net):
    return net.rsplit("/", 1)[-1]


def strip_signal(alt):
    """'LPUART0_RX:input' -> 'LPUART0_RX'; '~{RESET}' -> 'RESET_b'."""
    s = alt.rsplit(":", 1)[0]
    return re.sub(r"^~\{(.*)\}$", r"\1_b", s)


def connections(tree):
    """ball -> (net, [connections]) for U401; connections describe the rest of the net."""
    value = {c.get("ref"): c.findtext("value") for c in tree.iter("comp")}
    nets, pin_net = {}, {}
    for n in tree.iter("net"):
        nodes = [(x.get("ref"), x.get("pin"), x.get("pinfunction") or "") for x in n.iter("node")]
        nets[n.get("name")] = nodes
        for r, p, _ in nodes:
            pin_net[(r, p)] = n.get("name")
    out = {}
    for name, nodes in nets.items():
        for r, p, _ in nodes:
            if r != REF:
                continue
            if name.startswith("unconnected"):
                out[p] = (None, [], None)
                continue
            conns, pulls = [], []
            for r2, p2, f2 in nodes:
                if r2 == REF:
                    continue
                if r2[0] in "RC" and r2[1].isdigit():
                    far = [short(pin_net[(r2, q)]) for q in ("1", "2") if q != p2 and (r2, q) in pin_net]
                    far = far[0] if far else "?"
                    conns.append(f"{r2} {value[r2]} to {far}")
                    if r2[0] == "R" and value[r2] not in ("0R", "0"):
                        if far == "GND":
                            pulls.append(f"{value[r2]} down ({r2})")
                        elif far in RAILS or far.endswith("_VDD"):
                            pulls.append(f"{value[r2]} up to {far} ({r2})")
                elif r2.startswith("TP"):
                    conns.append(f"{r2} test point")
                else:
                    func = re.sub(r"_[0-9]+$", "", f2)
                    func = re.sub(r"~\{(.*?)\}", r"\1_L", func)
                    conns.append(f"{r2} {func}" if func and func != "~" else f"{r2} {value[r2]}")
            out[p] = (short(name), conns, ", ".join(pulls) or None)
    return out


def assign(signals, free_by_signal, taken=frozenset()):
    """Distinct free balls for every signal, or None (small backtracking match)."""
    if not signals:
        return {}
    s, rest = signals[0], signals[1:]
    for ball in free_by_signal.get(s, []):
        if ball in taken:
            continue
        sub = assign(rest, free_by_signal, taken | {ball})
        if sub is not None:
            return {s: ball, **sub}
    return None


def interfaces(balls):
    free = [b for b in balls if b["net"] is None and b["kind"] == "signal"]
    used = [b for b in balls if b["net"] is not None and b["kind"] == "signal"]
    result = []
    for kind, pat, required, optional in KINDS:
        instances = {}
        for b in balls:
            if b["kind"] != "signal":
                continue
            for sig in b["alternates"]:
                m = re.match(pat, sig)
                if m:
                    func = re.sub(r"\d+$", "", sig[m.end():]) if kind == "LPSPI" and sig[m.end():].startswith("PCS") else sig[m.end():]
                    instances.setdefault(m.group(1), {}).setdefault(func, []).append((sig, b))
        for inst in sorted(instances, key=lambda x: int(x) if x.isdigit() else -1):
            funcs = instances[inst]
            name = f"{kind}{inst}"
            in_use = {}
            for b in used:
                if b["function"] and re.match(pat, b["function"]) and re.match(pat, b["function"]).group(1) == inst:
                    in_use[b["function"]] = b["ball"]
            options = {}
            for func, entries in funcs.items():
                fb = sorted({b["ball"] for sig, b in entries if b["net"] is None}, key=ball_key)
                sigs = sorted({sig for sig, _ in entries})
                options[func] = {"signals": sigs, "free": fb}
            free_by_signal = {f: o["free"] for f, o in options.items()}
            fit = None
            for req in required:
                if all(f in options for f in req):
                    fit = assign(req, free_by_signal)
                    if fit is not None:
                        break
            status = "used" if in_use else ("available" if fit else "conflict")
            # What occupies the balls a conflicting instance would need
            blocked_by = {}
            if status == "conflict":
                for f in required[0]:
                    if f in options and not options[f]["free"]:
                        blocked_by[f] = sorted({b["net"] for sig, b in funcs[f]})
                    elif f not in options:
                        blocked_by[f] = []
            result.append({
                "kind": kind, "name": name, "status": status, "used": in_use,
                "required": required[0], "optional": optional,
                "example": fit or {},
                "blockedBy": blocked_by,
                "signals": {f: options[f] for f in sorted(options)},
            })
    pools = []
    for kind, pat in POOLS:
        groups = {}
        for b in balls:
            if b["kind"] != "signal":
                continue
            for sig in b["alternates"]:
                m = re.match(pat, sig)
                if m:
                    g = groups.setdefault(m.group(1), {"used": set(), "free": set(), "freeBalls": set()})
                    if b["net"] is None:
                        g["free"].add(sig)
                        g["freeBalls"].add(b["ball"])
                    elif b["function"] == sig:
                        g["used"].add(sig)
        for g, v in sorted(groups.items()):
            pools.append({"kind": kind, "name": g if kind not in ("eMIOS", "FlexIO") else f"{kind}{g if kind == 'eMIOS' else ''}",
                          "used": sorted(v["used"], key=sig_key), "free": sorted(v["free"] - v["used"], key=sig_key),
                          "freeBalls": sorted(v["freeBalls"], key=ball_key)})
    return result, pools


def sig_key(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def ball_key(b):
    return (ROWS.index(b[0]), int(b[1:]))


def build():
    tree = netlist()
    conns = connections(tree)
    balls = []
    with open(PINS, newline="") as f:
        for r in csv.DictReader(f):
            alts = [strip_signal(a) for a in r["alternates"].split(";") if a]
            net, cn, pull = conns.get(r["number"], (None, [], None))
            port = r["name"].split("/")[0] if r["unit"] != "Power" else None
            balls.append({
                "ball": r["number"],
                "row": ROWS.index(r["number"][0]),
                "col": int(r["number"][1:]) - 1,
                "name": re.sub(r"~\{(.*?)\}", r"\1_b", r["name"]),
                "port": port,
                "kind": "signal" if port else ("osc" if r["name"] in ("EXTAL", "XTAL") else "supply"),
                "alternates": alts,
                "net": net,
                "connects": cn,
                "externalPull": pull,
                "function": None,
            })
    balls.sort(key=lambda b: ball_key(b["ball"]))
    return balls


def main():
    check = "--check" in sys.argv
    balls = build()
    # The planned function is the docs config's business; the generator only needs it to
    # tell which peripheral instances are taken, so read it from the config's `function:`.
    cfg = {}
    cfg_path = "docs/src/data/mcu-config.yaml"
    if os.path.exists(cfg_path):
        net = None
        for line in open(cfg_path):
            m = re.match(r"^([A-Z0-9_]+):\s*$", line)
            if m:
                net = m.group(1)
            m = re.match(r"^\s+function: (\S+)", line)
            if m and net:
                cfg[net] = m.group(1)
    for b in balls:
        if b["net"] in cfg:
            b["function"] = cfg[b["net"]]
    ifaces, pools = interfaces(balls)
    data = {
        "_generated": "by scripts/mcu_pinmap.py from the schematic netlist and the library pins.csv; do not edit",
        "part": "S32K344EHT1MMMST",
        "ref": REF,
        "package": "257MAPBGA (LFBGA-257, 14 x 14 mm, 0.8 mm pitch)",
        "rows": ROWS,
        "balls": balls,
        "interfaces": ifaces,
        "pools": pools,
    }
    text = json.dumps(data, indent=1) + "\n"
    if check:
        current = open(OUT).read() if os.path.exists(OUT) else ""
        if current != text:
            sys.exit(f"::error::{OUT} is out of date: run python3 scripts/mcu_pinmap.py")
        print(f"{OUT} is up to date.")
        return
    with open(OUT, "w") as f:
        f.write(text)
    nets = sum(1 for b in balls if b["net"])
    print(f"Wrote {OUT}: {len(balls)} balls, {nets} connected, "
          f"{sum(1 for i in ifaces if i['status'] == 'available')} spare interface instances.")


if __name__ == "__main__":
    main()
