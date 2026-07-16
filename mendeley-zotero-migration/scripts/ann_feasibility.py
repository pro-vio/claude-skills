import sys, json, os, hashlib, glob
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
data = json.load(open("extract/mendeley_local.json", encoding="utf-8"))
files = data["files"]; ann = data["annotationsV2"]
udir = r"C:\Users\Viorel Proteasa\AppData\Roaming\Mendeley Reference Manager\userfiles"

# fileId -> local path if present
local_ids = {fn[:-4] for fn in os.listdir(udir) if fn.lower().endswith(".pdf")}

# md5 of local Mendeley PDFs that are annotated
ann_by_file = defaultdict(int)
for a in ann:
    fid = (a.get("_custom") or {}).get("fileId")
    if fid: ann_by_file[fid]+=1

def md5(p):
    h=hashlib.md5()
    with open(p,"rb") as f:
        for ch in iter(lambda:f.read(1<<20), b""): h.update(ch)
    return h.hexdigest()

# md5 of all Zotero storage PDFs
zpdf = glob.glob(r"C:\Users\Viorel Proteasa\Zotero\storage\*\*.pdf")
print("Zotero storage PDFs:", len(zpdf), "-> hashing...")
zmd5 = {}
for p in zpdf:
    try: zmd5.setdefault(md5(p), p)
    except Exception: pass

# annotated + local Mendeley PDFs
ann_local = [fid for fid in ann_by_file if fid in local_ids]
tot_ann_local = sum(ann_by_file[f] for f in ann_local)
print(f"\nAnnotated Mendeley files total: {len(ann_by_file)} ({sum(ann_by_file.values())} annotations)")
print(f"  of which local PDF present: {len(ann_local)} ({tot_ann_local} annotations)")

match_content = 0; ann_match_content = 0
for fid in ann_local:
    p = os.path.join(udir, fid+".pdf")
    h = md5(p)
    if h in zmd5:
        match_content += 1; ann_match_content += ann_by_file[fid]
print(f"  of which SAME PDF already in Zotero storage (md5): {match_content} ({ann_match_content} annotations)")
print(f"  local but NOT yet in Zotero (attach fresh + annotate): {len(ann_local)-match_content} ({tot_ann_local-ann_match_content} annotations)")
