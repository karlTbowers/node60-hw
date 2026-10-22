# Diagram drafts (2026-10-21)

The Node60 system block diagram, written in both D2 (`system.d2`) and Mermaid (`system.mmd`) to compare them. Same blocks, groups, connections, and click targets as the Rev C diagram.

During the Starlight port these move to `docs/src/diagrams/` and this folder is deleted. The chosen format follows handbook chapter 08.

Render locally:
```bash
d2 --layout dagre system.d2 system.svg
mmdc -i system.mmd -o system-mermaid.svg
```
