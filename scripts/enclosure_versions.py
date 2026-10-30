#!/usr/bin/env python3
"""Draw every Node60 enclosure version (docs build step).

For each version in place_connectors.VERSIONS: write its spec as JSON, run the drawing
engine on it into <out>/<version>/, and finally write <out>/enclosure-versions.json, the
index the options page and the 3D mockup read (every version's full enclosure.json, plus its
SurLok plug check from check_surlok_clearance.py).

    python3 scripts/enclosure_versions.py docs/src/diagrams/build
    python3 scripts/enclosure_versions.py --check
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import enclosure_drawing  # noqa: E402
from check_surlok_clearance import check_version  # noqa: E402
from enclosure_geometry import spec  # noqa: E402
from place_connectors import CURRENT, VERSIONS  # noqa: E402


def main(argv):
    if "--check" in argv:
        bad = 0
        for vid in VERSIONS:
            problems = enclosure_drawing.check(spec(vid))
            for p in problems:
                print(f"{vid}: {p}", file=sys.stderr)
            print(f"{vid}: {len(problems)} problems")
            bad += len(problems)
        sys.exit(1 if bad else 0)
    out = Path(argv[1] if len(argv) > 1 else "docs/src/diagrams/build")
    index = {"current": CURRENT, "versions": {}}
    for vid in VERSIONS:
        d = out / vid
        d.mkdir(parents=True, exist_ok=True)
        (d / "spec.json").write_text(json.dumps(spec(vid), indent=1))
        enclosure_drawing.main(["enclosure_drawing.py", str(d / "spec.json"), str(d)])
        index["versions"][vid] = {**json.loads((d / "enclosure.json").read_text()),
                                  "plug_check": check_version(vid, quiet=True)}
    (out / "enclosure-versions.json").write_text(json.dumps(index, indent=1) + "\n")


if __name__ == "__main__":
    main(sys.argv)
