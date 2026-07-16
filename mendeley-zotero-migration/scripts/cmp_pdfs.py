import sqlite3, sys, os, hashlib
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot, fitz
c=sqlite3.connect(f"file:{os.path.join(zot.ZDIR,'zotero.sqlite')}?mode=ro",uri=True).cursor()
def pdf_of(iid):
    r=c.execute("""SELECT i.key, ia.path FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID
        WHERE ia.parentItemID=? AND ia.contentType='application/pdf' LIMIT 1""",(iid,)).fetchone()
    if not r: return None
    return os.path.join(zot.ZDIR,"storage",r[0],r[1][len("storage:"):])
def sha1(p):
    h=hashlib.sha1()
    with open(p,"rb") as f:
        for ch in iter(lambda: f.read(1<<20), b""): h.update(ch)
    return h.hexdigest()
def head(p,n=120):
    d=fitz.open(p); t=d[0].get_text().strip().replace("\n"," ")[:n]; pg=d.page_count; d.close(); return pg,t
for a,b,label in [(10387,10284,"Stinebrickner"),(10393,10397,"Essays on Economics of HE")]:
    pa,pb=pdf_of(a),pdf_of(b)
    print(f"\n=== {label}: gunoi {a} vs corect {b} ===")
    for iid,p in ((a,pa),(b,pb)):
        if not p or not os.path.exists(p): print(f"  item {iid}: fara fisier"); continue
        pg,t=head(p)
        print(f"  item {iid}: sha1={sha1(p)[:16]} pagini={pg} {round(os.path.getsize(p)/1e6,2)}MB")
        print(f"      {t}")
    if pa and pb and os.path.exists(pa) and os.path.exists(pb):
        print(f"  --> ACELASI FISIER: {sha1(pa)==sha1(pb)}")
