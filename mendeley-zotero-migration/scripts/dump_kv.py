import sys, os, pathlib, json, collections
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "shims"))
from dfindexeddb.indexeddb.chromium import record as crec

folder = pathlib.Path("mdb/file__0.indexeddb.leveldb")
reader = crec.FolderReader(folder)
kv = {}
for rec in reader.GetRecords(use_manifest=True):
    if type(rec.key).__name__ != "ObjectStoreDataKey":
        continue
    dbid = rec.key.key_prefix.database_id
    sid = rec.key.key_prefix.object_store_id
    try:
        kname = rec.key.encoded_user_key.value
    except Exception:
        kname = str(rec.key)
    kv.setdefault((dbid, sid), {})[str(kname)] = rec
for (dbid, sid), d in sorted(kv.items()):
    print(f"db={dbid} store={sid}: {len(d)} keys")
    for kn, rec in list(d.items())[:40]:
        v = rec.value
        vt = type(v).__name__
        extra = ""
        if isinstance(v, (str, bytes)):
            extra = repr(v[:60])
        elif isinstance(v, dict):
            extra = "dict keys: " + str(list(v.keys())[:8])
        elif isinstance(v, list):
            extra = f"list[{len(v)}]"
        else:
            extra = str(v)[:80]
        print("   ", kn[:70], "->", vt, extra[:150])
