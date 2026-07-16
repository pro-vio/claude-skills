import sqlite3, sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot
c=sqlite3.connect(f"file:{os.path.join(zot.ZDIR,'zotero.sqlite')}?mode=ro",uri=True).cursor()
orig={x["zid"] for x in json.load(open("extract/zotero_ids.json",encoding="utf-8"))}
for label,doi in [("Covert Research Ethics","10.1108/s2398-601820210000008005"),
                  ("EHEA de Wit/Craciun","10.1007/978-3-319-77407-7"),
                  ("No Title junk","10.1017/cbo9781107415324.004"),
                  ("impact factors","10.3354/esep00141")]:
    ids=[r[0] for r in c.execute("""SELECT DISTINCT d.itemID FROM itemData d
        JOIN itemDataValues v ON v.valueID=d.valueID JOIN fields f ON f.fieldID=d.fieldID
        WHERE f.fieldName='DOI' AND LOWER(v.value) LIKE ?""",(f"%{doi}%",)).fetchall()]
    ids=[i for i in ids if not c.execute("SELECT 1 FROM deletedItems WHERE itemID=?",(i,)).fetchone()]
    print(f"{label}: {[(i, 'VECHI' if i in orig else 'import') for i in ids]}")
