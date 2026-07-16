# -*- coding: utf-8 -*-
"""Everything the audit turned up that is safe to fix:

1. 10 itemRelations rows left pointing at deleted items.
2. Mendeley stamped the SAME bogus DOI (10.1017/CBO9781107415324.004) on 16 unrelated
   books and the SAME bogus ISBN (978-85-7811-079-6) on 13 of them — Kahneman, Acemoglu,
   Tight... An identifier that appears on a dozen different works is not that work's
   identifier; it would render a wrong DOI in every citation. Strip both.
3. Two placeholder-title records that (again) hide real documents — metadata read off
   the PDFs themselves.
4. Merge the 85 same-PDF groups whose title AND author agree. The other 39 are reported,
   not touched.
"""
import sqlite3, sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

APPLY = "--apply" in sys.argv
USERID = 1055731
BAD_DOI = "10.1017/CBO9781107415324.004"
BAD_ISBN = "978-85-7811-079-6"
DB = os.path.join(zot.ZDIR, "zotero.sqlite")
c = sqlite3.connect(f"file:{DB}?mode=ro" + ("" if APPLY else "&immutable=1"), uri=True).cursor()
audit = json.load(open("extract/audit.json", encoding="utf-8"))
cross = json.load(open("extract/cross_plan.json", encoding="utf-8"))
orig_ids = {x["zid"] for x in json.load(open("extract/zotero_ids.json", encoding="utf-8"))}

CORDELL = {"title": "The Politics of Ethnicity in Central Europe", "publisher": "Macmillan Press",
           "place": "Houndmills, Basingstoke", "date": "2000", "ISBN": "0-333-73171-9", "numPages": "255"}
TOOLBOX = {"title": 'Better Regulation "Toolbox"', "date": "2017", "numPages": "540",
           "institution": "European Commission",
           "url": "https://ec.europa.eu/info/law/law-making-process/better-regulation-why-and-how_en",
           "extra": "Complements the better regulation guidelines, SWD(2017) 350"}

rel_orphans = [r[0] for r in c.execute(
    "SELECT rowid FROM itemRelations WHERE itemID NOT IN (SELECT itemID FROM items)").fetchall()]
doi_items = c.execute("""SELECT d.itemID FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
    JOIN fields f ON f.fieldID=d.fieldID WHERE f.fieldName='DOI' AND LOWER(v.value) LIKE ?""",
    (f"%{BAD_DOI.lower()}%",)).fetchall()
isbn_items = c.execute("""SELECT d.itemID FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
    JOIN fields f ON f.fieldID=d.fieldID WHERE f.fieldName='ISBN' AND v.value LIKE ?""",
    (f"%{BAD_ISBN}%",)).fetchall()

def richness(iid):
    p = [r[0] for r in c.execute("SELECT itemID FROM itemAttachments WHERE parentItemID=? AND contentType='application/pdf'", (iid,)).fetchall()]
    a = 0
    if p:
        q = ",".join("?" * len(p))
        a = c.execute(f"SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID IN ({q})", p).fetchone()[0]
    return (a, len(p))

merges = []
for ids in cross["safe"]:
    ids = [i for i in ids if c.execute("SELECT 1 FROM items WHERE itemID=?", (i,)).fetchone()]
    if len(ids) < 2:
        continue
    origs = sorted(i for i in ids if i in orig_ids)
    master = origs[0] if origs else sorted(ids, key=lambda i: (-richness(i)[0], -richness(i)[1], i))[0]
    merges.append((master, [i for i in ids if i != master]))

print("=== REPARATII ===")
print(f"1. itemRelations orfane de sters      : {len(rel_orphans)}")
print(f"2. DOI fals de sters de pe            : {len(doi_items)} iteme")
print(f"   ISBN fals de sters de pe           : {len(isbn_items)} iteme")
print(f"3. metadate reparate                  : 9106 (Cordell), 10801 (EC Toolbox)")
print(f"4. grupuri same-PDF de contopit       : {len(merges)} -> {sum(len(l) for _, l in merges)} iteme dispar")
print(f"   (cele {len(cross['flag'])} semnalate NU se ating)")

if not APPLY:
    print("\n[DRY RUN] --apply pentru a repara.")
    sys.exit(0)

with zot.write_session("repair-audit-findings") as w:
    w.execute("DELETE FROM itemRelations WHERE itemID NOT IN (SELECT itemID FROM items)")
    fid_doi, fid_isbn = zot.field_id(w, "DOI"), zot.field_id(w, "ISBN")
    for (iid,) in doi_items:
        w.execute("DELETE FROM itemData WHERE itemID=? AND fieldID=?", (iid, fid_doi)); zot.touch(w, iid)
    for (iid,) in isbn_items:
        w.execute("DELETE FROM itemData WHERE itemID=? AND fieldID=?", (iid, fid_isbn)); zot.touch(w, iid)

    # 9106 -> edited book
    w.execute("DELETE FROM itemData WHERE itemID=9106")
    w.execute("UPDATE items SET itemTypeID=? WHERE itemID=9106", (zot.item_type_id(w, "book"),))
    for fn, v in CORDELL.items():
        zot.set_field(w, 9106, zot.field_id(w, fn), v)
    w.execute("DELETE FROM itemCreators WHERE itemID=9106")
    zot._set_creators(w, 9106, [("editor", "Cordell", "Karl")])
    zot.touch(w, 9106)
    # 10801 -> EC report
    w.execute("DELETE FROM itemData WHERE itemID=10801")
    w.execute("UPDATE items SET itemTypeID=? WHERE itemID=10801", (zot.item_type_id(w, "report"),))
    for fn, v in TOOLBOX.items():
        zot.set_field(w, 10801, zot.field_id(w, fn), v)
    w.execute("DELETE FROM itemCreators WHERE itemID=10801")
    zot._set_creators(w, 10801, [("author", "European Commission")])
    zot.touch(w, 10801)

    n = 0
    for master, losers in merges:
        for l in losers:
            r = w.execute("SELECT key FROM items WHERE itemID=?", (l,)).fetchone()
            if not r:
                continue
            uri = f"http://zotero.org/users/{USERID}/items/{r[0]}"
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
            w.execute("INSERT OR IGNORE INTO itemRelations (itemID,predicateID,object) VALUES (?,1,?)", (master, uri))
            n += 1
        zot.touch(w, master)
    print(f"Reparat: {len(rel_orphans)} relatii orfane, DOI fals de pe {len(doi_items)}, ISBN fals de pe {len(isbn_items)}, "
          f"2 iteme retipate, {n} iteme contopite.")
