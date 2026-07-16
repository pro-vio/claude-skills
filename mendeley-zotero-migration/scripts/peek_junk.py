import sqlite3, sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot, fitz
c=sqlite3.connect(f"file:{os.path.join(zot.ZDIR,'zotero.sqlite')}?mode=ro",uri=True).cursor()
for iid in (10387,10393):
    r=c.execute("""SELECT i.key, ia.path FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID
                   WHERE ia.parentItemID=?""",(iid,)).fetchone()
    if not r: print(f"item {iid}: fara atasament"); continue
    fp=os.path.join(zot.ZDIR,"storage",r[0],r[1][len("storage:"):])
    print(f"\n{'='*80}\nitem {iid} -> {os.path.basename(fp)}")
    if not os.path.exists(fp): print("   FISIERUL LIPSESTE"); continue
    print(f"   marime: {round(os.path.getsize(fp)/1e6,2)} MB")
    d=fitz.open(fp)
    print(f"   pagini: {d.page_count}")
    txt=d[0].get_text().strip()
    print("   --- prima pagina (900 car.) ---")
    print("   " + (txt[:900].replace("\n","\n   ") if txt else "(fara text — scan?)"))
    d.close()
