import sqlite3, sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot
c=sqlite3.connect(f"file:{os.path.join(zot.ZDIR,'zotero.sqlite')}?mode=ro",uri=True).cursor()
print("item 1142 — autor acum:")
for ct,ln,fn in c.execute("""SELECT ct.creatorType, cr.lastName, cr.firstName FROM itemCreators ic
    JOIN creators cr ON cr.creatorID=ic.creatorID JOIN creatorTypes ct ON ct.creatorTypeID=ic.creatorTypeID
    WHERE ic.itemID=1142 ORDER BY ic.orderIndex""").fetchall():
    print(f"   {ct}: {ln}, {fn}")
print("\nitem 10387 (sters):", "prezent!" if c.execute("SELECT 1 FROM items WHERE itemID=10387").fetchone() else "sters OK")
print("item 10284 (Stinebrickner) pastrat:", "DA" if c.execute("SELECT 1 FROM items WHERE itemID=10284").fetchone() else "LIPSA!")
print("item 10393 (teza See) intact:", "DA" if c.execute("SELECT 1 FROM items WHERE itemID=10393").fetchone() else "LIPSA!")
NT="itemID NOT IN (SELECT itemID FROM deletedItems)"
print("\niteme:", c.execute(f"SELECT COUNT(*) FROM items i JOIN itemTypes t ON t.itemTypeID=i.itemTypeID WHERE t.typeName NOT IN ('attachment','note','annotation') AND i.{NT}").fetchone()[0])
print("adnotari:", c.execute("SELECT COUNT(*) FROM itemAnnotations").fetchone()[0])
for l,q in [("adnotari orfane","SELECT COUNT(*) FROM itemAnnotations WHERE itemID NOT IN (SELECT itemID FROM items) OR parentItemID NOT IN (SELECT itemID FROM items)"),
            ("note orfane","SELECT COUNT(*) FROM itemNotes WHERE parentItemID IS NOT NULL AND parentItemID NOT IN (SELECT itemID FROM items)"),
            ("itemCreators orfane","SELECT COUNT(*) FROM itemCreators WHERE itemID NOT IN (SELECT itemID FROM items)"),
            ("itemData orfane","SELECT COUNT(*) FROM itemData WHERE itemID NOT IN (SELECT itemID FROM items)")]:
    print(f"  {l}: {c.execute(q).fetchone()[0]}")
