import sqlite3, sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot, fitz
c=sqlite3.connect(f"file:{os.path.join(zot.ZDIR,'zotero.sqlite')}?mode=ro",uri=True).cursor()
def show(iid,label):
    ty=c.execute("SELECT it.typeName FROM items i JOIN itemTypes it ON it.itemTypeID=i.itemTypeID WHERE i.itemID=?",(iid,)).fetchone()
    if not ty: print(f"{label} (item {iid}): LIPSA"); return
    print(f"\n{label} — item {iid} [{ty[0]}]")
    for fn,v in sorted(c.execute("""SELECT f.fieldName, v.value FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
        JOIN fields f ON f.fieldID=d.fieldID WHERE d.itemID=?""",(iid,)).fetchall()):
        print(f"    {fn}: {str(v)[:60]}")
    print("    autori:", c.execute("""SELECT cr.lastName, cr.firstName FROM itemCreators ic
        JOIN creators cr ON cr.creatorID=ic.creatorID WHERE ic.itemID=? ORDER BY ic.orderIndex""",(iid,)).fetchall())
    r=c.execute("""SELECT i.key, ia.path FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID
        WHERE ia.parentItemID=? AND ia.contentType='application/pdf' LIMIT 1""",(iid,)).fetchone()
    if r:
        fp=os.path.join(zot.ZDIR,"storage",r[0],r[1][len("storage:"):])
        d=fitz.open(fp); t=d[0].get_text().strip().replace("\n"," ")[:70]; d.close()
        print(f"    PDF ({d.page_count if False else ''}): {t}")
    else:
        print("    PDF: (niciunul)")
    print("    colectii:", [x[0] for x in c.execute("""SELECT col.collectionName FROM collectionItems ci
        JOIN collections col ON col.collectionID=ci.collectionID WHERE ci.itemID=?""",(iid,)).fetchall()])
show(10393,"REPARAT: teza Edward C. See")
show(14280,"NOU: teza Xing Xia")
show(10397,"NEATINS: Denning")
NT="itemID NOT IN (SELECT itemID FROM deletedItems)"
print("\niteme:", c.execute(f"SELECT COUNT(*) FROM items i JOIN itemTypes t ON t.itemTypeID=i.itemTypeID WHERE t.typeName NOT IN ('attachment','note','annotation') AND i.{NT}").fetchone()[0])
for l,q in [("adnotari orfane","SELECT COUNT(*) FROM itemAnnotations WHERE itemID NOT IN (SELECT itemID FROM items) OR parentItemID NOT IN (SELECT itemID FROM items)"),
            ("itemData orfane","SELECT COUNT(*) FROM itemData WHERE itemID NOT IN (SELECT itemID FROM items)"),
            ("atasamente orfane","SELECT COUNT(*) FROM itemAttachments WHERE parentItemID IS NOT NULL AND parentItemID NOT IN (SELECT itemID FROM items)")]:
    print(f"  {l}: {c.execute(q).fetchone()[0]}")
