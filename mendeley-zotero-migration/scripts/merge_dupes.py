# -*- coding: utf-8 -*-
"""Merge duplicate items after the official Mendeley import.

Grouping: DOI, else ISBN, else normalised title+year — across ALL items at once, so a
group may hold the user's original AND several imported copies.

Master choice:
  - the user's ORIGINAL item if the group has one (its key is what Word/LibreOffice
    citations point at; imported copies are brand-new and cited by nothing), lowest id;
  - otherwise the richest imported copy (most annotations, then most PDFs, then lowest id).

Merging moves everything the loser carries onto the master: PDF attachments (annotations
ride along as their children), child notes, collection memberships, tags. Then the loser,
now empty, is deleted. Dry-run by default.
"""
import sqlite3, sys, os, json, re
from collections import defaultdict, Counter
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
APPLY = "--apply" in sys.argv
con = sqlite3.connect(f"file:{DB}?mode=ro" + ("" if APPLY else "&immutable=1"), uri=True)
c = con.cursor()
NT = "i.itemID NOT IN (SELECT itemID FROM deletedItems)"
orig_ids = {x["zid"] for x in json.load(open("extract/zotero_ids.json", encoding="utf-8"))}

rows = c.execute(f"""SELECT i.itemID FROM items i JOIN itemTypes it ON it.itemTypeID=i.itemTypeID
                     WHERE it.typeName NOT IN ('attachment','note','annotation') AND {NT}""").fetchall()
items = {r[0]: {} for r in rows}
for iid, fn, val in c.execute("""SELECT d.itemID, f.fieldName, v.value FROM itemData d
        JOIN itemDataValues v ON v.valueID=d.valueID JOIN fields f ON f.fieldID=d.fieldID
        WHERE f.fieldName IN ('title','nameOfAct','caseName','DOI','ISBN','date','extra')""").fetchall():
    if iid in items:
        items[iid][fn] = val

def ndoi(s):
    if not s: return None
    m = re.search(r"10\.\d{4,9}/\S+", str(s), re.I)
    return m.group(0).rstrip(".").lower() if m else None
def nisbn(s):
    if not s: return None
    d = re.sub(r"[^0-9Xx]", "", str(s)); return d.upper() or None
def ntitle(s):
    if not s: return None
    s = re.sub(r"<[^>]+>", " ", str(s))
    s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip(); return s or None
def yr(s):
    m = re.search(r"\d{4}", str(s or "")); return m.group(0) if m else None

# First author surname, for disambiguation.
author1 = {}
for iid, last in c.execute("""SELECT ic.itemID, cr.lastName FROM itemCreators ic
        JOIN creators cr ON cr.creatorID=ic.creatorID WHERE ic.orderIndex=0""").fetchall():
    author1[iid] = re.sub(r"[^a-z]", "", (last or "").lower()) or None

# An identifier ALONE must never group: Mendeley stamps junk DOIs on unrelated records
# (10.1017/CBO9781107415324.004 pulled 18 different books — Kahneman with Acemoglu),
# and every chapter of a book shares the book's ISBN. Titles must agree too; where the
# title is the only evidence, the first author must agree as well ("Selective Incentives"
# exists by both della Porta and Oliver).
groups = defaultdict(list)
for iid, f in items.items():
    t = f.get("title") or f.get("nameOfAct") or f.get("caseName")
    doi = ndoi(f.get("DOI")) or ndoi(f.get("extra"))
    tt = ntitle(t)
    if not tt:
        continue
    a1 = author1.get(iid)
    if doi:
        key = ("doi", doi, tt)
    elif a1:
        key = ("ty", tt, yr(f.get("date")), a1)
    else:
        key = ("ty0", tt, yr(f.get("date")))
    groups[key].append(iid)
dupe_groups = {k: v for k, v in groups.items() if len(v) > 1}

# Author guard: a shared (junk) DOI + identical title still isn't proof — "Selective
# Incentives" exists by both della Porta and Oliver. Require the first authors to be
# compatible: equal, or one a substring of the other (handles "European Commission" vs
# "European Commission, Directorate-General for Research and Innovation"). A group with
# genuinely different authors is left alone and reported for manual review.
def compatible(ids):
    aus = [author1.get(i) for i in ids]
    known = [a for a in aus if a]
    for i in range(len(known)):
        for j in range(i + 1, len(known)):
            a, b = known[i], known[j]
            if a != b and a not in b and b not in a:
                return False
    return True

review = {k: v for k, v in dupe_groups.items() if not compatible(v)}
dupe_groups = {k: v for k, v in dupe_groups.items() if compatible(v)}
if review:
    print(f"!! {len(review)} grupuri LASATE NEATINSE (autori diferiti — de verificat manual):")
    for k, v in review.items():
        names = sorted({author1.get(i) or "-" for i in v})
        print(f"   {names} — {str(k[1] if k[0]=='doi' else k[1])[:55]}")
    print()

def richness(iid):
    pdfs = [r[0] for r in c.execute("SELECT itemID FROM itemAttachments WHERE parentItemID=? AND contentType='application/pdf'", (iid,)).fetchall()]
    ann = 0
    if pdfs:
        q = ",".join("?" * len(pdfs))
        ann = c.execute(f"SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID IN ({q})", pdfs).fetchone()[0]
    return (ann, len(pdfs))

plan = []          # (master, [losers])
for key, ids in dupe_groups.items():
    origs = sorted(i for i in ids if i in orig_ids)
    if origs:
        master = origs[0]
    else:
        master = sorted(ids, key=lambda i: (-richness(i)[0], -richness(i)[1], i))[0]
    losers = [i for i in ids if i != master]
    plan.append((master, losers))

n_losers = sum(len(l) for _, l in plan)
with_orig = sum(1 for m, _ in plan if m in orig_ids)
print("=== PLAN CONTOPIRE ===")
print(f"grupuri duplicate      : {len(plan)}")
print(f"iteme de contopit      : {n_losers}")
print(f"  master = item vechi  : {with_orig} grupuri")
print(f"  master = copie import: {len(plan)-with_orig} grupuri")
print(f"iteme dupa dedup       : {len(items)} -> {len(items)-n_losers}")

moves = Counter()
for master, losers in plan:
    for l in losers:
        moves["pdf"] += c.execute("SELECT COUNT(*) FROM itemAttachments WHERE parentItemID=?", (l,)).fetchone()[0]
        moves["note"] += c.execute("SELECT COUNT(*) FROM itemNotes WHERE parentItemID=?", (l,)).fetchone()[0]
        moves["colectii"] += c.execute("SELECT COUNT(*) FROM collectionItems WHERE itemID=?", (l,)).fetchone()[0]
        moves["taguri"] += c.execute("SELECT COUNT(*) FROM itemTags WHERE itemID=?", (l,)).fetchone()[0]
print(f"\nde mutat pe masteri: {dict(moves)}")
json.dump([[m, l] for m, l in plan], open("extract/merge_plan.json", "w"))

if not APPLY:
    print("\n[DRY RUN] --apply pentru a contopi.")
    sys.exit(0)

con.close()
with zot.write_session("merge-duplicate-items") as w:
    merged = 0
    for master, losers in plan:
        for l in losers:
            w.execute("UPDATE itemAttachments SET parentItemID=? WHERE parentItemID=?", (master, l))
            w.execute("UPDATE itemNotes SET parentItemID=? WHERE parentItemID=?", (master, l))
            for (cid,) in w.execute("SELECT collectionID FROM collectionItems WHERE itemID=?", (l,)).fetchall():
                oi = w.execute("SELECT COALESCE(MAX(orderIndex),0)+1 FROM collectionItems WHERE collectionID=?", (cid,)).fetchone()[0]
                w.execute("INSERT OR IGNORE INTO collectionItems (collectionID,itemID,orderIndex) VALUES (?,?,?)", (cid, master, oi))
            for (tid,) in w.execute("SELECT tagID FROM itemTags WHERE itemID=?", (l,)).fetchall():
                w.execute("INSERT OR IGNORE INTO itemTags (itemID,tagID,type) VALUES (?,?,0)", (master, tid))
            for tbl in ("itemData", "itemCreators", "itemTags", "collectionItems", "deletedItems", "itemRelations"):
                try: w.execute(f"DELETE FROM {tbl} WHERE itemID=?", (l,))
                except sqlite3.OperationalError: pass
            w.execute("DELETE FROM items WHERE itemID=?", (l,))
            merged += 1
        zot.touch(w, master)
    print(f"Contopite {merged} iteme in {len(plan)} masteri.")
