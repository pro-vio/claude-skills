# -*- coding: utf-8 -*-
"""The PDFs that are genuinely absent: no local Mendeley copy, and the import didn't
bring them either. Their annotations cannot be placed."""
import sys, json, os
sys.stdout.reconfigure(encoding="utf-8")

amap = json.load(open("extract/ann_by_filehash.json", encoding="utf-8"))
h2att = json.load(open("extract/zotero_sha1_to_attach.json", encoding="utf-8"))
remap = json.load(open("extract/hash_remap.json", encoding="utf-8"))
data = json.load(open("extract/mendeley_local.json", encoding="utf-8"))
docs = data["documents"]; files = data["files"]
UD = r"C:\Users\Viorel Proteasa\AppData\Roaming\Mendeley Reference Manager\userfiles"
local_ids = {fn[:-4] for fn in os.listdir(UD) if fn.lower().endswith(".pdf")}

h_info = {}
for did, fl in files.items():
    for f in fl:
        if f.get("filehash"):
            h_info[f["filehash"]] = (did, f["id"], f.get("file_name"), f.get("size"))

absent = [h for h in amap if h not in h2att and h not in remap]
print(f"PDF-uri ABSENTE cu adevarat: {len(absent)}")
print(f"adnotari blocate: {sum(len(amap[h]) for h in absent)}\n")
for h in sorted(absent, key=lambda x: -len(amap[x])):
    did, fid, fname, size = h_info.get(h, (None, None, None, None))
    d = docs.get(did) or {}
    au = d.get("authors") or []
    names = ", ".join((a.get("last_name") or "") for a in au[:3] if isinstance(a, dict)) or "-"
    n = len(amap[h])
    mine = sum(1 for x in amap[h] if x["author"] is None)
    who = sorted({x["author"] for x in amap[h] if x["author"]})
    print(f"{n:3} adnotari ({mine} ale tale" + (f" | studenti: {', '.join(who)}" if who else "") + ")")
    print(f"     {names} ({d.get('year')}) — {str(d.get('title') or fname)[:78]}")
    print(f"     tip: {d.get('type')} | in trash Mendeley: {bool(d.get('isTrashed'))} | "
          f"copie locala: {'DA' if fid in local_ids else 'NU'} | fisier: {fname}")
    print(f"     marime: {round((size or 0)/1e6, 1)} MB | doc Mendeley: {did}")
    print()
