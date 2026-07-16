# -*- coding: utf-8 -*-
"""Calibrate: for a PDF whose OWN annotations the import brought, compare Zotero's
stored representation against my conversion of the same Mendeley source, so the
dedup signature is reliable before inserting the students' annotations."""
import sqlite3, sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot, annconv, fitz

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
ZSTOR = os.path.join(zot.ZDIR, "storage")
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True).cursor()
amap = json.load(open("extract/ann_by_filehash.json", encoding="utf-8"))
h2att = json.load(open("extract/zotero_sha1_to_attach.json", encoding="utf-8"))

# pick a filehash whose annotations are all mine and present in DB
target = None
for h, lst in amap.items():
    atts = h2att.get(h)
    if not atts or any(x["author"] for x in lst) or len(lst) < 4:
        continue
    q = ",".join("?" * len(atts))
    n = c.execute(f"SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID IN ({q})", atts).fetchone()[0]
    if n >= 4:
        target = h
        break
print("filehash:", target)
atts = h2att[target]
att = atts[0]
key, path = c.execute("SELECT i.key, ia.path FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID WHERE ia.itemID=?", (att,)).fetchone()
fp = os.path.join(ZSTOR, key, path[len("storage:"):])
doc = fitz.open(fp)

db_rows = c.execute("SELECT type,text,comment,color,pageLabel,position FROM itemAnnotations WHERE parentItemID=? ORDER BY sortIndex", (att,)).fetchall()
print(f"\nDB are {len(db_rows)} adnotari; Mendeley are {len(amap[target])}")
print("\n--- ZOTERO (import) ---")
for r in db_rows[:3]:
    pos = json.loads(r[5])
    print(f"  type={r[0]} page={r[4]} pageIndex={pos['pageIndex']} color={r[3]}")
    print(f"    rects={pos['rects'][:2]}")
    print(f"    text={(r[1] or '')[:70]!r}")

print("\n--- CONVERSIA MEA din aceeasi sursa Mendeley ---")
for x in amap[target][:3]:
    r = annconv.convert(x["ann"], doc)
    if not r:
        continue
    pos = json.loads(r["position"])
    print(f"  type={r['type']} page={r['pageLabel']} pageIndex={pos['pageIndex']} color={r['color']}")
    print(f"    rects={pos['rects'][:2]}")
    print(f"    text={(r['text'] or '')[:70]!r}")
doc.close()
