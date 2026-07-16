import json, glob, os
base = r"C:\Users\Viorel Proteasa\AppData\Roaming\Mendeley Reference Manager\IndexedDB\file__0.indexeddb.blob"
dec = json.JSONDecoder(strict=False)
for f in sorted(glob.glob(os.path.join(base, "*", "*", "*"))):
    raw = open(f, "rb").read()
    start = None
    for i in range(min(200, len(raw)-1)):
        if raw[i] in (0x5B, 0x7B) and raw[i+1] == 0:
            start = i; break
    if start is None:
        continue
    txt = raw[start:].decode("utf-16-le", errors="ignore")
    try:
        data, _ = dec.raw_decode(txt)
    except Exception as e:
        print(os.path.relpath(f, base), "-> still error:", str(e)[:80]); continue
    rel = os.path.relpath(f, base)
    if isinstance(data, list):
        print(rel, "-> list", len(data), "item0 type:", data[0].get("type") if isinstance(data[0], dict) else type(data[0]).__name__)
    else:
        print(rel, "-> dict keys:", list(data.keys()))
        for k, v in data.items():
            if isinstance(v, list):
                print("    ", k, ": list", len(v), "sample keys:", list(v[0].keys())[:15] if v and isinstance(v[0], dict) else "")
            else:
                print("    ", k, ":", type(v).__name__, str(v)[:80])
