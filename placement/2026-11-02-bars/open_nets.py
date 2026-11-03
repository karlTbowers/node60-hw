#!/usr/bin/env python3
"""Print the nets a KRT route left open, one per line, from the last JSON_SUMMARY in its log."""
import json
import sys

s = [l for l in open(sys.argv[1]) if l.startswith("JSON_SUMMARY: ")]
d = json.loads(s[-1][len("JSON_SUMMARY: "):]) if s else {}
nets = list(d.get("failed_single", [])) + [m["net_name"] for m in d.get("failed_multipoint", [])]
print("\n".join(dict.fromkeys(nets)))
