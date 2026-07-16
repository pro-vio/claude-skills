import sqlite3, sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot, fitz
c=sqlite3.connect(f"file:{os.path.join(zot.ZDIR,'zotero.sqlite')}?mode=ro",uri=True).cursor()
for iid in (9106,10801):
    r=c.execute("""SELECT i.key, ia.path FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID
        WHERE ia.parentItemID=? AND ia.contentType='application/pdf' LIMIT 1""",(iid,)).fetchone()
    fp=os.path.join(zot.ZDIR,"storage",r[0],r[1][len("storage:"):])
    d=fitz.open(fp)
    print("="*80); print(f"item {iid}: {os.path.basename(fp)} ({d.page_count} pag.)")
    print("   metadate PDF:", {k:v for k,v in d.metadata.items() if v and k in ('title','author','subject','creationDate')})
    for p in range(0,min(5,d.page_count)):
        t=d[p].get_text().strip()
        if t:
            print(f"   --- pagina {p+1} ---")
            print("   "+t[:500].replace("\n","\n   "))
    d.close(); print()
