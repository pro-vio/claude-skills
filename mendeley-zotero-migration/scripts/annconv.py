# -*- coding: utf-8 -*-
"""Pure Mendeley-annotation -> Zotero-annotation conversion helpers."""
import json, hashlib
import fitz
COLOR={"yellow-light80":"#ffd400","azureblue-light80":"#2ea8e5","mendeleyred-light80":"#ff6666",
       "pink-light80":"#e56eee","green-light80":"#5fb236","grey-30":"#aaaaaa",
       "orange-light80":"#f19837","purple-light80":"#a28ae5",None:"#ffd400"}
def md5(p):
    h=hashlib.md5(); h.update(open(p,"rb").read()); return h.hexdigest()
def body_text(a):
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
        # Zotero's own Mendeley importer CENTRES the 22x22 note box on the Mendeley
        # point; anchoring a corner there lands 11pt off (measured: dx=dy=+11 on
        # 211/215 notes). Match the importer so positions and dedup signatures agree.
        x,y=ps[0]["top_left"]["x"], ps[0]["top_left"]["y"]
        rects=[[round(x-11,3),round(y-11,3),round(x+11,3),round(y+11,3)]]
    else:
        parts=[]
        for r in rects:
            fr=fitz.Rect(r[0], H-r[3], r[2], H-r[1])
            t=P.get_textbox(fr).strip()
            if t: parts.append(t)
        text=" ".join(parts) or None
    color=COLOR.get(cu.get("color"),"#ffd400")
    yMax=max(r[3] for r in rects)
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
