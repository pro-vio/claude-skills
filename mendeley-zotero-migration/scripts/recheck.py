import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
p=r"C:\Users\Viorel Proteasa\Zotero\zotero.sqlite"
c=sqlite3.connect(f"file:{p}?mode=ro",uri=True).cursor()   # NO immutable — live DB
NT="itemID NOT IN (SELECT itemID FROM deletedItems)"
print("iteme:", c.execute(f"SELECT COUNT(*) FROM items i JOIN itemTypes it ON it.itemTypeID=i.itemTypeID WHERE it.typeName NOT IN ('attachment','note','annotation') AND i.{NT}").fetchone()[0])
print("colecții:", c.execute("SELECT COUNT(*) FROM collections").fetchone()[0])
print("PDF:", c.execute("SELECT COUNT(*) FROM itemAttachments WHERE contentType='application/pdf'").fetchone()[0])
print("adnotări:", c.execute("SELECT COUNT(*) FROM itemAnnotations").fetchone()[0])
# what are the collections? show newest ones
rows=c.execute("SELECT collectionID, collectionName, parentCollectionID FROM collections ORDER BY collectionID DESC LIMIT 15").fetchall()
print("\nultimele 15 colecții (după ID):")
for cid,nm,par in rows: print(f"  [{cid}] {nm}  (parent {par})")
