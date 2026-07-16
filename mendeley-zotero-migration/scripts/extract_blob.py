import sys, json, glob, os
base = r"C:\Users\Viorel Proteasa\AppData\Roaming\Mendeley Reference Manager\IndexedDB\file__0.indexeddb.blob"
for f in sorted(glob.glob(os.path.join(base, "*", "*", "*"))):
    raw = open(f, "rb").read()
    # find start of UTF-16LE JSON: look for '[' or '{' followed by 0x00
    start = None
    for i in range(min(64, len(raw)-1)):
        if raw[i] in (0x5B, 0x7B) and raw[i+1] == 0:
            start = i; break
    if start is None:
        print(f, "size", len(raw), "-> no utf16 json start found; first bytes:", raw[:24].hex())
        continue
    try:
        txt = raw[start:].decode("utf-16-le", errors="ignore")
        # trim trailing garbage after last ] or }
        last = max(txt.rfind("]"), txt.rfind("}"))
        txt = txt[:last+1]
        data = json.loads(txt)
        kind = type(data).__name__
        n = len(data) if isinstance(data, (list, dict)) else "?"
        print(os.path.relpath(f, base), "size", len(raw), "->", kind, n)
        if isinstance(data, list) and data:
            print("   sample keys:", list(data[0].keys())[:12])
    except Exception as e:
        print(os.path.relpath(f, base), "size", len(raw), "-> parse error:", str(e)[:100])
