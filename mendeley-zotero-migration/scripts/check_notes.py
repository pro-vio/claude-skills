import sys; sys.stdout.reconfigure(encoding="utf-8")
import json, os
base = r"C:\Users\Viorel Proteasa\AppData\Roaming\Mendeley Reference Manager\IndexedDB\file__0.indexeddb.blob"
dec = json.JSONDecoder(strict=False)
raw = open(os.path.join(base, r"1\08\820"), "rb").read()
for i in range(200):
    if raw[i] == 0x5B and raw[i+1] == 0:
        ann = dec.raw_decode(raw[i:].decode("utf-16-le", errors="ignore"))[0]
        break
notes = [a for a in ann if (a.get("_custom") or {}).get("type") == "sticky_note"]
n = notes[0]
print(json.dumps(n, indent=1, ensure_ascii=False)[:1800])
withbody = sum(1 for a in notes if a.get("body"))
print("\nsticky notes with body:", withbody, "/", len(notes))
docs_with_ann = len({(a.get("_custom") or {}).get("documentId") for a in ann})
files_with_ann = len({(a.get("_custom") or {}).get("fileId") for a in ann})
print("distinct documents with annotations:", docs_with_ann, "| distinct files:", files_with_ann)
