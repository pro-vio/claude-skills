import json, sys
from collections import defaultdict, Counter
sys.stdout.reconfigure(encoding="utf-8")
d=json.load(open("extract/mendeley_local.json",encoding="utf-8"))
docs=d["documents"]; files=d["files"]; ann=d["annotationsV2"]; groups=d["groups"]
ME="ff0f3568-d081-36fb-a122-1b0f6e93a71c"

print("=== cine a făcut adnotările (profileId) ===")
pc=Counter((a.get("_custom") or {}).get("profileId") for a in ann)
for pid,n in pc.most_common():
    who = "EU (Viorel)" if pid==ME else f"altcineva ({str(pid)[:8]})"
    print(f"  {n:5}  {who}")
print("\nprivacyLevel:", Counter((a.get("_custom") or {}).get("privacyLevel") for a in ann))

# doc -> is group?
def gid(did): return docs.get(did,{}).get("group_id")
adoc=Counter()
for a in ann:
    did=(a.get("_custom") or {}).get("documentId")
    adoc[("GRUP" if gid(did) else "personal") if did in docs else "doc necunoscut"]+=1
print("\n=== adnotări după unde stă documentul ===")
for k,v in adoc.most_common(): print(f"  {v:5}  {k}")

# same content (filehash) annotated under BOTH a personal and a group doc
fid_to_doc={}; fid_hash={}
for did,fl in files.items():
    for f in fl:
        fid_to_doc[f["id"]]=did; fid_hash[f["id"]]=f.get("filehash")
byhash=defaultdict(lambda: {"personal":set(),"group":set()})
for a in ann:
    cu=a.get("_custom") or {}
    fid=cu.get("fileId"); did=cu.get("documentId")
    h=fid_hash.get(fid)
    if not h or did not in docs: continue
    byhash[h]["group" if gid(did) else "personal"].add(fid)
both=[h for h,v in byhash.items() if v["personal"] and v["group"]]
print(f"\n=== SUPRAPUNERE: același PDF (filehash) adnotat ȘI personal ȘI în grup ===")
print(f"  fișiere-conținut în ambele: {len(both)}")
tot=0
for h in both:
    for side in ("personal","group"):
        for fid in byhash[h][side]:
            tot+=sum(1 for a in ann if (a.get("_custom") or {}).get("fileId")==fid)
print(f"  adnotări implicate în aceste suprapuneri: {tot}")
