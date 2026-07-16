import json, sys, os
sys.stdout.reconfigure(encoding="utf-8")
data=json.load(open("extract/mendeley_local.json",encoding="utf-8"))
docs=data["documents"]; files=data["files"]
ud=r"C:\Users\Viorel Proteasa\AppData\Roaming\Mendeley Reference Manager\userfiles"
local={fn[:-4] for fn in os.listdir(ud) if fn.lower().endswith(".pdf")}

active={did:v for did,v in docs.items() if not v.get("isTrashed")}
fa_true=sum(1 for v in active.values() if v.get("file_attached") is True)
print(f"Active docs: {len(active)}")
print(f"  file_attached == True: {fa_true}")
# active docs that have a file entry
active_with_fileentry=[did for did in active if did in files]
print(f"  have a file entry in 'files' store: {len(active_with_fileentry)}")
# of those, how many have the file locally
local_ok=0; missing=0; missing_hashes=set()
for did in active_with_fileentry:
    fs=files[did]
    if any(f["id"] in local for f in fs): local_ok+=1
    else:
        missing+=1
        for f in fs: missing_hashes.add(f.get("filehash"))
print(f"    of which local PDF present: {local_ok}")
print(f"    of which NOT local (cloud-only): {missing}")
# total size of local
tot=sum(os.path.getsize(os.path.join(ud,f)) for f in os.listdir(ud) if f.lower().endswith('.pdf'))
print(f"\nLocal userfiles total size: {tot/1e9:.2f} GB across {len(local)} files")
