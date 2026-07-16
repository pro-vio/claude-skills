import sys, json, os
sys.stdout.reconfigure(encoding="utf-8")
d = json.load(open("extract/mendeley_local.json", encoding="utf-8"))
docs = d["documents"]; cols = d["collections"]; files = d["files"]

user_cols = cols.get("user", [])
print("== user folders:", len(user_cols))
for c in user_cols:
    print("  ", c.get("id")[:8], "| parent:", (c.get("parentId") or c.get("parent_id") or "-")[:8] if (c.get("parentId") or c.get("parent_id")) else "-", "|", c.get("name"))

print("\nisTrashed:", sum(1 for v in docs.values() if v.get("isTrashed")))
print("types:", end=" ")
from collections import Counter
print(Counter(v.get("type") for v in docs.values()).most_common(10))
ids_with_doi = sum(1 for v in docs.values() if (v.get("identifiers") or {}).get("doi"))
print("docs with DOI:", ids_with_doi)

# local PDFs vs referenced files
local = {fn[:-4] for fn in os.listdir(r"C:\Users\Viorel Proteasa\AppData\Roaming\Mendeley Reference Manager\userfiles") if fn.endswith(".pdf")}
allfiles = [f for v in files.values() for f in v]
have = [f for f in allfiles if f["id"] in local]
print("\nfile entries:", len(allfiles), "| local PDFs:", len(local), "| matched locally:", len(have))
# annotated docs coverage
ann = d["annotationsV2"]
ann_files = {(a.get("_custom") or {}).get("fileId") for a in ann}
print("annotated fileIds:", len(ann_files), "| of which local:", len(ann_files & local))
