#!/usr/bin/env python3
"""Check a DropOut board schematic against handbook chapter 05.

  python3 scripts/check_schematic.py <board>        (run from the repo root)

Uses `kicad-cli sch export netlist` (KiCad's own view of the hierarchy) and checks:

  Sheet files
    - the root sheet is <board>.kicad_sch at the repo root;
    - every other .kicad_sch lives directly in sheets/ (flat, no subfolders);
    - every file in sheets/ is used by the hierarchy.
  Page numbers
    - every sheet's page number is a plain integer from 1 to 99, unique; the root is page 1.
  Reference designators
    - each is <PREFIX><page><nn>: page x 100 + nn, nn from 01 to 99
      (R201 = first resistor on page 2; C1101 = first capacitor on page 11);
    - none is left unannotated ("R?").
  Net names (rule O-2: every net is named)
    - no net keeps a KiCad auto-generated name ("Net-(R201-Pad2)");
    - an "unconnected-(...)" net is allowed only when every pin on it carries a
      no-connect flag or is a no-connect pin; any other is a pin left unwired.

Exits 1 with one ::error:: line per problem (readable in GitHub Actions annotations).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

SKIP_DIRS = {".git", "lib", "docs", "node_modules", "outputs"}


def kicad_cli():
    for c in ("kicad-cli", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"):
        if shutil.which(c) or os.path.exists(c):
            return c
    sys.exit("::error::kicad-cli not found")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    board = sys.argv[1]
    root_file = f"{board}.kicad_sch"
    errors = []

    if not os.path.exists(root_file):
        print(f"No {root_file} yet - skipping schematic checks.")
        return

    # Sheet files on disk
    on_disk = set()
    for dirpath, dirnames, filenames in os.walk("."):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for f in filenames:
            if f.endswith(".kicad_sch"):
                on_disk.add(os.path.normpath(os.path.join(dirpath, f)))
    for path in sorted(on_disk):
        if path == root_file:
            continue
        if os.path.dirname(path) != "sheets":
            errors.append(f"{path}: sheet files belong directly in sheets/ (only {root_file} sits at the root)")

    # KiCad's view of the hierarchy
    with tempfile.TemporaryDirectory() as tmp:
        net = os.path.join(tmp, "net.xml")
        r = subprocess.run(
            [kicad_cli(), "sch", "export", "netlist", "--format", "kicadxml", "-o", net, root_file],
            capture_output=True, text=True,
        )
        if r.returncode != 0 or not os.path.exists(net):
            sys.exit(f"::error::kicad-cli could not export the netlist:\n{r.stdout}{r.stderr}")
        tree = ET.parse(net)

    page_of = {}  # sheet tstamps path -> page number (int)
    used = set()
    pages_seen = {}
    for sheet in tree.iter("sheet"):
        name, page, tstamps = sheet.get("name"), sheet.get("number"), sheet.get("tstamps")
        source = (sheet.findtext("title_block/source") or "").strip()
        if source:
            used.add(source)
        if not re.fullmatch(r"[1-9]\d?", page or ""):
            errors.append(f"sheet {name}: page number '{page}' must be an integer from 1 to 99")
            continue
        n = int(page)
        if n in pages_seen:
            errors.append(f"sheet {name}: page {n} is also used by {pages_seen[n]}")
        pages_seen[n] = name
        page_of[tstamps] = n
    if pages_seen.get(1) != "/":
        errors.append("the root sheet must be page 1")

    for path in sorted(on_disk):
        if path != root_file and os.path.dirname(path) == "sheets" and os.path.basename(path) not in used:
            errors.append(f"{path}: not used by the hierarchy (remove it or place it as a sheet)")

    # Reference designators
    for comp in tree.iter("comp"):
        ref = comp.get("ref")
        sp = comp.find("sheetpath")
        page = page_of.get(sp.get("tstamps") if sp is not None else None)
        where = sp.get("names") if sp is not None else "?"
        m = re.fullmatch(r"([A-Z]+)(\d+)", ref or "")
        if not m:
            errors.append(f"{ref} on {where}: not annotated as <PREFIX><number>")
            continue
        if page is None:
            continue  # page-number error already reported
        num = int(m.group(2))
        if num // 100 != page or not 1 <= num % 100 <= 99:
            errors.append(
                f"{ref} on {where} (page {page}): expected {m.group(1)}{page}01-{m.group(1)}{page}99; "
                "re-annotate with 'First free after sheet number x 100'"
            )

    # Net names: an auto-generated name means a wire with no label (or a dropped label)
    for net in tree.iter("net"):
        name = net.get("name") or ""
        pins = ", ".join(f"{n.get('ref')}.{n.get('pin')}" for n in net.iter("node"))
        if re.search(r"(^|/)Net-\(", name):
            errors.append(f"net {name} ({pins}): unnamed; give it a label (chapter 05, every net is named)")
        elif re.search(r"(^|/)unconnected-\(", name):
            if not all("no_connect" in (n.get("pintype") or "") for n in net.iter("node")):
                errors.append(f"net {name} ({pins}): pin is not wired; wire it or place a no-connect flag")

    for e in errors:
        print(f"::error::{e}")
    if errors:
        sys.exit(f"{len(errors)} schematic convention problem(s).")
    print(
        f"Schematic conventions OK: {len(pages_seen)} sheet(s), "
        f"{sum(1 for _ in tree.iter('comp'))} part(s), {sum(1 for _ in tree.iter('net'))} net(s)."
    )


if __name__ == "__main__":
    main()
