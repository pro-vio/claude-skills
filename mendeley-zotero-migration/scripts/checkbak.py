import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
for label,p in [("PRE-MIGRARE (phase2 backup)", r"C:\Users\Viorel Proteasa\Zotero\zotero.sqlite.pre-mendeley-phase2-collections.bak"),
                ("CURENT (post-migrare)",       r"C:\Users\Viorel Proteasa\Zotero\zotero.sqlite")]:
    try:
        c=sqlite3.connect(f"file:{p}?mode=ro&immutable=1",uri=True).cursor()
        NT="itemID NOT IN (SELECT itemID FROM deletedItems)"
        n=c.execute(f"SELECT COUNT(*) FROM items i JOIN itemTypes it ON it.itemTypeID=i.itemTypeID WHERE it.typeName NOT IN ('attachment','note','annotation') AND i.{NT}").fetchone()[0]
        col=c.execute("SELECT COUNT(*) FROM collections").fetchone()[0]
        att=c.execute("SELECT COUNT(*) FROM itemAttachments WHERE contentType='application/pdf'").fetchone()[0]
        ann=c.execute("SELECT COUNT(*) FROM itemAnnotations").fetchone()[0]
        print(f"{label}: {n} iteme | {col} colecții | {att} PDF | {ann} adnotări")
    except Exception as e:
        print(f"{label}: EROARE {e}")
