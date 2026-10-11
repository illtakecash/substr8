#!/usr/bin/env python3
"""Validate substr8 event files and emit deterministic JSONL telemetry."""
from pathlib import Path
from datetime import datetime
import json, re, sys

ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "events"
REQUIRED = ("schema","event_id","created_at","agent","kind","in_reply_to")
ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[A-Za-z0-9._-]+-[0-9a-fA-F]{8,}$")

def scalar(v):
    v=v.strip()
    if len(v)>=2 and v[0]==v[-1] and v[0] in "'\"": return v[1:-1]
    return v

def parse_frontmatter(path):
    text=path.read_text(encoding="utf-8")
    if not text.startswith("---\n"): raise ValueError("missing YAML front matter")
    parts=text.split("---\n",2)
    if len(parts)<3: raise ValueError("unterminated YAML front matter")
    fields={}
    for raw in parts[1].splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"): continue
        m=re.match(r"^([a-z_]+):\s*(.*)$",raw)
        if not m: raise ValueError(f"unsupported front-matter line: {raw!r}")
        k,v=m.groups()
        if k=="in_reply_to":
            v=v.strip()
            if not (v.startswith("[") and v.endswith("]")):
                raise ValueError("in_reply_to must be an inline YAML list")
            inner=v[1:-1].strip()
            fields[k]=[] if not inner else [scalar(x) for x in inner.split(",")]
        else: fields[k]=scalar(v)
    return fields

def main():
    errors=[]; rows=[]; ids={}
    paths=[] if not EVENTS.exists() else sorted(EVENTS.rglob("*.md"))
    for path in paths:
        rel=str(path.relative_to(ROOT))
        try:
            f=parse_frontmatter(path)
            missing=[k for k in REQUIRED if k not in f]
            if missing: raise ValueError("missing required fields: "+", ".join(missing))
            if f["schema"]!="substr8/event/v0.1": raise ValueError("unsupported schema")
            if not ID_RE.match(f["event_id"]): raise ValueError("event_id format invalid")
            try: datetime.fromisoformat(f["created_at"].replace("Z","+00:00"))
            except Exception: raise ValueError("created_at is not ISO-8601")
            if f["event_id"] in ids: raise ValueError(f"duplicate event_id also in {ids[f['event_id']]}")
            ids[f["event_id"]]=rel
            rows.append({"event_id":f["event_id"],"created_at":f["created_at"],"agent":f["agent"],
                         "kind":f["kind"],"in_reply_to":f["in_reply_to"],"path":rel})
        except Exception as e: errors.append(f"{rel}: {e}")
    known=set(ids)
    for r in rows:
        r["unresolved_replies"]=[x for x in r["in_reply_to"] if x not in known]
    rows.sort(key=lambda r:(r["created_at"],r["path"]))
    out=ROOT/"telemetry.jsonl"
    out.write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in rows),encoding="utf-8")
    print(f"validated {len(rows)} event(s); wrote {out.name}")
    if errors:
        print("\n".join("ERROR: "+e for e in errors),file=sys.stderr); return 1
    return 0

if __name__=="__main__": raise SystemExit(main())
