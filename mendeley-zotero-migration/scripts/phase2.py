# -*- coding: utf-8 -*-
import sys, json, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot, migrate

data = json.load(open("extract/mendeley_local.json", encoding="utf-8"))
folders = data["collections"]["user"]           # id, name, parent_id?
docs = data["documents"]
rec = json.load(open("extract/reconcile.json", encoding="utf-8"))

# --- topological order: parents before children ---
by_id = {f["id"]: f for f in folders}
ordered, placed = [], set()
def visit(fid):
    if fid in placed or fid not in by_id: return
    f = by_id[fid]
    p = f.get("parent_id")
    if p and p in by_id and p not in placed:
        visit(p)
    ordered.append(f); placed.add(fid)
for f in folders: visit(f["id"])
assert len(ordered) == len(folders), (len(ordered), len(folders))

# --- union of folder memberships per EXISTING matched Zotero itemID ---
# matched entries: (mid, zid, how); zid = Zotero itemID
z_folders = {}   # zotero itemID -> set(mendeley folder uuid)
for mid, zid, how in rec["matched"]:
    fs = docs.get(mid, {}).get("folder_uuids") or []
    if fs:
        z_folders.setdefault(zid, set()).update(fs)

print(f"Folders to create: {len(ordered)}")
print(f"Existing Zotero items to file into folders: {len(z_folders)}")

DRY = "--apply" not in sys.argv
if DRY:
    filings = sum(len(v) for v in z_folders.values())
    print(f"\n[DRY RUN] would create {len(ordered)} collections and make {filings} item-collection filings.")
    print("Run with --apply to write.")
    sys.exit(0)

muid_to_cid = {}
created = []
with zot.write_session("mendeley-phase2-collections") as cur:
    for f in ordered:
        parent_cid = muid_to_cid.get(f.get("parent_id"))
        cid = migrate.add_collection(cur, f["name"], parent_cid)
        muid_to_cid[f["id"]] = cid
        created.append(cid)
    filings = 0
    for zid, fset in z_folders.items():
        for muid in fset:
            cid = muid_to_cid.get(muid)
            if cid is not None:
                zot.add_to_collection(cur, zid, cid)
                filings += 1
    print(f"Created {len(created)} collections; {filings} filings done.")

# persist the map for phase 3
json.dump({"muid_to_cid": muid_to_cid, "created_collection_ids": created},
          open("extract/folder_map.json", "w", encoding="utf-8"), ensure_ascii=False)
print("Saved extract/folder_map.json")
