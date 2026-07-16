import sys, json, os
from collections import defaultdict, Counter
sys.stdout.reconfigure(encoding="utf-8")
men = {m["mid"]: m for m in json.load(open("extract/mendeley_ids.json", encoding="utf-8"))}
rec = json.load(open("extract/reconcile.json", encoding="utf-8"))
data = json.load(open("extract/mendeley_local.json", encoding="utf-8"))
files = data["files"]
ann = data["annotationsV2"]

# local PDFs
udir = r"C:\Users\Viorel Proteasa\AppData\Roaming\Mendeley Reference Manager\userfiles"
local = {fn[:-4] for fn in os.listdir(udir) if fn.lower().endswith(".pdf")}
# fileId -> docId; docId -> local pdf?
doc_local_pdf = {}
for did, flist in files.items():
    for f in flist:
        if f["id"] in local:
            doc_local_pdf.setdefault(did, []).append(f["id"])
# annotated fileIds
ann_by_file = defaultdict(int)
for a in ann:
    fid = (a.get("_custom") or {}).get("fileId")
    if fid: ann_by_file[fid]+=1

tc_ids = rec["tocreate"]
# group by DOI, else title+year, else unique
groups = defaultdict(list)
singles = []
for mid in tc_ids:
    m = men[mid]
    if m["doi"]:
        groups[("doi", m["doi"])].append(mid)
    elif m["title_n"]:
        groups[("ty", m["title_n"], m["year"])].append(mid)
    else:
        singles.append(mid)

unique_reps = []
merged_away = 0
for k, mids in groups.items():
    unique_reps.append(mids[0])
    merged_away += len(mids) - 1
unique_reps += singles

n_new = len(unique_reps)
print(f"To-create brut: {len(tc_ids)}")
print(f"  - duplicate interne colapsate: {merged_away}")
print(f"  = ITEME NOI UNICE de creat: {n_new}")

# coverage on unique reps (but PDFs/annotations should be gathered from ALL group members)
def group_members(mid):
    m = men[mid]
    if m["doi"]:
        return groups[("doi", m["doi"])]
    if m["title_n"]:
        return groups.get(("ty", m["title_n"], m["year"]), [mid])
    return [mid]

new_with_pdf = 0; new_with_ann = 0; total_local_pdfs = 0; total_ann = 0
for rep in unique_reps:
    mems = group_members(rep)
    pdfs = set()
    anns = 0
    for mm in mems:
        for fid in doc_local_pdf.get(mm, []):
            pdfs.add(fid)
            anns += ann_by_file.get(fid, 0)
    if pdfs:
        new_with_pdf += 1; total_local_pdfs += len(pdfs)
    if anns:
        new_with_ann += 1; total_ann += anns

print(f"\nDintre itemele noi unice:")
print(f"  cu PDF local atașabil: {new_with_pdf}  ({total_local_pdfs} PDF-uri)")
print(f"  cu adnotări pe PDF local: {new_with_ann}  ({total_ann} adnotări)")

# also matched items may get PDFs/annotations attached to EXISTING zotero items
matched = rec["matched"]
m_with_pdf = 0; m_ann = 0
for mid, zid, how in matched:
    mems_pdfs = doc_local_pdf.get(mid, [])
    if mems_pdfs:
        m_with_pdf += 1
        for fid in mems_pdfs: m_ann += ann_by_file.get(fid,0)
print(f"\nItemele MATCHED (existente în Zotero) cu PDF local de atașat: {m_with_pdf} ({m_ann} adnotări)")

json.dump({"unique_reps":unique_reps}, open("extract/create_plan.json","w",encoding="utf-8"))
