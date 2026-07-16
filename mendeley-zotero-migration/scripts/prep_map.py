import json, sys, os, hashlib
from collections import defaultdict, Counter
sys.stdout.reconfigure(encoding="utf-8")
d=json.load(open("extract/mendeley_local.json",encoding="utf-8"))
files=d["files"]; ann=d["annotationsV2"]; docs=d["documents"]
names=json.load(open("extract/profile_names.json",encoding="utf-8"))
ME="ff0f3568-d081-36fb-a122-1b0f6e93a71c"

# verify filehash algorithm
hs=[f.get("filehash") for v in files.values() for f in v if f.get("filehash")]
print("filehash length distribution:", Counter(len(h) for h in hs))
# confirm against a local file
ud=r"C:\Users\Viorel Proteasa\AppData\Roaming\Mendeley Reference Manager\userfiles"
local={fn[:-4] for fn in os.listdir(ud) if fn.lower().endswith(".pdf")}
checked=0
for did,fl in files.items():
    for f in fl:
        if f["id"] in local and f.get("filehash"):
            p=os.path.join(ud,f["id"]+".pdf"); data=open(p,"rb").read()
            print(f"  sample: sha1 match = {hashlib.sha1(data).hexdigest()==f['filehash']} | md5 match = {hashlib.md5(data).hexdigest()==f['filehash']}")
            checked+=1
    if checked>=3: break

# build filehash -> annotations (with author name)
fid_hash={}; 
for did,fl in files.items():
    for f in fl: fid_hash[f["id"]]=f.get("filehash")
bymap=defaultdict(list)
noh=0
for a in ann:
    cu=a.get("_custom") or {}
    h=fid_hash.get(cu.get("fileId"))
    if not h: noh+=1; continue
    pid=cu.get("profileId")
    author=None if pid==ME else (names.get(pid) or f"Mendeley {str(pid)[:8]}")
    bymap[h].append({"ann":a,"author":author})
print(f"\nfilehash-uri distincte cu adnotări: {len(bymap)}")
print(f"adnotări mapate: {sum(len(v) for v in bymap.values())} | fără filehash: {noh}")
mine=sum(1 for v in bymap.values() for x in v if x["author"] is None)
theirs=sum(1 for v in bymap.values() for x in v if x["author"])
print(f"  ale mele: {mine} | ale studenților: {theirs}")
json.dump({h:[{"author":x["author"],"ann":x["ann"]} for x in v] for h,v in bymap.items()},
          open("extract/ann_by_filehash.json","w",encoding="utf-8"),ensure_ascii=False)
print("saved extract/ann_by_filehash.json")
