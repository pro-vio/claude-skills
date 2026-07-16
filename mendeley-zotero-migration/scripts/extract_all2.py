import sys, os, pathlib, json, glob
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "shims"))
from dfindexeddb.indexeddb.chromium import record as crec, blink

folder = pathlib.Path("mdb/file__0.indexeddb.leveldb")
reader = crec.FolderReader(folder)
WANT = {"documents", "annotationsV2", "files", "highlights", "collections",
        "notebook", "groups", "profile", "recentlyRead", "documentsOrder"}
inline, latest, blobsized = {}, {}, {}
for rec in reader.GetRecords(use_manifest=True):
    if type(rec.key).__name__ != "ObjectStoreDataKey": continue
    kp = rec.key.key_prefix
    if kp.database_id != 1 or kp.object_store_id != 1: continue
    try: kname = str(rec.key.encoded_user_key.value)
    except Exception: continue
    short = kname.split(":", 1)[-1]
    if short not in WANT: continue
    v = rec.value
    ver = getattr(v, "version", 0) or 0
    if short in latest and latest[short] >= ver: continue
    latest[short] = ver
    if v.value is not None:
        val = v.value
        if isinstance(val, str):
            try: val = json.loads(val)
            except Exception: pass
        inline[short] = val
    else:
        blobsized[short] = v.blob_size

# match blob-backed stores to blob files by decoded size
blobvals = {}
for f in glob.glob("mdb/file__0.indexeddb.blob/1/*/*"):
    raw = open(f, "rb").read()
    try: s = blink.V8ScriptValueDecoder.FromBytes(raw)
    except Exception: continue
    if isinstance(s, str):
        blobvals[len(raw)] = (f, s)

out = dict(inline)
for short, size in blobsized.items():
    hit = blobvals.get(size)
    if hit is None:
        # tolerate small size mismatch
        cand = [k for k in blobvals if abs(k - size) < 200]
        hit = blobvals[cand[0]] if cand else None
    if hit:
        out[short] = json.loads(hit[1])
        print(f"{short}: blob {hit[0]} ({size} bytes)")
    else:
        print(f"{short}: NO BLOB MATCH for size {size}", file=sys.stderr)

os.makedirs("extract", exist_ok=True)
with open("extract/mendeley_local.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)

print()
for k, v in sorted(out.items()):
    if isinstance(v, dict): print(k, "-> dict", len(v))
    elif isinstance(v, list): print(k, "-> list", len(v))
    else: print(k, "->", type(v).__name__, str(v)[:60])
