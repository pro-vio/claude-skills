# -*- coding: utf-8 -*-
import sys, json, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot
plan=json.load(open("extract/attach_plan.json",encoding="utf-8"))
mapping=[]
for zid,lst in plan.items():
    for path,fname in lst: mapping.append((int(zid),path,fname))
print(f"Attaching {len(mapping)} PDFs...")
if "--apply" not in sys.argv:
    print("[DRY RUN] --apply to write."); sys.exit(0)
attach_ids={}
with zot.write_session("mendeley-phase4-pdfs") as cur:
    ok=0
    for zid,path,fname in mapping:
        # copy to a temp name matching the human file_name so Zotero shows nice title
        aid=zot.attach_pdf(cur, zid, path)   # uses basename of path (the uuid) as stored name
        attach_ids[f"{zid}:{os.path.basename(path)}"]=aid
        ok+=1
    print(f"Attached {ok} PDFs.")
json.dump(attach_ids, open("extract/attach_ids.json","w",encoding="utf-8"))
print("saved attach_ids.json")
