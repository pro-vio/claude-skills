import sys, os, json, glob
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0,"shims")
from dfindexeddb.indexeddb.chromium import record as crec, blink
import pathlib
folder=pathlib.Path("mdb/file__0.indexeddb.leveldb")
reader=crec.FolderReader(folder)
WANT={"offline","userPreferences","reader","readerv2","lastSync","documentsOrder"}
latest={}; out={}
blobmap={}
for f in glob.glob("mdb/file__0.indexeddb.blob/1/*/*"):
    raw=open(f,"rb").read()
    try: s=blink.V8ScriptValueDecoder.FromBytes(raw)
    except Exception: continue
    if isinstance(s,str): blobmap[len(raw)]=s
for rec in reader.GetRecords(use_manifest=True):
    if type(rec.key).__name__!="ObjectStoreDataKey": continue
    kp=rec.key.key_prefix
    if kp.database_id!=1 or kp.object_store_id!=1: continue
    try: kn=str(rec.key.encoded_user_key.value)
    except Exception: continue
    short=kn.split(":",1)[-1]
    if short not in WANT: continue
    v=rec.value; ver=getattr(v,"version",0) or 0
    if short in latest and latest[short]>=ver: continue
    latest[short]=ver
    if v.value is not None:
        val=v.value
        if isinstance(val,str):
            try: val=json.loads(val)
            except Exception: pass
        out[short]=val
    elif v.blob_size in blobmap:
        try: out[short]=json.loads(blobmap[v.blob_size])
        except Exception: out[short]=blobmap[v.blob_size][:500]
for k,v in out.items():
    print(f"\n=== {k} ===")
    print(json.dumps(v,ensure_ascii=False)[:900] if not isinstance(v,str) else v[:900])
