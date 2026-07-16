# -*- coding: utf-8 -*-
import sys, json
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
import build_spec
data=json.load(open("extract/mendeley_local.json",encoding="utf-8"))
docs=data["documents"]
reps=json.load(open("extract/create_plan.json",encoding="utf-8"))["unique_reps"]

specs=[build_spec.build_spec(docs[m]) for m in reps]
print("=== TYPE DISTRIBUTION (Zotero) ===")
print(Counter(s["ztype"] for s in specs).most_common())
print("\n=== COVERAGE ===")
for k in ("creators","tags","note"):
    print(f"  with {k}: {sum(1 for s in specs if s[k])}")
withextra=sum(1 for s in specs if s['fields'].get('extra'))
print(f"  with extra field: {withextra}")

# show a few full specimens across types
print("\n=== SAMPLE SPECS ===")
seen=set()
for m,s in zip(reps,specs):
    if s["ztype"] in seen: continue
    seen.add(s["ztype"])
    print(f"\n--- [{s['ztype']}] (mendeley id {m[:8]}) ---")
    for k,v in s["fields"].items(): print(f"  {k}: {v[:90]}")
    if s["creators"]: print(f"  creators: {s['creators'][:4]}")
    if s["tags"]: print(f"  tags: {s['tags'][:6]}")
    if s["note"]: print(f"  note: {s['note'][:120].replace(chr(10),' / ')}")
    if len(seen)>=8: break
