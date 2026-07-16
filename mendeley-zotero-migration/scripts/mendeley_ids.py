import sys, json, re
sys.stdout.reconfigure(encoding="utf-8")
d = json.load(open("extract/mendeley_local.json", encoding="utf-8"))
docs = d["documents"]

def norm_doi(s):
    if not s: return None
    m = re.search(r"10\.\d{4,9}/\S+", str(s), re.I)
    return m.group(0).rstrip(".").lower() if m else None
def norm_isbn(s):
    if not s: return None
    d = re.sub(r"[^0-9Xx]", "", str(s))
    return d.upper() or None
def norm_title(s):
    if not s: return None
    s = re.sub(r"<[^>]+>", " ", str(s))
    s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return s or None

out = []
for did, v in docs.items():
    if v.get("isTrashed"):
        continue
    ident = v.get("identifiers") or {}
    au = v.get("authors") or []
    a1 = None
    if au:
        first = au[0]
        # "Surname Given" format seen earlier
        a1 = str(first).split()[0].lower() if first else None
    out.append({
        "mid": did,
        "type": v.get("type"),
        "doi": norm_doi(ident.get("doi")),
        "isbn": norm_isbn(ident.get("isbn")),
        "pmid": str(ident.get("pmid")) if ident.get("pmid") else None,
        "title_n": norm_title(v.get("title")),
        "year": str(v.get("year")) if v.get("year") else None,
        "author1": a1,
        "folders": v.get("folder_uuids") or [],
        "has_note": bool((v.get("notes") or "").strip()),
    })
json.dump(out, open("extract/mendeley_ids.json","w",encoding="utf-8"), ensure_ascii=False)
print("active mendeley docs:", len(out))
print("with doi:", sum(1 for x in out if x["doi"]), "| isbn:", sum(1 for x in out if x["isbn"]),
      "| pmid:", sum(1 for x in out if x["pmid"]), "| title:", sum(1 for x in out if x["title_n"]))
