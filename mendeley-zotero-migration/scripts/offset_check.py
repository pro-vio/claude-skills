# -*- coding: utf-8 -*-
"""Measure the systematic offset between my conversion and Zotero's import,
separately for highlights (type 1) and notes (type 2), across many PDFs."""
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

dx = Counter(); dy = Counter(); exact = Counter(); checked = 0
for h, lst in amap.items():
    atts = h2att.get(h)
    if not atts or any(x["author"] for x in lst):
        continue
    att = atts[0]
    n = c.execute("SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID=?", (att,)).fetchone()[0]
    if n != len(lst) or n == 0:
        continue          # only PDFs where the import brought exactly this set
    row = c.execute("SELECT i.key, ia.path FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID WHERE ia.itemID=?", (att,)).fetchone()
    fp = os.path.join(ZSTOR, row[0], row[1][len("storage:"):])
    if not os.path.exists(fp):
        continue
    doc = fitz.open(fp)
    db = []
    for typ, pos in c.execute("SELECT type,position FROM itemAnnotations WHERE parentItemID=?", (att,)).fetchall():
        p = json.loads(pos)
        db.append((typ, p["pageIndex"], p.get("rects") or []))
    for x in lst:
        r = annconv.convert(x["ann"], doc)
        if not r:
            continue
        p = json.loads(r["position"])
        pi = p["pageIndex"]; rects = p.get("rects") or []
        if not rects:
            continue
        # find a DB annotation on the same page + type with the same rect COUNT
        cands = [d for d in db if d[0] == r["type"] and d[1] == pi and len(d[2]) == len(rects)]
        if not cands:
            continue
        # nearest by first rect
        best = min(cands, key=lambda d: abs(d[2][0][0] - rects[0][0]) + abs(d[2][0][1] - rects[0][1]))
        ddx = round(rects[0][0] - best[2][0][0], 2)
        ddy = round(rects[0][1] - best[2][0][1], 2)
        dx[(r["type"], ddx)] += 1
        dy[(r["type"], ddy)] += 1
        exact[(r["type"], ddx == 0 and ddy == 0)] += 1
        checked += 1
    doc.close()
    if checked > 400:
        break

print("verificate:", checked)
print("\ndx cele mai frecvente (type, dx):", dx.most_common(6))
print("dy cele mai frecvente (type, dy):", dy.most_common(6))
print("\npotrivire exacta:", dict(exact))
