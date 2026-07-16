import sqlite3, sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot
c=sqlite3.connect(f"file:{os.path.join(zot.ZDIR,'zotero.sqlite')}?mode=ro",uri=True).cursor()
NT="i.itemID NOT IN (SELECT itemID FROM deletedItems)"
for label,q in [("Stinebrickner / causal effect of studying","%causal effect of studying%"),
                ("Essays on the Economics of Higher Education","%economics of higher education%")]:
    print(f"\n=== {label} ===")
    ids=[r[0] for r in c.execute(f"""SELECT DISTINCT d.itemID FROM itemData d
        JOIN itemDataValues v ON v.valueID=d.valueID JOIN fields f ON f.fieldID=d.fieldID
        JOIN items i ON i.itemID=d.itemID
        WHERE f.fieldName IN ('title') AND LOWER(v.value) LIKE ? AND {NT}""",(q,)).fetchall()]
    for iid in ids:
        t=c.execute("""SELECT v.value FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
            JOIN fields f ON f.fieldID=d.fieldID WHERE d.itemID=? AND f.fieldName='title'""",(iid,)).fetchone()
        ty=c.execute("SELECT it.typeName FROM items i JOIN itemTypes it ON it.itemTypeID=i.itemTypeID WHERE i.itemID=?",(iid,)).fetchone()[0]
        au=[f"{l}" for l, in c.execute("""SELECT cr.lastName FROM itemCreators ic JOIN creators cr ON cr.creatorID=ic.creatorID
            WHERE ic.itemID=? ORDER BY ic.orderIndex LIMIT 3""",(iid,)).fetchall()]
        att=c.execute("SELECT COUNT(*) FROM itemAttachments WHERE parentItemID=? AND contentType='application/pdf'",(iid,)).fetchone()[0]
        cols=[r[0] for r in c.execute("""SELECT col.collectionName FROM collectionItems ci
            JOIN collections col ON col.collectionID=ci.collectionID WHERE ci.itemID=?""",(iid,)).fetchall()]
        print(f"  item {iid} [{ty}] {', '.join(au)} — {t[0][:60]}")
        print(f"      pdf={att} colectii={cols}")
