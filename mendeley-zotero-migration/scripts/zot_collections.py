import sys, sqlite3, json
sys.stdout.reconfigure(encoding="utf-8")
con = sqlite3.connect("extract/zotero_ro.sqlite")
c = con.cursor()
rows = c.execute("SELECT collectionID, key, collectionName, parentCollectionID FROM collections").fetchall()
print("Existing Zotero collections:", len(rows))
byid = {r[0]: r for r in rows}
def path(cid):
    parts=[]; seen=set()
    while cid and cid not in seen:
        seen.add(cid); r=byid.get(cid)
        if not r: break
        parts.append(r[2]); cid=r[3]
    return " / ".join(reversed(parts))
for r in sorted(rows, key=lambda r: path(r[0])):
    print(f"  [{r[0]}] {path(r[0])}")
# also count items per collection
print("\nItems currently filed in collections:",
      c.execute("SELECT COUNT(DISTINCT itemID) FROM collectionItems").fetchone()[0])
con.close()
