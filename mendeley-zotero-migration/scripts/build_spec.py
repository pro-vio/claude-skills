# -*- coding: utf-8 -*-
"""Map a Mendeley document (IndexedDB record) -> Zotero item spec.
Returns dict: {ztype, fields{}, creators[], tags[], note, extra_lines[]}."""
import re, json, sqlite3, os

_VF = json.load(open(os.path.join(os.path.dirname(__file__),"extract","valid_fields.json"),encoding="utf-8"))
_con = sqlite3.connect(os.path.join(os.path.dirname(__file__),"extract","zotero_ro.sqlite"))
_allowed_creators = {}
for (t,) in _con.execute("SELECT typeName FROM itemTypes").fetchall():
    rows=_con.execute("""SELECT ct.creatorType FROM itemTypeCreatorTypes itct
      JOIN creatorTypes ct ON ct.creatorTypeID=itct.creatorTypeID
      JOIN itemTypes it ON it.itemTypeID=itct.itemTypeID WHERE it.typeName=?""",(t,)).fetchall()
    _allowed_creators[t]=[r[0] for r in rows]

TYPE_MAP = {
    "journal":"journalArticle","book":"book","book_section":"bookSection","report":"report",
    "generic":"document","bill":"bill","working_paper":"report","web_page":"webpage",
    "thesis":"thesis","conference_proceedings":"conferencePaper","newspaper_article":"newspaperArticle",
    "statute":"statute","case":"case","television_broadcast":"tvBroadcast","film":"film",
    "magazine_article":"magazineArticle","hearing":"hearing","encyclopedia_article":"encyclopediaArticle",
    "generic_document":"document","patent":"patent","computer_program":"computerProgram",
}
# where Mendeley 'source' (container title) goes, per Zotero type
SOURCE_TARGET = {
    "journalArticle":"publicationTitle","magazineArticle":"publicationTitle","newspaperArticle":"publicationTitle",
    "bookSection":"bookTitle","conferencePaper":"proceedingsTitle","webpage":"websiteTitle",
    "encyclopediaArticle":"encyclopediaTitle",
}
TITLE_FIELD = {"statute":"nameOfAct","case":"caseName"}   # else 'title'
DATE_FIELD  = {"statute":"dateEnacted","case":"dateDecided"}  # else 'date'

def _name(p):
    ln=(p.get("last_name") or "").strip(); fn=(p.get("first_name") or "").strip()
    return ln, fn

def _date(d):
    y=d.get("year"); m=d.get("month"); day=d.get("day")
    if not y: return None
    s=f"{int(y):04d}"
    if m:
        s+=f"-{int(m):02d}"
        if day: s+=f"-{int(day):02d}"
    return s

def build_spec(d):
    mtype=d.get("type") or "generic"
    zt=TYPE_MAP.get(mtype,"document")
    vf=set(_VF.get(zt,[]))
    fields={}; extra=[]
    def put(fname,val):
        if val in (None,"",[],{}): return
        val=str(val).strip()
        if not val: return
        if fname in vf: fields[fname]=val
        else: extra.append((fname,val))
    # title
    tf=TITLE_FIELD.get(zt,"title"); put(tf, d.get("title"))
    # container
    src=d.get("source")
    if src:
        tgt=SOURCE_TARGET.get(zt)
        if tgt: put(tgt,src)
        elif zt=="thesis": put("university",src)
        elif zt=="report": put("institution",src)
        else: extra.append(("source",src))
    # date
    dt=_date(d); df=DATE_FIELD.get(zt,"date"); put(df,dt)
    # scalar fields
    put("volume",d.get("volume")); put("issue",d.get("issue")); put("pages",d.get("pages"))
    put("publisher",d.get("publisher")); put("place",d.get("city")); put("edition",d.get("edition"))
    put("series",d.get("series")); put("abstractNote",d.get("abstract")); put("language",d.get("language"))
    if d.get("institution") and "institution" in vf and "institution" not in fields:
        put("institution",d.get("institution"))
    if d.get("genre"):
        if zt=="thesis": put("thesisType",d.get("genre"))
        elif zt=="report": put("reportType",d.get("genre"))
        elif zt=="film": put("genre",d.get("genre"))
        else: extra.append(("genre",d.get("genre")))
    # identifiers
    ident=d.get("identifiers") or {}
    if ident.get("doi"): put("DOI", re.sub(r"^https?://(dx\.)?doi\.org/","",str(ident["doi"]),flags=re.I))
    if ident.get("isbn"): put("ISBN",ident["isbn"])
    if ident.get("issn"): put("ISSN",ident["issn"])
    if ident.get("pmid"):
        if "PMID" in vf: put("PMID",ident["pmid"])
        else: extra.append(("PMID",ident["pmid"]))
    if ident.get("arxiv"): extra.append(("arXiv",re.sub(r"^arXiv:","",str(ident["arxiv"]),flags=re.I)))
    # url from websites
    ws=d.get("websites") or []
    if ws: put("url",ws[0])
    if len(ws)>1: extra.extend(("url",u) for u in ws[1:])
    # country/department/chapter -> extra
    for k in ("country","department","chapter","series_editor"):
        if d.get(k): extra.append((k,d[k]))
    # creators
    allowed=set(_allowed_creators.get(zt,["author"]))
    creators=[]
    for a in (d.get("authors") or []):
        ln,fn=_name(a)
        if ln or fn: creators.append(("author",ln,fn) if fn else ("author",ln))
    if "editor" in allowed:
        for e in (d.get("editors") or []):
            ln,fn=_name(e); 
            if ln or fn: creators.append(("editor",ln,fn) if fn else ("editor",ln))
    else:
        for e in (d.get("editors") or []):
            ln,fn=_name(e); extra.append(("editor",f"{ln}{', '+fn if fn else ''}"))
    if "translator" in allowed:
        for tr in (d.get("translators") or []):
            ln,fn=_name(tr)
            if ln or fn: creators.append(("translator",ln,fn) if fn else ("translator",ln))
    # tags = keywords + tags
    tags=[]
    for kw in (d.get("keywords") or []):
        if isinstance(kw,str) and kw.strip(): tags.append(kw.strip())
    for tg in (d.get("tags") or []):
        if isinstance(tg,str) and tg.strip(): tags.append(tg.strip())
    tags=list(dict.fromkeys(tags))
    # note (doc-level): strip HTML <br/> -> newlines
    note=None
    raw=(d.get("notes") or "").strip()
    if raw:
        txt=re.sub(r"<br\s*/?>","\n",raw)
        txt=re.sub(r"<[^>]+>","",txt)
        note=txt.strip() or None
    # extra field
    extra_field="\n".join(f"{k}: {v}" for k,v in extra) if extra else None
    if extra_field: fields["extra"]=(fields.get("extra","")+("\n" if fields.get("extra") else "")+extra_field)
    return {"ztype":zt,"fields":fields,"creators":creators,"tags":tags,"note":note}
