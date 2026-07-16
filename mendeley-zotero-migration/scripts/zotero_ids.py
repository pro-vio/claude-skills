import sys, sqlite3, json, re
sys.stdout.reconfigure(encoding="utf-8")
con = sqlite3.connect("extract/zotero_ro.sqlite")
c = con.cursor()

fieldID = dict(c.execute("SELECT fieldName, fieldID FROM fields").fetchall())

def field_values(names):
    ids = [str(fieldID[n]) for n in names if n in fieldID]
    q = f"""SELECT iv.itemID, f.fieldName, idv.value
            FROM itemData iv
            JOIN itemDataValues idv ON idv.valueID = iv.valueID
            JOIN fields f ON f.fieldID = iv.fieldID
            WHERE iv.fieldID IN ({','.join(ids)})"""
    return c.execute(q).fetchall()

# top-level items
c.execute("""
SELECT i.itemID, i.key, it.typeName
FROM items i JOIN itemTypes it ON it.itemTypeID=i.itemTypeID
WHERE i.itemID NOT IN (SELECT itemID FROM deletedItems)
  AND it.typeName NOT IN ('attachment','note','annotation')
""")
items = {r[0]: {"key": r[1], "type": r[2]} for r in c.fetchall()}

for iid, fn, val in field_values(["title","DOI","ISBN","date","extra","publicationTitle"]):
    if iid in items:
        items[iid].setdefault("f", {})[fn] = val

# creators (first author surname)
c.execute("""SELECT ic.itemID, cr.lastName, ic.orderIndex
             FROM itemCreators ic JOIN creators cr ON cr.creatorID=ic.creatorID
             ORDER BY ic.itemID, ic.orderIndex""")
for iid, last, oi in c.fetchall():
    if iid in items and "author1" not in items[iid]:
        items[iid]["author1"] = last

con.close()

def norm_doi(s):
    if not s: return None
    m = re.search(r"10\.\d{4,9}/\S+", s, re.I)
    return m.group(0).rstrip(".").lower() if m else None
def norm_isbn(s):
    if not s: return None
    d = re.sub(r"[^0-9Xx]", "", s)
    return d.upper() or None
def norm_title(s):
    if not s: return None
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return s or None
def year_of(s):
    if not s: return None
    m = re.search(r"\d{4}", s)
    return m.group(0) if m else None

out = []
for iid, d in items.items():
    f = d.get("f", {})
    extra = f.get("extra","")
    doi = norm_doi(f.get("DOI")) or norm_doi(extra)
    pmid = None
    m = re.search(r"PMID:\s*(\d+)", extra, re.I)
    if m: pmid = m.group(1)
    out.append({
        "zid": iid, "key": d["key"], "type": d["type"],
        "doi": doi,
        "isbn": norm_isbn(f.get("ISBN")),
        "pmid": pmid,
        "title_n": norm_title(f.get("title")),
        "year": year_of(f.get("date")),
        "author1": (d.get("author1") or "").lower() or None,
    })
json.dump(out, open("extract/zotero_ids.json","w",encoding="utf-8"), ensure_ascii=False)
print("zotero items with ids:", len(out))
print("with doi:", sum(1 for x in out if x["doi"]), "| isbn:", sum(1 for x in out if x["isbn"]),
      "| pmid:", sum(1 for x in out if x["pmid"]), "| title:", sum(1 for x in out if x["title_n"]))
