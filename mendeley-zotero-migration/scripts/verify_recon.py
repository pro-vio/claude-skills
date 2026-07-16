import sys, json
from collections import defaultdict, Counter
sys.stdout.reconfigure(encoding="utf-8")
zot = {z["zid"]: z for z in json.load(open("extract/zotero_ids.json", encoding="utf-8"))}
men = {m["mid"]: m for m in json.load(open("extract/mendeley_ids.json", encoding="utf-8"))}
rec = json.load(open("extract/reconcile.json", encoding="utf-8"))
mdocs = json.load(open("extract/mendeley_local.json", encoding="utf-8"))["documents"]

# 1. multiple Mendeley -> same Zotero (internal dupes among matched)
z_hit = defaultdict(list)
for mid, zid, how in rec["matched"]:
    z_hit[zid].append((mid, how))
multi = {z:v for z,v in z_hit.items() if len(v)>1}
print("Zotero items matched by >1 Mendeley doc (=dupe candidates):", len(multi))
for zid, lst in list(multi.items())[:3]:
    print("  Z:", mdocs.get(next(iter(mdocs)),{}) and zot[zid]["title_n"][:50] if zot[zid]["title_n"] else "?", "<-", len(lst), "mendeley docs")

# 2. spot-check title-only matches
print("\n--- 8 potriviri DOAR pe titlu (de verificat vizual) ---")
tonly = [(mid,zid) for mid,zid,how in rec["matched"] if how=="title"]
for mid, zid in tonly[:8]:
    mt = mdocs[mid].get("title","")[:70]
    print(f"  M[{mdocs[mid].get('year')}] {mt}")

# 3. characterize 219 unmatched Zotero items
matched_z = {zid for _,zid,_ in rec["matched"]}
unmatched = [z for zid,z in zot.items() if zid not in matched_z]
print("\n--- 219 iteme Zotero nepotrivite: tipuri ---")
print(Counter(z["type"] for z in unmatched).most_common())
print("din care fără DOI/ISBN:", sum(1 for z in unmatched if not z["doi"] and not z["isbn"]))

# 4. internal dupes among TO-CREATE (same normalized title+year)
tc = [men[mid] for mid in rec["tocreate"]]
key = defaultdict(list)
for m in tc:
    if m["title_n"]:
        key[(m["title_n"], m["year"])].append(m["mid"])
dupes = {k:v for k,v in key.items() if len(v)>1}
ndupe_docs = sum(len(v) for v in dupes.values())
print(f"\nDuplicate INTERNE în setul de creat: {len(dupes)} grupuri, {ndupe_docs} documente")
for (t,y),v in list(dupes.items())[:5]:
    print(f"  x{len(v)} [{y}] {t[:55]}")
