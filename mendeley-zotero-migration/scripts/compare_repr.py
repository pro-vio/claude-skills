# -*- coding: utf-8 -*-
"""Compare how Zotero's importer stored an annotation vs the Mendeley source,
so we can build a reliable matching signature for attribution."""
import sqlite3, sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True).cursor()
amap = json.load(open("extract/ann_by_filehash.json", encoding="utf-8"))
h2att = json.load(open("extract/zotero_sha1_to_attach.json", encoding="utf-8"))

# find a filehash with student annotations AND present in zotero
target = None
for h, lst in amap.items():
    if h in h2att and any(x["author"] for x in lst):
        target = h
        break
print("filehash:", target)
lst = amap[target]
print("Mendeley: %d adnotari (%d ale studentilor)" % (len(lst), sum(1 for x in lst if x["author"])))
atts = h2att[target]
print("atasamente Zotero cu acest continut:", atts)

for a in atts:
    rows = c.execute("SELECT type,authorName,text,comment,color,pageLabel,sortIndex,position FROM itemAnnotations WHERE parentItemID=?", (a,)).fetchall()
    print(f"\n--- atasament {a}: {len(rows)} adnotari in DB ---")
    for r in rows[:4]:
        pos = json.loads(r[7])
        print(f"  type={r[0]} author={r[1]!r} page={r[5]} pageIndex={pos.get('pageIndex')}")
        print(f"     rect0={pos['rects'][0] if pos.get('rects') else None}")
        print(f"     text={(r[2] or '')[:60]!r}")
        print(f"     comment={(r[3] or '')[:60]!r}  color={r[4]}")

print("\n--- sursa Mendeley (primele 4) ---")
for x in lst[:4]:
    cu = x["ann"].get("_custom") or {}
    ps = cu.get("positions") or []
    body = x["ann"].get("body") or []
    btxt = None
    if body and isinstance(body[0], dict):
        v = body[0].get("value")
        btxt = v.get("text") if isinstance(v, dict) else v
    print(f"  type={cu.get('type')} author={x['author']!r} page={ps[0].get('page') if ps else None} color={cu.get('color')}")
    if ps:
        print(f"     top_left={ps[0].get('top_left')} bottom_right={ps[0].get('bottom_right')}")
    print(f"     body={str(btxt)[:60]!r}")
