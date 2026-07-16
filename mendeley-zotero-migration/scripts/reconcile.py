import sys, json
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
zot = json.load(open("extract/zotero_ids.json", encoding="utf-8"))
men = json.load(open("extract/mendeley_ids.json", encoding="utf-8"))

# build Zotero indexes
by_doi, by_isbn, by_pmid, by_ta = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
for z in zot:
    if z["doi"]: by_doi[z["doi"]].append(z)
    if z["isbn"]: by_isbn[z["isbn"]].append(z)
    if z["pmid"]: by_pmid[z["pmid"]].append(z)
    if z["title_n"] and z["year"]: by_ta[(z["title_n"], z["year"])].append(z)
    if z["title_n"]: by_ta[(z["title_n"], None)].append(z)

matched, tocreate = [], []
match_by = defaultdict(int)
used_z = set()
for m in men:
    hit, how = None, None
    if m["doi"] and by_doi.get(m["doi"]):
        hit, how = by_doi[m["doi"]][0], "doi"
    elif m["pmid"] and by_pmid.get(m["pmid"]):
        hit, how = by_pmid[m["pmid"]][0], "pmid"
    elif m["isbn"] and by_isbn.get(m["isbn"]):
        hit, how = by_isbn[m["isbn"]][0], "isbn"
    elif m["title_n"] and by_ta.get((m["title_n"], m["year"])):
        hit, how = by_ta[(m["title_n"], m["year"])][0], "title+year"
    elif m["title_n"] and by_ta.get((m["title_n"], None)):
        cand = by_ta[(m["title_n"], None)][0]
        hit, how = cand, "title"
    if hit:
        matched.append((m, hit, how)); match_by[how]+=1; used_z.add(hit["zid"])
    else:
        tocreate.append(m)

print("=== RECONCILIERE ===")
print(f"Mendeley active: {len(men)}  |  Zotero existing: {len(zot)}")
print(f"MATCHED (există deja în Zotero): {len(matched)}")
for k,v in match_by.items(): print(f"    prin {k}: {v}")
print(f"DE CREAT (nou în Zotero): {len(tocreate)}")
print(f"Zotero items neatinse de match: {len(zot)-len(used_z)}")

from collections import Counter
print("\nTipuri de creat:", Counter(m["type"] for m in tocreate).most_common())
print("De creat cu DOI:", sum(1 for m in tocreate if m["doi"]),
      "| cu note:", sum(1 for m in tocreate if m["has_note"]),
      "| în foldere:", sum(1 for m in tocreate if m["folders"]))

json.dump({"matched":[(m["mid"],h["zid"],how) for m,h,how in matched],
           "tocreate":[m["mid"] for m in tocreate]},
          open("extract/reconcile.json","w",encoding="utf-8"))
