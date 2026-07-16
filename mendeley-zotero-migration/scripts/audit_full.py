# -*- coding: utf-8 -*-
"""Full health check of the library after the migration + import + dedup."""
import sqlite3, sys, os, json, hashlib, re
from collections import defaultdict, Counter
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
ZSTOR = os.path.join(zot.ZDIR, "storage")
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True).cursor()
NT = "itemID NOT IN (SELECT itemID FROM deletedItems)"
BIB = "it.typeName NOT IN ('attachment','note','annotation')"

print("=" * 78)
print("A. INTEGRITATE REFERENTIALA")
for label, q in [
    ("itemData orfane", "SELECT COUNT(*) FROM itemData WHERE itemID NOT IN (SELECT itemID FROM items)"),
    ("itemCreators orfane", "SELECT COUNT(*) FROM itemCreators WHERE itemID NOT IN (SELECT itemID FROM items)"),
    ("itemTags orfane", "SELECT COUNT(*) FROM itemTags WHERE itemID NOT IN (SELECT itemID FROM items)"),
    ("itemNotes orfane (item)", "SELECT COUNT(*) FROM itemNotes WHERE itemID NOT IN (SELECT itemID FROM items)"),
    ("itemNotes cu parinte lipsa", "SELECT COUNT(*) FROM itemNotes WHERE parentItemID IS NOT NULL AND parentItemID NOT IN (SELECT itemID FROM items)"),
    ("itemAttachments orfane", "SELECT COUNT(*) FROM itemAttachments WHERE itemID NOT IN (SELECT itemID FROM items)"),
    ("atasamente cu parinte lipsa", "SELECT COUNT(*) FROM itemAttachments WHERE parentItemID IS NOT NULL AND parentItemID NOT IN (SELECT itemID FROM items)"),
    ("adnotari orfane", "SELECT COUNT(*) FROM itemAnnotations WHERE itemID NOT IN (SELECT itemID FROM items)"),
    ("adnotari cu parinte lipsa", "SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID NOT IN (SELECT itemID FROM items)"),
    ("collectionItems orfane (item)", "SELECT COUNT(*) FROM collectionItems WHERE itemID NOT IN (SELECT itemID FROM items)"),
    ("collectionItems orfane (colectie)", "SELECT COUNT(*) FROM collectionItems WHERE collectionID NOT IN (SELECT collectionID FROM collections)"),
    ("colectii cu parinte lipsa", "SELECT COUNT(*) FROM collections WHERE parentCollectionID IS NOT NULL AND parentCollectionID NOT IN (SELECT collectionID FROM collections)"),
    ("itemRelations orfane", "SELECT COUNT(*) FROM itemRelations WHERE itemID NOT IN (SELECT itemID FROM items)"),
    ("adnotari cu position gol", "SELECT COUNT(*) FROM itemAnnotations WHERE position IS NULL OR position=''"),
    ("iteme fara tip valid", "SELECT COUNT(*) FROM items WHERE itemTypeID NOT IN (SELECT itemTypeID FROM itemTypes)"),
]:
    n = c.execute(q).fetchone()[0]
    print(f"  {'OK ' if n == 0 else '!! '}{label}: {n}")

print("\n" + "=" * 78)
print("B. FISIERE PE DISC")
rows = c.execute(f"""SELECT ia.itemID, i.key, ia.path, ia.parentItemID, ia.contentType
                     FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID
                     WHERE ia.path LIKE 'storage:%' AND i.{NT}""").fetchall()
missing = []
for aid, key, path, parent, ct in rows:
    fp = os.path.join(ZSTOR, key, path[len("storage:"):])
    if not os.path.exists(fp):
        missing.append((aid, parent, path, ct))
print(f"  atasamente stocate: {len(rows)} | FISIER LIPSA pe disc: {len(missing)}")
mis_ann = 0
for aid, parent, path, ct in missing:
    mis_ann += c.execute("SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID=?", (aid,)).fetchone()[0]
print(f"  dintre care cu adnotari: {mis_ann} adnotari ar fi nefolosibile")
# storage folders with no attachment row
keys_db = {r[0] for r in c.execute("SELECT i.key FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID WHERE ia.path LIKE 'storage:%'").fetchall()}
on_disk = {d for d in os.listdir(ZSTOR) if os.path.isdir(os.path.join(ZSTOR, d))}
orphan_dirs = on_disk - keys_db
print(f"  foldere storage fara atasament in DB: {len(orphan_dirs)}")

print("\n" + "=" * 78)
print("C. CALITATEA METADATELOR")
n = c.execute(f"""SELECT COUNT(*) FROM items i JOIN itemTypes it ON it.itemTypeID=i.itemTypeID
    WHERE {BIB} AND i.{NT} AND NOT EXISTS(SELECT 1 FROM itemData d JOIN fields f ON f.fieldID=d.fieldID
    WHERE d.itemID=i.itemID AND f.fieldName IN ('title','nameOfAct','caseName'))""").fetchone()[0]
print(f"  iteme FARA titlu: {n}")
n = c.execute(f"""SELECT COUNT(*) FROM items i JOIN itemTypes it ON it.itemTypeID=i.itemTypeID
    WHERE {BIB} AND i.{NT} AND NOT EXISTS(SELECT 1 FROM itemCreators ic WHERE ic.itemID=i.itemID)""").fetchone()[0]
print(f"  iteme FARA autor: {n}")
junk = c.execute("""SELECT d.itemID, v.value FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
    JOIN fields f ON f.fieldID=d.fieldID WHERE f.fieldName='title'
    AND (v.value LIKE '%No Title%' OR v.value LIKE '%済無%')""").fetchall()
print(f"  titluri-placeholder ramase: {len(junk)} {[j[0] for j in junk][:6]}")
# the notorious junk DOI
bad = c.execute("""SELECT d.itemID FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
    JOIN fields f ON f.fieldID=d.fieldID WHERE f.fieldName='DOI'
    AND LOWER(v.value) LIKE '%10.1017/cbo9781107415324.004%'""").fetchall()
print(f"  iteme cu DOI-ul fals Mendeley (10.1017/CBO9781107415324.004): {len(bad)}")
for (iid,) in bad[:20]:
    t = c.execute("""SELECT v.value FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
        JOIN fields f ON f.fieldID=d.fieldID WHERE d.itemID=? AND f.fieldName='title'""", (iid,)).fetchone()
    au = c.execute("""SELECT cr.lastName FROM itemCreators ic JOIN creators cr ON cr.creatorID=ic.creatorID
        WHERE ic.itemID=? ORDER BY ic.orderIndex LIMIT 1""", (iid,)).fetchone()
    print(f"      {iid}: {(au[0] if au else '-')} — {(t[0] if t else '?')[:58]}")

print("\n" + "=" * 78)
print("D. DUPLICATE RAMASE")
# same PDF content attached to DIFFERENT items
h = defaultdict(set)
for aid, key, path, parent, ct in rows:
    if ct != "application/pdf" or parent is None:
        continue
    fp = os.path.join(ZSTOR, key, path[len("storage:"):])
    if not os.path.exists(fp):
        continue
    try:
        d = hashlib.sha1()
        with open(fp, "rb") as f:
            for ch in iter(lambda: f.read(1048576), b""):
                d.update(ch)
        h[d.hexdigest()].add(parent)
    except Exception:
        pass
cross = {k: v for k, v in h.items() if len(v) > 1}
print(f"  acelasi PDF pe ITEME DIFERITE: {len(cross)} continuturi, {sum(len(v) for v in cross.values())} iteme")
print(f"  (dedup-ul a colapsat doar in interiorul aceluiasi item)")

print("\n" + "=" * 78)
print("E. COS DE GUNOI")
print(f"  iteme in trash: {c.execute('SELECT COUNT(*) FROM deletedItems').fetchone()[0]}")
json.dump({"cross": {k: sorted(v) for k, v in cross.items()}, "missing_files": missing,
           "junk_doi": [b[0] for b in bad]}, open("extract/audit.json", "w"))
