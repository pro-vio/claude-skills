import sys, os, pathlib, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "shims"))
from dfindexeddb.indexeddb.chromium import record as crec
from dfindexeddb.indexeddb.chromium import blink

folder = pathlib.Path("mdb/file__0.indexeddb.leveldb")
reader = crec.FolderReader(folder)

WANT = {"documents", "annotationsV2", "files", "highlights", "collections",
        "notebook", "groups", "profile", "recentlyRead"}
out = {}
latest = {}
for rec in reader.GetRecords(use_manifest=True):
    if type(rec.key).__name__ != "ObjectStoreDataKey":
        continue
    kp = rec.key.key_prefix
    if kp.database_id != 1 or kp.object_store_id != 1:
        continue
    try:
        kname = str(rec.key.encoded_user_key.value)
    except Exception:
        continue
    short = kname.split(":", 1)[-1]
    if short not in WANT:
        continue
    v = rec.value
    ver = getattr(v, "version", 0) or 0
    if short in latest and latest[short] >= ver:
        continue
    latest[short] = ver
    if v.value is not None:
        val = v.value
        if isinstance(val, str):
            try: val = json.loads(val)
            except Exception: pass
        out[short] = val
    elif rec.external_value is not None:
        out[short] = rec.external_value
    else:
        out[short] = None
        print("MISSING VALUE for", short, file=sys.stderr)

for k, v in sorted(out.items()):
    t = type(v).__name__
    print(k, "->", t, (list(v.keys())[:10] if isinstance(v, dict) else len(v) if isinstance(v, list) else str(v)[:80]))

os.makedirs("extract", exist_ok=True)
with open("extract/mendeley_local.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, default=str)
print("saved extract/mendeley_local.json")
