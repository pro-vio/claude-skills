import sqlite3, sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot, fitz
c=sqlite3.connect(f"file:{os.path.join(zot.ZDIR,'zotero.sqlite')}?mode=ro",uri=True).cursor()
ab=c.execute("""SELECT v.value FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
    JOIN fields f ON f.fieldID=d.fieldID WHERE d.itemID=10397 AND f.fieldName='abstractNote'""").fetchone()
print("=== ABSTRACTUL din itemul 10397 (atribuit lui Denning) ===")
print(ab[0][:900] if ab else "(niciunul)")
r=c.execute("""SELECT i.key, ia.path FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID
    WHERE ia.parentItemID=10397 AND ia.contentType='application/pdf' LIMIT 1""").fetchone()
fp=os.path.join(zot.ZDIR,"storage",r[0],r[1][len("storage:"):])
d=fitz.open(fp)
print("\n=== ABSTRACTUL din PDF-ul atasat (teza Xing Xia) ===")
for p in range(2,7):
    t=d[p].get_text().strip()
    if "abstract" in t.lower()[:200] or len(t)>400:
        print(f"--- pagina {p+1} ---")
        print(t[:900]); break
d.close()
# does Xing Xia exist elsewhere?
print("\n=== exista Xing Xia altundeva in biblioteca? ===")
NT="i.itemID NOT IN (SELECT itemID FROM deletedItems)"
hits=c.execute(f"""SELECT DISTINCT i.itemID FROM items i JOIN itemCreators ic ON ic.itemID=i.itemID
    JOIN creators cr ON cr.creatorID=ic.creatorID WHERE LOWER(cr.lastName) LIKE '%xia%' AND {NT}""").fetchall()
for (iid,) in hits:
    t=c.execute("""SELECT v.value FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
        JOIN fields f ON f.fieldID=d.fieldID WHERE d.itemID=? AND f.fieldName='title'""",(iid,)).fetchone()
    au=c.execute("""SELECT cr.lastName, cr.firstName FROM itemCreators ic JOIN creators cr ON cr.creatorID=ic.creatorID
        WHERE ic.itemID=? ORDER BY ic.orderIndex LIMIT 2""",(iid,)).fetchall()
    print(f"  item {iid}: {au} — {(t[0] if t else '?')[:55]}")
