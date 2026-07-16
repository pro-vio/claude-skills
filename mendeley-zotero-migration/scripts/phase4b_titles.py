# -*- coding: utf-8 -*-
import sys, json, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot
plan=json.load(open("extract/attach_plan.json",encoding="utf-8"))
aids=json.load(open("extract/attach_ids.json",encoding="utf-8"))
# build attach itemID -> human file_name
title_for={}
for zid,lst in plan.items():
    for path,fname in lst:
        k=f"{zid}:{os.path.basename(path)}"
        if k in aids: title_for[aids[k]]=fname
print(f"Setting titles on {len(title_for)} attachments")
if "--apply" not in sys.argv:
    print("[DRY]"); sys.exit(0)
with zot.write_session("mendeley-phase4b-titles") as cur:
    fid=zot.field_id(cur,"title")
    for aid,name in title_for.items():
        zot.set_field(cur,aid,fid,name)
    print(f"Set {len(title_for)} attachment titles.")
