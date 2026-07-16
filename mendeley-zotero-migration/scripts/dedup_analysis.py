# -*- coding: utf-8 -*-
"""Measure duplicates after the official import: the user's original 461 items
vs the ~2197 imported ones, and duplicate PDF attachments."""
import sqlite3, sys, os, json, re
from collections import defaultdict, Counter
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
c = sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True).cursor()
NT = "i.itemID NOT IN (SELECT itemID FROM deletedItems)"

# original items = those recorded pre-migration
orig = {x["zid"] for x in json.load(open("extract/zotero_ids.json", encoding="utf-8"))}

rows = c.execute(f"""SELECT i.itemID, it.typeName FROM items i JOIN itemTypes it ON it.itemTypeID=i.itemTypeID
                     WHERE it.typeName NOT IN ('attachment','note','annotation') AND {NT}""").fetchall()
items = {r[0]: {"type": r[1]} for r in rows}
for iid, fn, val in c.execute("""SELECT d.itemID, f.fieldName, v.value FROM itemData d
        JOIN itemDataValues v ON v.valueID=d.valueID JOIN fields f ON f.fieldID=d.fieldID
        WHERE f.fieldName IN ('title','nameOfAct','caseName','DOI','ISBN','date','extra')""").fetchall():
    if iid in items:
        items[iid].setdefault("f", {})[fn] = val

def ndoi(s):
    if not s: return None
    m = re.search(r"10\.\d{4,9}/\S+", str(s), re.I)
    return m.group(0).rstrip(".").lower() if m else None
def nisbn(s):
    if not s: return None
    d = re.sub(r"[^0-9Xx]", "", str(s))
    return d.upper() or None
def ntitle(s):
    if not s: return None
    s = re.sub(r"<[^>]+>", " ", str(s))
    s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return s or None
def yr(s):
    m = re.search(r"\d{4}", str(s or ""))
    return m.group(0) if m else None

norm = {}
for iid, d in items.items():
    f = d.get("f", {})
    t = f.get("title") or f.get("nameOfAct") or f.get("caseName")
    norm[iid] = {
        "doi": ndoi(f.get("DOI")) or ndoi(f.get("extra")),
        "isbn": nisbn(f.get("ISBN")),
        "title": ntitle(t),
        "year": yr(f.get("date")),
        "orig": iid in orig,
    }
imported = [i for i in items if i not in orig]
print(f"iteme total: {len(items)} | originale ale tale: {sum(1 for i in items if i in orig)} | din import: {len(imported)}")

# index originals
by_doi = defaultdict(list); by_isbn = defaultdict(list); by_ty = defaultdict(list)
for iid in items:
    if not norm[iid]["orig"]: continue
    n = norm[iid]
    if n["doi"]: by_doi[n["doi"]].append(iid)
    if n["isbn"]: by_isbn[n["isbn"]].append(iid)
    if n["title"]: by_ty[(n["title"], n["year"])].append(iid)

dupes = []; how = Counter()
for iid in imported:
    n = norm[iid]
    hit = None; h = None
    if n["doi"] and by_doi.get(n["doi"]): hit, h = by_doi[n["doi"]][0], "doi"
    elif n["isbn"] and by_isbn.get(n["isbn"]): hit, h = by_isbn[n["isbn"]][0], "isbn"
    elif n["title"] and by_ty.get((n["title"], n["year"])): hit, h = by_ty[(n["title"], n["year"])][0], "title+year"
    if hit:
        dupes.append((iid, hit, h)); how[h] += 1
print(f"\n=== DUPLICATE import <-> originalele tale ===")
print(f"  perechi: {len(dupes)}  {dict(how)}")

# duplicates WITHIN the import
seen = defaultdict(list)
for iid in imported:
    n = norm[iid]
    k = ("doi", n["doi"]) if n["doi"] else (("ty", n["title"], n["year"]) if n["title"] else None)
    if k: seen[k].append(iid)
intra = {k: v for k, v in seen.items() if len(v) > 1}
print(f"\n=== DUPLICATE in interiorul importului ===")
print(f"  grupuri: {len(intra)} | iteme implicate: {sum(len(v) for v in intra.values())}")

# duplicate PDF attachments (same content, multiple attachment rows)
h2att = json.load(open("extract/zotero_sha1_to_attach.json", encoding="utf-8"))
multi = {h: v for h, v in h2att.items() if len(v) > 1}
print(f"\n=== PDF-uri duplicate (acelasi continut) ===")
print(f"  continuturi cu 2+ atasamente: {len(multi)} | atasamente in plus: {sum(len(v)-1 for v in multi.values())}")
json.dump({"dupes": [[a, b, h] for a, b, h in dupes],
           "intra": {str(k): v for k, v in intra.items()}},
          open("extract/dedup_plan.json", "w", encoding="utf-8"))
