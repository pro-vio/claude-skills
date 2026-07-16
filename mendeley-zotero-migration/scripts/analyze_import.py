import sqlite3, sys, json
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
p=r"C:\Users\Viorel Proteasa\Zotero\zotero.sqlite"
c=sqlite3.connect(f"file:{p}?mode=ro&immutable=1",uri=True).cursor()

# the import root + its whole subtree
root=131
kids={}
for cid,nm,par in c.execute("SELECT collectionID,collectionName,parentCollectionID FROM collections").fetchall():
    kids.setdefault(par,[]).append((cid,nm))
def subtree(cid):
    out=[cid]
    for k,_ in kids.get(cid,[]): out+=subtree(k)
    return out
imp_cols=subtree(root)
print(f"colecții sub 'Imported': {len(imp_cols)}")
print("subcolecții directe:", [nm for _,nm in kids.get(root,[])])

# items in import subtree
q=",".join("?"*len(imp_cols))
imp_items=set(r[0] for r in c.execute(f"SELECT DISTINCT itemID FROM collectionItems WHERE collectionID IN ({q})",imp_cols).fetchall())
print(f"\niteme în subarborele importat: {len(imp_items)}")

# my migration items still present?
m2z=json.load(open("extract/mid_to_zid.json",encoding="utf-8"))
mine=set(m2z.values())
q2=",".join("?"*len(mine))
mine_present=c.execute(f"SELECT COUNT(*) FROM items WHERE itemID IN ({q2})",list(mine)).fetchone()[0]
print(f"itemele MELE încă prezente: {mine_present} (din {len(mine)} distincte)")
print(f"suprapunere iteme mele ∩ import: {len(mine & imp_items)}")

# annotations: on import attachments vs mine
imp_att=set(r[0] for r in c.execute(f"SELECT itemID FROM itemAttachments WHERE parentItemID IN ({','.join('?'*len(imp_items))})",list(imp_items)).fetchall()) if imp_items else set()
print(f"\natașamente sub import: {len(imp_att)}")
if imp_att:
    qa=",".join("?"*len(imp_att))
    na=c.execute(f"SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID IN ({qa})",list(imp_att)).fetchone()[0]
    print(f"adnotări pe atașamentele importului: {na}")
# authorName samples
print("\nexemple authorName din import:")
for an,n in c.execute("SELECT authorName, COUNT(*) FROM itemAnnotations WHERE authorName IS NOT NULL AND authorName<>'' GROUP BY authorName ORDER BY COUNT(*) DESC LIMIT 10").fetchall():
    print(f"  {n:4}  {an}")
