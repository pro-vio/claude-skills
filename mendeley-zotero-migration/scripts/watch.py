import sqlite3, sys, time
sys.stdout.reconfigure(encoding="utf-8")
p=r"C:\Users\Viorel Proteasa\Zotero\zotero.sqlite"
def snap():
    c=sqlite3.connect(f"file:{p}?mode=ro&immutable=1",uri=True).cursor()
    NT="itemID NOT IN (SELECT itemID FROM deletedItems)"
    it=c.execute(f"SELECT COUNT(*) FROM items i JOIN itemTypes t ON t.itemTypeID=i.itemTypeID WHERE t.typeName NOT IN ('attachment','note','annotation') AND i.{NT}").fetchone()[0]
    col=c.execute("SELECT COUNT(*) FROM collections").fetchone()[0]
    att=c.execute("SELECT COUNT(*) FROM itemAttachments WHERE contentType='application/pdf'").fetchone()[0]
    ann=c.execute("SELECT COUNT(*) FROM itemAnnotations").fetchone()[0]
    return it,col,att,ann
a=snap(); time.sleep(20); b=snap()
print(f"          iteme  colecții  PDF   adnotări")
print(f"acum   :  {a[0]:5}  {a[1]:5}  {a[2]:5}  {a[3]:5}")
print(f"+20s   :  {b[0]:5}  {b[1]:5}  {b[2]:5}  {b[3]:5}")
print(f"delta  :  {b[0]-a[0]:+5}  {b[1]-a[1]:+5}  {b[2]-a[2]:+5}  {b[3]-a[3]:+5}")
print("\n=> import ÎN CURS" if b!=a else "\n=> static (import terminat sau oprit)")
