# -*- coding: utf-8 -*-
import sqlite3, sys, os, json, hashlib
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot
DB = os.path.join(zot.ZDIR, "zotero.sqlite")
ZSTOR = os.path.join(zot.ZDIR, "storage")
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True).cursor()
NT = "itemID NOT IN (SELECT itemID FROM deletedItems)"
print("=== STARE FINALA ===")
print("iteme top-level :", c.execute(f"SELECT COUNT(*) FROM items i JOIN itemTypes t ON t.itemTypeID=i.itemTypeID WHERE t.typeName NOT IN ('attachment','note','annotation') AND i.{NT}").fetchone()[0], "(2658 -> 2372 asteptat)")
print("colectii        :", c.execute("SELECT COUNT(*) FROM collections").fetchone()[0])
print("atasamente PDF  :", c.execute("SELECT COUNT(*) FROM itemAttachments WHERE contentType='application/pdf'").fetchone()[0], "(2476 - 265 = 2211 asteptat)")
print("adnotari        :", c.execute("SELECT COUNT(*) FROM itemAnnotations").fetchone()[0], "(4435 - 10 = 4425 asteptat)")
print("  cu authorName :", c.execute("SELECT COUNT(*) FROM itemAnnotations WHERE authorName IS NOT NULL AND authorName<>''").fetchone()[0])
print("note-copil      :", c.execute("SELECT COUNT(*) FROM itemNotes WHERE parentItemID IS NOT NULL").fetchone()[0])
print("\n=== INTEGRITATE ===")
for label, q in [
    ("itemData orfane", "SELECT COUNT(*) FROM itemData WHERE itemID NOT IN (SELECT itemID FROM items)"),
    ("itemAttachments orfane", "SELECT COUNT(*) FROM itemAttachments WHERE itemID NOT IN (SELECT itemID FROM items)"),
    ("atasamente cu parinte inexistent", "SELECT COUNT(*) FROM itemAttachments WHERE parentItemID IS NOT NULL AND parentItemID NOT IN (SELECT itemID FROM items)"),
    ("adnotari orfane", "SELECT COUNT(*) FROM itemAnnotations WHERE itemID NOT IN (SELECT itemID FROM items) OR parentItemID NOT IN (SELECT itemID FROM items)"),
    ("note orfane", "SELECT COUNT(*) FROM itemNotes WHERE parentItemID IS NOT NULL AND parentItemID NOT IN (SELECT itemID FROM items)"),
    ("collectionItems orfane", "SELECT COUNT(*) FROM collectionItems WHERE itemID NOT IN (SELECT itemID FROM items) OR collectionID NOT IN (SELECT collectionID FROM collections)"),
    ("itemCreators orfane", "SELECT COUNT(*) FROM itemCreators WHERE itemID NOT IN (SELECT itemID FROM items)"),
    ("itemTags orfane", "SELECT COUNT(*) FROM itemTags WHERE itemID NOT IN (SELECT itemID FROM items)"),
]:
    print(f"  {label}: {c.execute(q).fetchone()[0]}")

# did the user's original items survive? (citations depend on their keys)
orig = {x["zid"] for x in json.load(open("extract/zotero_ids.json", encoding="utf-8"))}
q = ",".join("?" * len(orig))
alive = c.execute(f"SELECT COUNT(*) FROM items WHERE itemID IN ({q})", list(orig)).fetchone()[0]
print(f"\nitemele tale ORIGINALE inca prezente: {alive} / {len(orig)}  (citarile depind de ele)")

# remaining same-content duplicates within one item
rows = c.execute("""SELECT ia.parentItemID, i.key, ia.path FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID
                    WHERE ia.contentType='application/pdf' AND ia.parentItemID IS NOT NULL AND ia.path LIKE 'storage:%'""").fetchall()
def sha1(fp):
    h = hashlib.sha1()
    with open(fp, "rb") as f:
        for ch in iter(lambda: f.read(1048576), b""): h.update(ch)
    return h.hexdigest()
per = defaultdict(list)
for parent, key, path in rows:
    fp = os.path.join(ZSTOR, key, path[len("storage:"):])
    if os.path.exists(fp):
        try: per[parent].append(sha1(fp))
        except Exception: pass
left = sum(1 for p, hs in per.items() if len(hs) != len(set(hs)))
print(f"iteme cu PDF-uri duplicate ramase (ar trebui 0): {left}")
