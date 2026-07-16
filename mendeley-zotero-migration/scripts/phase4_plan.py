# -*- coding: utf-8 -*-
import sys, json, os, hashlib, sqlite3
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
data=json.load(open("extract/mendeley_local.json",encoding="utf-8"))
docs=data["documents"]; files=data["files"]
m2z=json.load(open("extract/mid_to_zid.json",encoding="utf-8"))
rec=json.load(open("extract/reconcile.json",encoding="utf-8"))
udir=r"C:\Users\Viorel Proteasa\AppData\Roaming\Mendeley Reference Manager\userfiles"
matched_z={mid:zid for mid,zid,how in rec["matched"]}
new_items=set(m2z.values()); matched_items=set(matched_z.values())
target={**{mid:z for mid,z in m2z.items()}, **matched_z}
local_ids={fn[:-4] for fn in os.listdir(udir) if fn.lower().endswith(".pdf")}
def md5(p):
    h=hashlib.md5(); h.update(open(p,"rb").read()); return h.hexdigest()

con=sqlite3.connect(r"C:\Users\Viorel Proteasa\Zotero\zotero.sqlite"); c=con.cursor()
pdf_children=defaultdict(int); have_md5=defaultdict(set)
for parent,hashv in c.execute("""SELECT parentItemID, storageHash FROM itemAttachments
      WHERE contentType='application/pdf' AND parentItemID IS NOT NULL""").fetchall():
    pdf_children[parent]+=1
    if hashv: have_md5[parent].add(hashv)
con.close()

plan=defaultdict(list); seen=set(); skip_dup=0; skip_has_pdf=0
for did, flist in files.items():
    zid=target.get(did)
    if zid is None: continue
    is_matched = zid in matched_items
    for f in flist:
        fid=f["id"]
        if fid not in local_ids: continue
        p=os.path.join(udir,fid+".pdf"); h=md5(p)
        if h in have_md5.get(zid,set()): skip_dup+=1; continue
        # matched item that already has SOME pdf -> skip to avoid dup
        if is_matched and pdf_children.get(zid,0)>0: skip_has_pdf+=1; continue
        key=(zid,h)
        if key in seen: continue
        seen.add(key)
        plan[zid].append((p, f.get("file_name") or (fid+".pdf")))

n_pdf=sum(len(v) for v in plan.values())
to_new=sum(1 for z in plan if z in new_items and z not in matched_items)
to_matched=sum(1 for z in plan if z in matched_items)
print(f"PDFs to attach: {n_pdf} onto {len(plan)} items")
print(f"  onto NEW items: {to_new} | onto matched items WITH NO pdf yet: {to_matched}")
print(f"  skipped identical-md5 already attached: {skip_dup}")
print(f"  skipped matched-item-already-has-a-pdf: {skip_has_pdf}")
json.dump({str(z):v for z,v in plan.items()}, open("extract/attach_plan.json","w",encoding="utf-8"),ensure_ascii=False)
print("saved extract/attach_plan.json")
