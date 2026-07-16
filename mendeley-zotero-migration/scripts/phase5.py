# -*- coding: utf-8 -*-
import sys, json, os, hashlib, sqlite3
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot
import fitz

udir=r"C:\Users\Viorel Proteasa\AppData\Roaming\Mendeley Reference Manager\userfiles"
ann=json.load(open("extract/mendeley_local.json",encoding="utf-8"))["annotationsV2"]

COLOR={"yellow-light80":"#ffd400","azureblue-light80":"#2ea8e5","mendeleyred-light80":"#ff6666",
       "pink-light80":"#e56eee","green-light80":"#5fb236","grey-30":"#aaaaaa",
       "orange-light80":"#f19837","purple-light80":"#a28ae5",None:"#ffd400"}

def md5(p):
    h=hashlib.md5(); h.update(open(p,"rb").read()); return h.hexdigest()

# --- map annotated local files -> zotero attachment itemID via md5 ---
local={fn[:-4] for fn in os.listdir(udir) if fn.lower().endswith(".pdf")}
byfile=defaultdict(list)
for a in ann:
    fid=(a.get("_custom") or {}).get("fileId")
    if fid: byfile[fid].append(a)
annotated_local=[f for f in byfile if f in local]
# md5 of each annotated local file
file_md5={f:md5(os.path.join(udir,f+".pdf")) for f in annotated_local}

con=sqlite3.connect(r"C:\Users\Viorel Proteasa\Zotero\zotero.sqlite"); c=con.cursor()
ZSTOR=os.path.join(zot.ZDIR,"storage")
# Map md5-of-actual-stored-file -> attachment itemID (storageHash column is often NULL).
# Cache to disk: hashing all stored PDFs takes minutes.
target_md5={h for h in file_md5.values()}
CACHE="extract/storage_md5.json"
if os.path.exists(CACHE):
    stored_md5=json.load(open(CACHE,encoding="utf-8"))  # {attachItemID(str): md5}
else:
    stored_md5={}
    for iid,key,path in c.execute("SELECT ia.itemID,i.key,ia.path FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID WHERE ia.contentType='application/pdf' AND ia.path LIKE 'storage:%'").fetchall():
        fpath=os.path.join(ZSTOR,key,path[len('storage:'):])
        if os.path.exists(fpath):
            try: stored_md5[str(iid)]=md5(fpath)
            except Exception: pass
    json.dump(stored_md5,open(CACHE,"w",encoding="utf-8"))
hash_to_attach={}
for iid,h in stored_md5.items():
    if h in target_md5: hash_to_attach.setdefault(h,int(iid))
# also existing annotations per attachment (avoid re-adding if rerun)
existing_ann=defaultdict(int)
for (p,) in c.execute("SELECT parentItemID FROM itemAnnotations").fetchall(): existing_ann[p]+=1
con.close()

file_to_attach={f:hash_to_attach.get(h) for f,h in file_md5.items()}
mapped=[f for f in annotated_local if file_to_attach.get(f)]
n_ann_mapped=sum(len(byfile[f]) for f in mapped)
print(f"Annotated local files: {len(annotated_local)} | mapped to a Zotero attachment: {len(mapped)}")
print(f"Annotations recreatable: {n_ann_mapped}")

def body_text(a):
    """Extract the comment text from a Mendeley annotation body, tolerating
    value as {text:...} dict OR a plain string."""
    for b in (a.get("body") or []):
        v=b.get("value") if isinstance(b,dict) else None
        if isinstance(v,dict):
            t=v.get("text")
            if t and str(t).strip(): return str(t).strip()
        elif isinstance(v,str) and v.strip():
            return v.strip()
    return None

def convert(a, doc):
    cu=a.get("_custom") or {}
    typ=cu.get("type"); ps=cu.get("positions") or []
    if not ps: return None
    page0=ps[0]["page"]-1
    if page0<0 or page0>=doc.page_count: return None
    P=doc[page0]; H=P.rect.height
    rects=[]
    for r in ps:
        tl=r["top_left"]; br=r["bottom_right"]
        x0,x1=min(tl["x"],br["x"]),max(tl["x"],br["x"])
        yb,yt=min(tl["y"],br["y"]),max(tl["y"],br["y"])
        rects.append([round(x0,3),round(yb,3),round(x1,3),round(yt,3)])
    ztype=2 if typ=="sticky_note" else 1
    text=None; comment=body_text(a)
    if ztype==2:
        x,y=ps[0]["top_left"]["x"], ps[0]["top_left"]["y"]
        rects=[[round(x,3),round(y,3),round(x+22,3),round(y+22,3)]]
    else:
        parts=[]
        for r in rects:
            fr=fitz.Rect(r[0], H-r[3], r[2], H-r[1])
            t=P.get_textbox(fr).strip()
            if t: parts.append(t)
        text=" ".join(parts) or None
    color=COLOR.get(cu.get("color"),"#ffd400")
    yMax=max(r[3] for r in rects)
    # offset via reading-order words
    off=0
    try:
        words=P.get_text("words"); acc=0; best=10**9; bestoff=0
        tlx=rects[0][0]; tly=H-rects[0][3]
        for w in words:
            wx,wy=w[0],w[1]; d=abs(wy-tly)*1000+abs(wx-tlx)
            if d<best: best=d; bestoff=acc
            acc+=len(w[4])+1
        off=min(bestoff,999999)
    except Exception: off=0
    sort=f"{page0:05d}|{off:06d}|{max(0,round(H-yMax)):05d}"
    pos=json.dumps({"pageIndex":page0,"rects":rects},separators=(",",":"))
    return dict(type=ztype,text=text,comment=comment,color=color,
                pageLabel=str(ps[0]["page"]),sortIndex=sort,position=pos)

DRY = "--apply" not in sys.argv
if DRY:
    # preview a few
    shown=0
    for f in mapped:
        doc=fitz.open(os.path.join(udir,f+".pdf"))
        for a in byfile[f]:
            r=convert(a,doc)
            if not r: continue
            print(f"\n[{ 'NOTE' if r['type']==2 else 'HL' }] p{r['pageLabel']} {r['color']} sort={r['sortIndex']}")
            if r['text']: print("  text:", r['text'][:110])
            if r['comment']: print("  comment:", r['comment'][:110])
            shown+=1
            if shown>=6: break
        doc.close()
        if shown>=6: break
    print(f"\n[DRY RUN] would write {n_ann_mapped} annotations onto {len(mapped)} attachments. --apply to write.")
    sys.exit(0)

ann_type_id=None
with zot.write_session("mendeley-phase5-annotations") as cur:
    ann_type_id=zot.item_type_id(cur,"annotation")
    written=0; skipped_dup=0
    for f in mapped:
        parent=file_to_attach[f]
        doc=fitz.open(os.path.join(udir,f+".pdf"))
        # if this attachment already has annotations, skip to avoid duplicates on rerun
        cnt=cur.execute("SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID=?",(parent,)).fetchone()[0]
        if cnt>0:
            skipped_dup+=len(byfile[f]); doc.close(); continue
        for a in byfile[f]:
            r=convert(a,doc)
            if not r: continue
            iid=zot._next_id(cur,"itemID","items"); t=zot.now()
            cur.execute("INSERT INTO items (itemID,itemTypeID,dateAdded,dateModified,clientDateModified,libraryID,key,version,synced) "
                        "VALUES (?,?,?,?,?,?,?,0,0)",(iid,ann_type_id,t,t,t,zot.LIBRARY_ID,zot.newkey()))
            cur.execute("INSERT INTO itemAnnotations (itemID,parentItemID,type,authorName,text,comment,color,pageLabel,sortIndex,position,isExternal) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,0)",
                        (iid,parent,r["type"],None,r["text"],r["comment"],r["color"],r["pageLabel"],r["sortIndex"],r["position"]))
            written+=1
        doc.close()
    print(f"Wrote {written} annotations; skipped {skipped_dup} (attachment already had annotations).")
