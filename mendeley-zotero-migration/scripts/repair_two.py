# -*- coding: utf-8 -*-
"""Two repairs, each different from what it first looked like.

10393: every field is junk (Mendeley placeholder — a chemistry DOI/ISSN/PMID and an
  abstract about polypeptide binding) while the PDF is Edward C. See's dissertation.
  Retype to thesis and set the metadata read off the title page.

10397: the record is CORRECT (Denning's dissertation — its abstract is about Texas
  community-college tuition). The FILE is the wrong one: Xing Xia's Columbia thesis.
  So don't touch Denning's metadata — move the misfiled PDF onto a new item of its own,
  or Xing Xia's work stays lost under Denning's name.
"""
import sqlite3, sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

APPLY = "--apply" in sys.argv
DB = os.path.join(zot.ZDIR, "zotero.sqlite")
c = sqlite3.connect(f"file:{DB}?mode=ro" + ("" if APPLY else "&immutable=1"), uri=True).cursor()

SEE = {"title": "Essays on the Economics of Higher Education", "thesisType": "PhD dissertation",
       "university": "University of Florida", "place": "Gainesville, FL", "date": "2012", "numPages": "175"}
XIA = {"title": "Three Essays on the Economics of Higher Education", "thesisType": "PhD dissertation",
       "university": "Columbia University", "place": "New York, NY", "date": "2016", "numPages": "162"}

print("=== 10393: retipare journalArticle -> thesis + metadate reale ===")
old = c.execute("""SELECT f.fieldName FROM itemData d JOIN fields f ON f.fieldID=d.fieldID WHERE d.itemID=10393""").fetchall()
print(f"  campuri de sters (toate gunoi): {sorted(x[0] for x in old)}")
print(f"  campuri noi: {SEE}")
print(f"  autor: 'Nursalam, 2016 / metode penelitian' -> 'See, Edward C.'")

print("\n=== 10397: itemul Denning ramane NEATINS; PDF-ul (teza Xing Xia) se muta pe item nou ===")
att = c.execute("""SELECT ia.itemID FROM itemAttachments ia WHERE ia.parentItemID=10397
                   AND ia.contentType='application/pdf'""").fetchone()
print(f"  atasament de mutat: {att[0] if att else '(niciunul)'}")
cols = [r[0] for r in c.execute("SELECT collectionID FROM collectionItems WHERE itemID=10397").fetchall()]
print(f"  itemul nou intra in aceleasi colectii: {cols}")
print(f"  campuri item nou: {XIA}")

if not APPLY:
    print("\n[DRY RUN] --apply pentru a repara.")
    sys.exit(0)

with zot.write_session("repair-see-and-xia") as w:
    # ---- 10393 -> thesis / Edward C. See ----
    tid = zot.item_type_id(w, "thesis")
    w.execute("DELETE FROM itemData WHERE itemID=10393")
    w.execute("UPDATE items SET itemTypeID=? WHERE itemID=10393", (tid,))
    for fn, val in SEE.items():
        zot.set_field(w, 10393, zot.field_id(w, fn), val)
    w.execute("DELETE FROM itemCreators WHERE itemID=10393")
    zot._set_creators(w, 10393, [("author", "See", "Edward C.")])
    zot.touch(w, 10393)

    # ---- new item for Xing Xia; move the misfiled PDF onto it ----
    xia_id = zot.add_item(w, "thesis", XIA, creators=[("author", "Xia", "Xing")])
    for cid in cols:
        zot.add_to_collection(w, xia_id, cid)
    if att:
        w.execute("UPDATE itemAttachments SET parentItemID=? WHERE itemID=?", (xia_id, att[0]))
        w.execute("UPDATE itemNotes SET parentItemID=? WHERE parentItemID=?", (xia_id, att[0]))
    zot.touch(w, 10397)
    print(f"10393 retipat ca teza (Edward C. See); item nou {xia_id} pentru Xing Xia, PDF mutat pe el.")
