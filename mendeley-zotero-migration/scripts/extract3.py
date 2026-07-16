import json, os
base = r"C:\Users\Viorel Proteasa\AppData\Roaming\Mendeley Reference Manager\IndexedDB\file__0.indexeddb.blob"
dec = json.JSONDecoder(strict=False)
def load(rel):
    raw = open(os.path.join(base, rel), "rb").read()
    for i in range(min(200, len(raw)-1)):
        if raw[i] in (0x5B, 0x7B) and raw[i+1] == 0:
            txt = raw[i:].decode("utf-16-le", errors="ignore")
            return dec.raw_decode(txt)[0]

d = load(r"3\02\23c")
docs = d["docs"]["docs"]
print("num docs:", len(docs))
sample = docs["1"]
print("doc keys:", list(sample.keys()))
print(json.dumps(sample, indent=1, ensure_ascii=False)[:1200])

ann = load(r"1\08\820")
print("\nnum annotations:", len(ann))
a = ann[0]
print(json.dumps(a, indent=1, ensure_ascii=False)[:1500])
# annotation types
from collections import Counter
motiv = Counter()
for x in ann:
    b = x.get("body") or {}
    motiv[ (x.get("_custom") or {}).get("type") or (b.get("purpose") if isinstance(b, dict) else None) ] += 1
print("\nannotation kinds:", motiv)
