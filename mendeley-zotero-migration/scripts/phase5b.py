# -*- coding: utf-8 -*-
"""Insert annotations missed by phase5's per-file skip: for PDFs imported into
Mendeley as several records (same md5, different annotations), write the UNION
minus what's already on the attachment. Idempotent."""
import sys, json, os, hashlib, sqlite3
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot, fitz
import annconv

udir=r"C:\Users\Viorel Proteasa\AppData\Roaming\Mendeley Reference Manager\userfiles"
ann=json.load(open("extract/mendeley_local.json",encoding="utf-8"))["annotationsV2"]
local={fn[:-4] for fn in os.listdir(udir) if fn.lower().endswith(".pdf")}
byfile=defaultdict(list)
for a in ann:
    fid=(a.get("_custom") or {}).get("fileId")
    if fid: byfile[fid].append(a)
annotated_local=[f for f in byfile if f in local]
file_md5={f:annconv.md5(os.path.join(udir,f+".pdf")) for f in annotated_local}
stored_md5=json.load(open("extract/storage_md5.json",encoding="utf-8"))
target_md5=set(file_md5.values())
hash_to_attach={}
for iid,h in stored_md5.items():
    if h in target_md5: hash_to_attach.setdefault(h,int(iid))

# group annotated files by attachment
att_files=defaultdict(list)
for f in annotated_local:
    at=hash_to_attach.get(file_md5[f])
    if at: att_files[at].append(f)

def dbsig(typ,pos,text,comment):
    import json as J
    p=J.loads(pos); r0=p["rects"][0] if p.get("rects") else [0,0,0,0]
    key=(comment or "")[:40] if typ==2 else (text or "")[:40]
    return (typ, p.get("pageIndex"), round(r0[0]), round(r0[3]), key)

DRY = "--apply" not in sys.argv
con=sqlite3.connect(r"C:\Users\Viorel Proteasa\Zotero\zotero.sqlite"); c=con.cursor()
to_insert=[]  # (attach, convertedspec)
for at, fs in att_files.items():
    if len(fs)<2:  # singletons fully handled by phase5
        continue
    # existing annotations on this attachment
    existing=set()
    for typ,pos,text,comment in c.execute("SELECT type,position,text,comment FROM itemAnnotations WHERE parentItemID=?",(at,)).fetchall():
        try: existing.add(dbsig(typ,pos,text,comment))
        except Exception: pass
    # build union across all files, dedup
    seen=set()
    # open the pdf once (any file works, same content)
    doc=fitz.open(os.path.join(udir,fs[0]+".pdf"))
    for f in fs:
        for a in byfile[f]:
            r=annconv.convert(a,doc)
            if not r: continue
            s=dbsig(r["type"],r["position"],r["text"],r["comment"])
            if s in existing or s in seen: continue
            seen.add(s); to_insert.append((at,r))
    doc.close()
con.close()
print(f"Missing distinct annotations to insert: {len(to_insert)} onto {len(set(a for a,_ in to_insert))} attachments")
if DRY:
    print("[DRY RUN] --apply to write."); sys.exit(0)
with zot.write_session("mendeley-phase5b-union") as cur:
    tid=zot.item_type_id(cur,"annotation")
    for at,r in to_insert:
        iid=zot._next_id(cur,"itemID","items"); t=zot.now()
        cur.execute("INSERT INTO items (itemID,itemTypeID,dateAdded,dateModified,clientDateModified,libraryID,key,version,synced) "
                    "VALUES (?,?,?,?,?,?,?,0,0)",(iid,tid,t,t,t,zot.LIBRARY_ID,zot.newkey()))
        cur.execute("INSERT INTO itemAnnotations (itemID,parentItemID,type,authorName,text,comment,color,pageLabel,sortIndex,position,isExternal) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,0)",
                    (iid,at,r["type"],None,r["text"],r["comment"],r["color"],r["pageLabel"],r["sortIndex"],r["position"]))
    print(f"Inserted {len(to_insert)} missing annotations.")
