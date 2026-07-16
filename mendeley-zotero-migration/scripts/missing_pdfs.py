# -*- coding: utf-8 -*-
"""The annotated PDFs Zotero's import did not bring: list them with title + author,
and say whose annotations are stranded."""
import sys, json, os, hashlib
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")

amap = json.load(open("extract/ann_by_filehash.json", encoding="utf-8"))
h2att = json.load(open("extract/zotero_sha1_to_attach.json", encoding="utf-8"))
data = json.load(open("extract/mendeley_local.json", encoding="utf-8"))
docs = data["documents"]; files = data["files"]

# filehash -> (docId, file_name)
h_doc = {}
for did, fl in files.items():
    for f in fl:
        if f.get("filehash"):
            h_doc[f["filehash"]] = (did, f.get("file_name"))

missing = [h for h in amap if h not in h2att]
print(f"PDF-uri adnotate pe care importul NU le-a adus: {len(missing)}")
print(f"adnotari blocate pe ele: {sum(len(amap[h]) for h in missing)}\n")

rows = []
for h in missing:
    did, fname = h_doc.get(h, (None, None))
    d = docs.get(did) or {}
    au = d.get("authors") or []
    a1 = (au[0].get("last_name") if au and isinstance(au[0], dict) else None) or "-"
    n = len(amap[h])
    mine = sum(1 for x in amap[h] if x["author"] is None)
    who = sorted({x["author"] for x in amap[h] if x["author"]})
    rows.append((n, a1, d.get("year"), d.get("title") or fname or "(fara titlu)", mine, who, d.get("isTrashed")))
rows.sort(key=lambda r: -r[0])
for n, a1, yr, t, mine, who, trashed in rows:
    tag = " [in trash Mendeley]" if trashed else ""
    w = f" | studenti: {', '.join(who)}" if who else ""
    print(f"  {n:3} adnotari ({mine} ale tale{w}){tag}")
    print(f"       {a1} ({yr}) — {str(t)[:75]}")
