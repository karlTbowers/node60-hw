# Diagram drafts (2026-10-21)

Node60's architecture is shown as **two D2 diagrams** (handbook chapter 08):

| File | View |
|---|---|
| `power.d2` | Power: battery path → VBAT_PROT bus → always-on supply, switched rails, switched loads. Line weight shows current. |
| `signals.d2` | Signals, digital and analog: inputs left, S32K344 centre, controlled devices right. Solid = digital, dashed = analog into the ADC. |

Every block links to its section of the architecture site. Both are **left-to-right**; the layout engine is set in each file (`power.d2`: **dagre**, `signals.d2`: **ELK**), so no `--layout` flag is needed.

During the Starlight port these move to `docs/src/diagrams/` and this folder is deleted.

Render locally:
```bash
d2 power.d2 power.svg
d2 signals.d2 signals.svg
```
