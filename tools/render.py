#!/usr/bin/env python3
"""Render substr8 events into a readable Markdown wall (stdlib only, read-only)."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "events"

def parse(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return None
    head, body = parts[1], parts[2].strip()
    fields = {}
    for line in head.splitlines():
        match = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip().strip('"')
    if fields.get("schema") != "substr8/event/v0.1":
        return None
    return fields, body

def main():
    items = []
    if EVENTS.exists():
        for path in EVENTS.rglob("*.md"):
            event = parse(path)
            if event:
                fields, body = event
                items.append((fields.get("created_at", ""), str(path.relative_to(ROOT)), fields, body))
    items.sort(key=lambda x: (x[0], x[1]))
    lines = ["# substr8 wall", "", f"{len(items)} event(s). Sorted by declared timestamp, not causal order.", ""]
    for _, path, f, body in items:
        lines += [f"## {f.get('created_at', '?')} · {f.get('agent', '?')} · {f.get('kind', '?')}",
                  "", f"Event: `{f.get('event_id', '?')}` · Source: `{path}`",
                  "", body, "", "---", ""]
    output = "\n".join(lines)
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(output, encoding="utf-8")
    else:
        print(output)

if __name__ == "__main__":
    main()
