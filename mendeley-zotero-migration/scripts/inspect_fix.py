import sqlite3, sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot
c=sqlite3.connect(f"file:{os.path.join(zot.ZDIR,'zotero.sqlite')}?mode=ro",uri=True).cursor()
print("=== item 1142 — creatori actuali ===")
for cid,ct,ln,fn,fm,oi in c.execute("""SELECT cr.creatorID, ct.creatorType, cr.lastName, cr.firstName, cr.fieldMode, ic.orderIndex
    FROM itemCreators ic JOIN creators cr ON cr.creatorID=ic.creatorID
    JOIN creatorTypes ct ON ct.creatorTypeID=ic.creatorTypeID WHERE ic.itemID=1142 ORDER BY ic.orderIndex""").fetchall():
    used=c.execute("SELECT COUNT(*) FROM itemCreators WHERE creatorID=?",(cid,)).fetchone()[0]
    print(f"  [{oi}] {ct}: lastName={ln!r} firstName={fn!r} fieldMode={fm} (creatorID {cid}, folosit de {used} iteme)")
print("\n=== inregistrarile-gunoi ===")
for iid in (10387,10393):
    t=c.execute("""SELECT v.value FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
        JOIN fields f ON f.fieldID=d.fieldID WHERE d.itemID=? AND f.fieldName='title'""",(iid,)).fetchone()
    att=[r[0] for r in c.execute("SELECT itemID FROM itemAttachments WHERE parentItemID=?",(iid,)).fetchall()]
    ann=0
    if att:
        q=",".join("?"*len(att)); ann=c.execute(f"SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID IN ({q})",att).fetchone()[0]
    notes=c.execute("SELECT COUNT(*) FROM itemNotes WHERE parentItemID=?",(iid,)).fetchone()[0]
    cols=[r[0] for r in c.execute("""SELECT col.collectionName FROM collectionItems ci
        JOIN collections col ON col.collectionID=ci.collectionID WHERE ci.itemID=?""",(iid,)).fetchall()]
    fname=None
    if att:
        r=c.execute("SELECT i.key, ia.path FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID WHERE ia.itemID=?",(att[0],)).fetchone()
        fname=r[1]
    print(f"  item {iid}: {t[0] if t else '?'!r}")
    print(f"     atasamente={len(att)} adnotari={ann} note={notes} colectii={cols}")
    print(f"     fisier: {fname}")
