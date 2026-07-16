import sys, os, pathlib, json, collections
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "shims"))
from dfindexeddb.indexeddb.chromium import record as crec

folder = pathlib.Path("mdb/file__0.indexeddb.leveldb")
reader = crec.FolderReader(folder)
counts = collections.Counter()
names = {}
errors = 0
for rec in reader.GetRecords(use_manifest=True):
    try:
        k = rec.key
        v = rec.value
        kn = type(k).__name__
        counts[kn] += 1
        if kn == "ObjectStoreNamesKey" or "Names" in kn:
            names[str(getattr(k, 'object_store_name', k))] = v
        if kn == "DatabaseNameKey":
            names[f"DB:{k}"] = v
    except Exception as e:
        errors += 1
print("key type counts:", dict(counts))
print("errors:", errors)
for n, v in list(names.items())[:30]:
    print("NAME:", n, "->", v)
