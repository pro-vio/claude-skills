# -*- coding: utf-8 -*-
"""Why don't my converted annotations match the imported ones? Compare, for a single
PDF whose annotations are all the user's own and were brought by the import."""
import sqlite3, sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot, annconv, fitz

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
ZSTOR = os.path.join(zot.ZDIR, "storage")
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True).cursor()
amap = json.load(open("extract/ann_by_filehash.json", encoding="utf-8"))
h2att = json.load(open("extract/zotero_sha1_to_attach.json", encoding="utf-8"))

target = None
for h, lst in amap.items():
    atts = h2att.get(h)
    if not atts or any(x["author"] for x in lst) or not (5 <= len(lst) <= 20):
        continue
    n = c.execute("SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID=?", (atts[0],)).fetchone()[0]
    if n == len(lst):          # same count -> import brought exactly these
        target = h
        break
print("filehash:", target, "| Mendeley:", len(amap[target]))
att = h2att[target][0]
key, path = c.execute("SELECT i.key, ia.path FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID WHERE ia.itemID=?", (att,)).fetchone()
doc = fitz.open(os.path.join(ZSTOR, key, path[len("storage:"):]))

db = []
for typ, pos in c.execute("SELECT type,position FROM itemAnnotations WHERE parentItemID=?", (att,)).fetchall():
    p = json.loads(pos)
    db.append((typ, p["pageIndex"], p.get("rects") or []))
mine = []
for x in amap[target]:
    r = annconv.convert(x["ann"], doc)
    if r:
        p = json.loads(r["position"])
        mine.append((r["type"], p["pageIndex"], p.get("rects") or []))
doc.close()

print(f"\nDB: {len(db)} | conversia mea: {len(mine)}")
print("\n--- pe pagini ---")
print("DB pageIndex   :", sorted(x[1] for x in db))
print("ale mele       :", sorted(x[1] for x in mine))
print("\n--- primele 3 din fiecare, aceeasi pagina daca se poate ---")
for pi in sorted({x[1] for x in db})[:3]:
    d = [x for x in db if x[1] == pi]
    m = [x for x in mine if x[1] == pi]
    print(f"\npagina index {pi}: DB {len(d)} vs ale mele {len(m)}")
    for x in d[:2]:
        print(f"   DB  type={x[0]} nrects={len(x[2])} rect0={[round(v,2) for v in x[2][0]] if x[2] else None}")
    for x in m[:2]:
        print(f"   EU  type={x[0]} nrects={len(x[2])} rect0={[round(v,2) for v in x[2][0]] if x[2] else None}")
