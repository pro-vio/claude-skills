import sys, json
sys.stdout.reconfigure(encoding="utf-8")
d = json.load(open("extract/mendeley_local.json", encoding="utf-8"))

docs = d["documents"]
print("== documents:", len(docs))
sample = next(iter(docs.values()))
print("doc fields:", sorted(sample.keys()))

cols = d["collections"]
print("\n== collections keys:", list(cols.keys()))
print(json.dumps(cols, ensure_ascii=False)[:800])

files = d["files"]
print("\n== files:", len(files), "docIds with files")
nf = sum(len(v) for v in files.values())
print("total file entries:", nf)
print("sample:", json.dumps(next(iter(files.values()))[0], ensure_ascii=False)[:300])

ann = d["annotationsV2"]
print("\n== annotationsV2:", len(ann))
from collections import Counter
print(Counter((a.get("_custom") or {}).get("type") for a in ann))

nb = d["notebook"]
print("\n== notebook keys:", list(nb.keys()))
print(json.dumps(nb, ensure_ascii=False)[:400])

# folder usage
withf = sum(1 for v in docs.values() if v.get("folder_uuids"))
trashed = sum(1 for v in docs.values() if v.get("trashed") or v.get("deleted"))
print("\ndocs with folder_uuids:", withf, "| trashed/deleted flag:", trashed)
# tags/notes
print("docs with notes:", sum(1 for v in docs.values() if (v.get("notes") or "").strip()))
print("docs with tags:", sum(1 for v in docs.values() if v.get("tags")))
