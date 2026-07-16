# -*- coding: utf-8 -*-
"""Look at what the audit flagged before touching anything: the 2 placeholder-title
items (last time such a record hid a 175-page dissertation), the 16 items carrying
Mendeley's junk DOI, and a sample of the same-PDF-on-different-items pairs."""
import sqlite3, sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot, fitz

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
ZSTOR = os.path.join(zot.ZDIR, "storage")
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True).cursor()
audit = json.load(open("extract/audit.json", encoding="utf-8"))

def pdf_head(iid, n=110):
    r = c.execute("""SELECT i.key, ia.path FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID
        WHERE ia.parentItemID=? AND ia.contentType='application/pdf' LIMIT 1""", (iid,)).fetchone()
    if not r: return None, None
    fp = os.path.join(ZSTOR, r[0], r[1][len("storage:"):])
    if not os.path.exists(fp): return None, None
    d = fitz.open(fp); pg = d.page_count; t = d[0].get_text().strip().replace("\n", " ")[:n]; d.close()
    return pg, t
def title(iid):
    r = c.execute("""SELECT v.value FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
        JOIN fields f ON f.fieldID=d.fieldID WHERE d.itemID=? AND f.fieldName IN ('title','nameOfAct') LIMIT 1""", (iid,)).fetchone()
    return r[0] if r else "(fara titlu)"
def au(iid):
    r = c.execute("""SELECT cr.lastName FROM itemCreators ic JOIN creators cr ON cr.creatorID=ic.creatorID
        WHERE ic.itemID=? ORDER BY ic.orderIndex LIMIT 1""", (iid,)).fetchone()
    return r[0] if r else "-"

print("=== 1. cele 2 titluri-placeholder ===")
for iid in (9106, 10801):
    ty = c.execute("SELECT it.typeName FROM items i JOIN itemTypes it ON it.itemTypeID=i.itemTypeID WHERE i.itemID=?", (iid,)).fetchone()
    if not ty: print(f"  item {iid}: nu exista"); continue
    pg, t = pdf_head(iid, 260)
    cols = [r[0] for r in c.execute("""SELECT col.collectionName FROM collectionItems ci
        JOIN collections col ON col.collectionID=ci.collectionID WHERE ci.itemID=?""", (iid,)).fetchall()]
    ann = 0
    ats = [r[0] for r in c.execute("SELECT itemID FROM itemAttachments WHERE parentItemID=?", (iid,)).fetchall()]
    if ats:
        q = ",".join("?" * len(ats))
        ann = c.execute(f"SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID IN ({q})", ats).fetchone()[0]
    print(f"\n  item {iid} [{ty[0]}] autor={au(iid)!r} adnotari={ann} colectii={cols}")
    print(f"     titlu DB : {title(iid)[:70]}")
    print(f"     PDF ({pg} pag.): {t}")

print("\n\n=== 2. cele 16 iteme cu DOI-ul fals — au si DOI corect propriu? ===")
for iid in audit["junk_doi"]:
    isbn = c.execute("""SELECT v.value FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
        JOIN fields f ON f.fieldID=d.fieldID WHERE d.itemID=? AND f.fieldName='ISBN'""", (iid,)).fetchone()
    print(f"  {iid}: {au(iid)} — {title(iid)[:52]} | ISBN={isbn[0][:20] if isbn else '-'}")

print("\n\n=== 3. acelasi PDF pe ITEME DIFERITE — primele 8 perechi ===")
for i, (h, ids) in enumerate(list(audit["cross"].items())[:8], 1):
    print(f"\n  [{i}] {len(ids)} iteme:")
    for iid in ids:
        ty = c.execute("SELECT it.typeName FROM items i JOIN itemTypes it ON it.itemTypeID=i.itemTypeID WHERE i.itemID=?", (iid,)).fetchone()
        if not ty: continue
        print(f"      {iid} [{ty[0]}] {au(iid)} — {title(iid)[:58]}")
