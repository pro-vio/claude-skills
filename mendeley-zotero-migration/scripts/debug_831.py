# -*- coding: utf-8 -*-
"""On PDFs where the import clearly brought the full set (DB count == Mendeley count,
no students), any of my annotations still flagged 'missing' is a matching bug.
Find what distinguishes them."""
import sqlite3, sys, os, json
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot, annconv, fitz

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
ZSTOR = os.path.join(zot.ZDIR, "storage")
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True).cursor()
amap = json.load(open("extract/ann_by_filehash.json", encoding="utf-8"))
h2att = json.load(open("extract/zotero_sha1_to_attach.json", encoding="utf-8"))

def sig(typ, pos):
    p = json.loads(pos) if isinstance(pos, str) else pos
    r = (p.get("rects") or [[0, 0, 0, 0]])[0]
    return (typ, p.get("pageIndex"), round(r[0]), round(r[1]))

miss_type = Counter(); miss_nrects = Counter(); examples = []
checked = 0
for h, lst in amap.items():
    atts = h2att.get(h)
    if not atts or any(x["author"] for x in lst):
        continue
    att = atts[0]
    n = c.execute("SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID=?", (att,)).fetchone()[0]
    if n != len(lst) or n == 0:
        continue
    row = c.execute("SELECT i.key, ia.path FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID WHERE ia.itemID=?", (att,)).fetchone()
    fp = os.path.join(ZSTOR, row[0], row[1][len("storage:"):])
    if not os.path.exists(fp):
        continue
    doc = fitz.open(fp)
    existing = {}
    for typ, pos in c.execute("SELECT type,position FROM itemAnnotations WHERE parentItemID=?", (att,)).fetchall():
        existing[sig(typ, pos)] = json.loads(pos)
    for x in lst:
        r = annconv.convert(x["ann"], doc)
        if not r:
            continue
        checked += 1
        s = sig(r["type"], r["position"])
        if s in existing:
            continue
        p = json.loads(r["position"])
        miss_type[r["type"]] += 1
        miss_nrects[len(p["rects"])] += 1
        if len(examples) < 4:
            # what does the DB have on that page?
            same_page = [(k, v) for k, v in existing.items() if k[1] == p["pageIndex"] and k[0] == r["type"]]
            examples.append({
                "mine_sig": s, "mine_nrects": len(p["rects"]), "mine_rect0": [round(v, 2) for v in p["rects"][0]],
                "db_same_page": [(k, len(v["rects"]), [round(q, 2) for q in v["rects"][0]]) for k, v in same_page[:3]],
                "mendeley_type": (x["ann"].get("_custom") or {}).get("type"),
            })
    doc.close()
    if checked > 600:
        break

print("verificate (doar PDF-uri 'complete'):", checked)
print("nepotrivite dupa type:", dict(miss_type))
print("nepotrivite dupa nr. rects:", dict(miss_nrects))
for e in examples:
    print("\n---")
    print(" mendeley_type:", e["mendeley_type"], "| mine nrects:", e["mine_nrects"], "rect0:", e["mine_rect0"])
    print(" DB pe aceeasi pagina/type:", e["db_same_page"])
