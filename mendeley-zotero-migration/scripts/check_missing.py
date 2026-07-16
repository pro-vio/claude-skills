# -*- coding: utf-8 -*-
"""Are the 42 'missing' PDFs really absent from Zotero, or just hashing differently?
Mendeley's filehash is the CLOUD copy's sha1; a local userfiles copy can differ."""
import sqlite3, sys, os, json, hashlib
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
ZSTOR = os.path.join(zot.ZDIR, "storage")
UD = r"C:\Users\Viorel Proteasa\AppData\Roaming\Mendeley Reference Manager\userfiles"
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True).cursor()
amap = json.load(open("extract/ann_by_filehash.json", encoding="utf-8"))
h2att = json.load(open("extract/zotero_sha1_to_attach.json", encoding="utf-8"))
data = json.load(open("extract/mendeley_local.json", encoding="utf-8"))
docs = data["documents"]; files = data["files"]

h_info = {}
for did, fl in files.items():
    for f in fl:
        if f.get("filehash"):
            h_info[f["filehash"]] = (did, f["id"], f.get("file_name"))

missing = [h for h in amap if h not in h2att]
local_ids = {fn[:-4] for fn in os.listdir(UD) if fn.lower().endswith(".pdf")}

def sha1(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1048576), b""): h.update(ch)
    return h.hexdigest()

have_local = 0; local_sha_differs = 0; placeable = []
for h in missing:
    did, fid, fname = h_info.get(h, (None, None, None))
    if fid and fid in local_ids:
        have_local += 1
        p = os.path.join(UD, fid + ".pdf")
        actual = sha1(p)
        if actual != h:
            local_sha_differs += 1
            if actual in h2att:
                placeable.append((h, actual, len(amap[h]), (docs.get(did) or {}).get("title")))
print(f"din cele {len(missing)} 'lipsa':")
print(f"  au copie LOCALA in Mendeley userfiles : {have_local}")
print(f"  a caror copie locala are ALT sha1 decat filehash-ul inregistrat: {local_sha_differs}")
print(f"  ...si al carei sha1 REAL exista in Zotero -> ADNOTARILE SUNT PLASABILE: {len(placeable)}")
print(f"     adnotari recuperabile astfel: {sum(p[2] for p in placeable)}")
for h, actual, n, t in placeable[:8]:
    print(f"       {n:3} adnotari — {str(t)[:60]}")
json.dump({h: actual for h, actual, n, t in placeable}, open("extract/hash_remap.json", "w"))
