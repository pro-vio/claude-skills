# -*- coding: utf-8 -*-
import sqlite3, sys, os, json
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot
DB = os.path.join(zot.ZDIR, "zotero.sqlite")
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True).cursor()
NT = "itemID NOT IN (SELECT itemID FROM deletedItems)"
print("=== STARE DUPA CURATARE ===")
print("iteme top-level:", c.execute(f"SELECT COUNT(*) FROM items i JOIN itemTypes t ON t.itemTypeID=i.itemTypeID WHERE t.typeName NOT IN ('attachment','note','annotation') AND i.{NT}").fetchone()[0], "(asteptat 461+2198 = 2659)")
print("colectii:", c.execute("SELECT COUNT(*) FROM collections").fetchone()[0], "(asteptat 14+113 = 127)")
print("atasamente PDF:", c.execute("SELECT COUNT(*) FROM itemAttachments WHERE contentType='application/pdf'").fetchone()[0])
print("adnotari:", c.execute("SELECT COUNT(*) FROM itemAnnotations").fetchone()[0], "(asteptat 140+3802 = 3942)")
print("note-copil:", c.execute("SELECT COUNT(*) FROM itemNotes WHERE parentItemID IS NOT NULL").fetchone()[0])
print("\nadnotari pe zi:")
for d, n in sorted(Counter(r[0][:10] for r in c.execute("SELECT i.dateAdded FROM itemAnnotations an JOIN items i ON i.itemID=an.itemID").fetchall()).items()):
    print(f"  {d}: {n}")
print("\n=== INTEGRITATE ===")
for label, q in [
    ("itemData orfane", "SELECT COUNT(*) FROM itemData WHERE itemID NOT IN (SELECT itemID FROM items)"),
    ("itemAttachments orfane", "SELECT COUNT(*) FROM itemAttachments WHERE itemID NOT IN (SELECT itemID FROM items)"),
    ("adnotari orfane", "SELECT COUNT(*) FROM itemAnnotations WHERE itemID NOT IN (SELECT itemID FROM items) OR parentItemID NOT IN (SELECT itemID FROM items)"),
    ("collectionItems orfane", "SELECT COUNT(*) FROM collectionItems WHERE itemID NOT IN (SELECT itemID FROM items) OR collectionID NOT IN (SELECT collectionID FROM collections)"),
    ("itemNotes orfane", "SELECT COUNT(*) FROM itemNotes WHERE itemID NOT IN (SELECT itemID FROM items)"),
    ("colectii cu parinte inexistent", "SELECT COUNT(*) FROM collections WHERE parentCollectionID IS NOT NULL AND parentCollectionID NOT IN (SELECT collectionID FROM collections)"),
]:
    print(f"  {label}: {c.execute(q).fetchone()[0]}")
print("\ncolectii radacina:")
for cid, nm in c.execute("SELECT collectionID,collectionName FROM collections WHERE parentCollectionID IS NULL ORDER BY collectionID").fetchall():
    n = c.execute("SELECT COUNT(*) FROM collectionItems WHERE collectionID=?", (cid,)).fetchone()[0]
    print(f"  [{cid}] {nm} ({n} iteme)")
