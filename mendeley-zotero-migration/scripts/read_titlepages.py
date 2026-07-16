import sqlite3, sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot, fitz
c=sqlite3.connect(f"file:{os.path.join(zot.ZDIR,'zotero.sqlite')}?mode=ro",uri=True).cursor()
for iid in (10393,10397):
    print("="*84)
    ty=c.execute("SELECT it.typeName FROM items i JOIN itemTypes it ON it.itemTypeID=i.itemTypeID WHERE i.itemID=?",(iid,)).fetchone()[0]
    print(f"item {iid} [{ty}] — campuri actuale:")
    for fn,v in c.execute("""SELECT f.fieldName, v.value FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
        JOIN fields f ON f.fieldID=d.fieldID WHERE d.itemID=? ORDER BY f.fieldName""",(iid,)).fetchall():
        print(f"    {fn}: {str(v)[:70]}")
    print("  creatori:", c.execute("""SELECT ct.creatorType, cr.lastName, cr.firstName FROM itemCreators ic
        JOIN creators cr ON cr.creatorID=ic.creatorID JOIN creatorTypes ct ON ct.creatorTypeID=ic.creatorTypeID
        WHERE ic.itemID=? ORDER BY ic.orderIndex""",(iid,)).fetchall())
    r=c.execute("""SELECT i.key, ia.path FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID
        WHERE ia.parentItemID=? AND ia.contentType='application/pdf' LIMIT 1""",(iid,)).fetchone()
    if r:
        fp=os.path.join(zot.ZDIR,"storage",r[0],r[1][len("storage:"):])
        d=fitz.open(fp)
        print(f"  --- pagina de titlu ({d.page_count} pagini) ---")
        print("   " + d[0].get_text().strip()[:700].replace("\n","\n   "))
        d.close()
    print()
