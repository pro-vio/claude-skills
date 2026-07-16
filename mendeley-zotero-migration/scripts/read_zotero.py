import sys, sqlite3, json
sys.stdout.reconfigure(encoding="utf-8")
con = sqlite3.connect("extract/zotero_ro.sqlite")
c = con.cursor()

# field name -> fieldID
fields = dict(c.execute("SELECT fieldName, fieldID FROM fields").fetchall())
# item types
itypes = dict(c.execute("SELECT itemTypeID, typeName FROM itemTypes").fetchall())

# top-level, non-deleted, non-attachment/note items
c.execute("""
SELECT i.itemID, i.key, it.typeName
FROM items i
JOIN itemTypes it ON it.itemTypeID = i.itemTypeID
WHERE i.itemID NOT IN (SELECT itemID FROM deletedItems)
  AND i.itemID NOT IN (SELECT itemID FROM itemAttachments WHERE parentItemID IS NOT NULL)
  AND i.itemID NOT IN (SELECT itemID FROM itemNotes WHERE parentItemID IS NOT NULL)
  AND it.typeName NOT IN ('attachment','note','annotation')
""")
rows = c.fetchall()
from collections import Counter
print("Zotero top-level items:", len(rows))
print("types:", Counter(r[2] for r in rows).most_common(12))
con.close()
