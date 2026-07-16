import sqlite3, sys
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
p=r"C:\Users\Viorel Proteasa\Zotero\zotero.sqlite"
c=sqlite3.connect(f"file:{p}?mode=ro&immutable=1",uri=True).cursor()
NT="itemID NOT IN (SELECT itemID FROM deletedItems)"
print("=== DUPĂ IMPORT ===")
print("iteme top-level:", c.execute(f"SELECT COUNT(*) FROM items i JOIN itemTypes t ON t.itemTypeID=i.itemTypeID WHERE t.typeName NOT IN ('attachment','note','annotation') AND i.{NT}").fetchone()[0])
print("colecții:", c.execute("SELECT COUNT(*) FROM collections").fetchone()[0])
print("atașamente PDF:", c.execute("SELECT COUNT(*) FROM itemAttachments WHERE contentType='application/pdf'").fetchone()[0])
print("adnotări:", c.execute("SELECT COUNT(*) FROM itemAnnotations").fetchone()[0])
print("  cu authorName:", c.execute("SELECT COUNT(*) FROM itemAnnotations WHERE authorName IS NOT NULL AND authorName<>''").fetchone()[0])
print("note:", c.execute("SELECT COUNT(*) FROM itemNotes").fetchone()[0])
print("biblioteci:", c.execute("SELECT libraryID, type FROM libraries").fetchall())
# top-level collections
print("\n=== colecții rădăcină ===")
for cid,nm in c.execute("SELECT collectionID,collectionName FROM collections WHERE parentCollectionID IS NULL ORDER BY collectionID").fetchall():
    n=c.execute("SELECT COUNT(*) FROM collectionItems WHERE collectionID=?",(cid,)).fetchone()[0]
    kids=c.execute("SELECT COUNT(*) FROM collections WHERE parentCollectionID=?",(cid,)).fetchone()[0]
    print(f"  [{cid}] {nm}  ({n} iteme, {kids} subcolecții)")
