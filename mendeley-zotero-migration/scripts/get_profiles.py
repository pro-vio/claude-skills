import sys, os, json, glob, pathlib
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0,"shims")
from dfindexeddb.indexeddb.chromium import record as crec, blink
reader=crec.FolderReader(pathlib.Path("mdb/file__0.indexeddb.leveldb"))
blobmap={}
for f in glob.glob("mdb/file__0.indexeddb.blob/1/*/*"):
    raw=open(f,"rb").read()
    try: s=blink.V8ScriptValueDecoder.FromBytes(raw)
    except Exception: continue
    if isinstance(s,str): blobmap[len(raw)]=s
WANT={"groupProfiles","profile"}
latest={}; out={}
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
    val=v.value
    if val is None and v.blob_size in blobmap: val=blobmap[v.blob_size]
    if isinstance(val,str):
        try: val=json.loads(val)
        except Exception: pass
    out[short]=val
gp=out.get("groupProfiles") or {}
print("groupProfiles entries:", len(gp) if isinstance(gp,dict) else type(gp))
names={}
if isinstance(gp,dict):
    for pid,v in gp.items():
        if isinstance(v,dict):
            nm=" ".join(x for x in [v.get("first_name"),v.get("last_name")] if x) or v.get("display_name") or v.get("name")
            names[pid]=nm
for pid,nm in list(names.items())[:30]: print(f"  {pid[:8]} -> {nm}")
json.dump(names,open("extract/profile_names.json","w",encoding="utf-8"),ensure_ascii=False)
print("\nsaved extract/profile_names.json")
