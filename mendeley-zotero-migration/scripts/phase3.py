# -*- coding: utf-8 -*-
import sys, json, os
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot, migrate, build_spec

data=json.load(open("extract/mendeley_local.json",encoding="utf-8"))
docs=data["documents"]
reps=json.load(open("extract/create_plan.json",encoding="utf-8"))["unique_reps"]
rec=json.load(open("extract/reconcile.json",encoding="utf-8"))
fm=json.load(open("extract/folder_map.json",encoding="utf-8"))
muid_to_cid=fm["muid_to_cid"]

# rebuild dedupe groups EXACTLY as dedupe_create.py (same normalized keys)
men={m["mid"]:m for m in json.load(open("extract/mendeley_ids.json",encoding="utf-8"))}
groups=defaultdict(list); singles=[]
for mid in rec["tocreate"]:
    m=men[mid]
    if m["doi"]: groups[("doi",m["doi"])].append(mid)
    elif m["title_n"]: groups[("ty",m["title_n"],m["year"])].append(mid)
    else: singles.append(mid)
rep_to_members={}
for k,mids in groups.items(): rep_to_members[mids[0]]=mids
for mid in singles: rep_to_members[mid]=[mid]
missing=[r for r in reps if r not in rep_to_members]
assert not missing, f"{len(missing)} reps without member list"

DRY = "--apply" not in sys.argv
n_items=len(reps)
n_notes=sum(1 for r in reps if build_spec.build_spec(docs[r])["note"])
n_tags=sum(1 for r in reps if build_spec.build_spec(docs[r])["tags"])
print(f"Items to create: {n_items} | with note: {n_notes} | with tags: {n_tags}")

if DRY:
    print("[DRY RUN] add --apply to write.")
    sys.exit(0)

mid_to_zid={}
with zot.write_session("mendeley-phase3-items") as cur:
    created=0
    for rep in reps:
        members=rep_to_members[rep]
        spec=build_spec.build_spec(docs[rep])
        iid=zot.add_item(cur, spec["ztype"], spec["fields"], creators=spec["creators"] or None)
        if spec["tags"]: migrate.add_tags(cur, iid, spec["tags"])
        if spec["note"]: zot.add_child_note(cur, iid, spec["note"])
        # union folder memberships across all group members
        folders=set()
        for mm in members: folders.update(docs[mm].get("folder_uuids") or [])
        for fu in folders:
            cid=muid_to_cid.get(fu)
            if cid is not None: zot.add_to_collection(cur, iid, cid)
        for mm in members: mid_to_zid[mm]=iid
        created+=1
    print(f"Created {created} items.")

json.dump(mid_to_zid, open("extract/mid_to_zid.json","w",encoding="utf-8"))
print(f"Saved mid_to_zid.json ({len(mid_to_zid)} mendeley ids -> zotero itemIDs)")
