# -*- coding: utf-8 -*-
import sqlite3, sys, os
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot
DB = os.path.join(zot.ZDIR, "zotero.sqlite")
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True).cursor()
NT = "itemID NOT IN (SELECT itemID FROM deletedItems)"
print("=== STARE FINALA ===")
print("iteme top-level:", c.execute(f"SELECT COUNT(*) FROM items i JOIN itemTypes t ON t.itemTypeID=i.itemTypeID WHERE t.typeName NOT IN ('attachment','note','annotation') AND i.{NT}").fetchone()[0])
print("colectii:", c.execute("SELECT COUNT(*) FROM collections").fetchone()[0])
print("atasamente PDF:", c.execute("SELECT COUNT(*) FROM itemAttachments WHERE contentType='application/pdf'").fetchone()[0])
print("adnotari:", c.execute("SELECT COUNT(*) FROM itemAnnotations").fetchone()[0], "(3942 + 493 = 4435 asteptat)")
print("  cu authorName:", c.execute("SELECT COUNT(*) FROM itemAnnotations WHERE authorName IS NOT NULL AND authorName<>''").fetchone()[0])
print("\ntop authorName:")
for a, n in c.execute("SELECT authorName, COUNT(*) FROM itemAnnotations WHERE authorName IS NOT NULL AND authorName<>'' GROUP BY authorName ORDER BY COUNT(*) DESC LIMIT 8").fetchall():
    print(f"  {n:4}  {a}")
print("\n=== INTEGRITATE ===")
for label, q in [
    ("adnotari orfane", "SELECT COUNT(*) FROM itemAnnotations WHERE itemID NOT IN (SELECT itemID FROM items) OR parentItemID NOT IN (SELECT itemID FROM items)"),
    ("adnotari cu position gol", "SELECT COUNT(*) FROM itemAnnotations WHERE position IS NULL OR position=''"),
    ("itemData orfane", "SELECT COUNT(*) FROM itemData WHERE itemID NOT IN (SELECT itemID FROM items)"),
    ("collectionItems orfane", "SELECT COUNT(*) FROM collectionItems WHERE itemID NOT IN (SELECT itemID FROM items)"),
]:
    print(f"  {label}: {c.execute(q).fetchone()[0]}")
# an item to eyeball: attachment with both mine and a student's
row = c.execute("""SELECT an.parentItemID, COUNT(*) tot,
                     SUM(CASE WHEN an.authorName IS NOT NULL AND an.authorName<>'' THEN 1 ELSE 0 END) stud
                   FROM itemAnnotations an GROUP BY an.parentItemID
                   HAVING stud > 0 AND tot > stud ORDER BY tot DESC LIMIT 3""").fetchall()
print("\n=== atasamente cu AMBELE (de verificat vizual) ===")
for att, tot, stud in row:
    p = c.execute("SELECT parentItemID FROM itemAttachments WHERE itemID=?", (att,)).fetchone()
    t = c.execute("""SELECT v.value FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
                     JOIN fields f ON f.fieldID=d.fieldID WHERE d.itemID=? AND f.fieldName IN ('title','nameOfAct') LIMIT 1""",
                  (p[0] if p and p[0] else att,)).fetchone()
    who = [r[0] for r in c.execute("SELECT DISTINCT authorName FROM itemAnnotations WHERE parentItemID=? AND authorName IS NOT NULL AND authorName<>''", (att,)).fetchall()]
    print(f"  {tot} adnotari ({tot-stud} ale tale + {stud} studenti: {', '.join(who)})")
    print(f"     -> {(t[0] if t else '?')[:70]}")
