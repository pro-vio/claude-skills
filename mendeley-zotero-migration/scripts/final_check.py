import sqlite3, sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot
c=sqlite3.connect(f"file:{os.path.join(zot.ZDIR,'zotero.sqlite')}?mode=ro",uri=True).cursor()
NT="itemID NOT IN (SELECT itemID FROM deletedItems)"
print("iteme       :", c.execute(f"SELECT COUNT(*) FROM items i JOIN itemTypes t ON t.itemTypeID=i.itemTypeID WHERE t.typeName NOT IN ('attachment','note','annotation') AND i.{NT}").fetchone()[0], "(2372 - 13 = 2359)")
print("PDF         :", c.execute("SELECT COUNT(*) FROM itemAttachments WHERE contentType='application/pdf'").fetchone()[0])
print("adnotari    :", c.execute("SELECT COUNT(*) FROM itemAnnotations").fetchone()[0])
print("dc:replaces :", c.execute("SELECT COUNT(*) FROM itemRelations WHERE predicateID=1").fetchone()[0], "(287 + 13 = 300)")
print("\nintegritate:")
for l,q in [("adnotari orfane","SELECT COUNT(*) FROM itemAnnotations WHERE itemID NOT IN (SELECT itemID FROM items) OR parentItemID NOT IN (SELECT itemID FROM items)"),
            ("note orfane","SELECT COUNT(*) FROM itemNotes WHERE parentItemID IS NOT NULL AND parentItemID NOT IN (SELECT itemID FROM items)"),
            ("itemData orfane","SELECT COUNT(*) FROM itemData WHERE itemID NOT IN (SELECT itemID FROM items)"),
            ("atasamente orfane","SELECT COUNT(*) FROM itemAttachments WHERE parentItemID IS NOT NULL AND parentItemID NOT IN (SELECT itemID FROM items)"),
            ("collectionItems orfane","SELECT COUNT(*) FROM collectionItems WHERE itemID NOT IN (SELECT itemID FROM items)")]:
    print(f"  {l}: {c.execute(q).fetchone()[0]}")
# verify the merged masters kept their annotations
for m,label in [(15,"IAD Framework"),(1264,"Unraveled Practices"),(1236,"Policy Incentives"),(1160,"Labour market")]:
    p=[r[0] for r in c.execute("SELECT itemID FROM itemAttachments WHERE parentItemID=?",(m,)).fetchall()]
    n=0
    if p:
        q=",".join("?"*len(p)); n=c.execute(f"SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID IN ({q})",p).fetchone()[0]
    print(f"  master {m} ({label}): {len(p)} atasamente, {n} adnotari")
