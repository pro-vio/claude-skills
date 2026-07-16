import sys, sqlite3, json
sys.stdout.reconfigure(encoding="utf-8")
con = sqlite3.connect("extract/zotero_ro.sqlite")
c = con.cursor()
# attachments (PDF) count
n_pdf = c.execute("""SELECT COUNT(*) FROM itemAttachments ia
  JOIN items i ON i.itemID=ia.itemID
  WHERE ia.contentType='application/pdf'
    AND ia.itemID NOT IN (SELECT itemID FROM deletedItems)""").fetchone()[0]
# items having at least one pdf child
n_parent_pdf = c.execute("""SELECT COUNT(DISTINCT ia.parentItemID) FROM itemAttachments ia
  WHERE ia.contentType='application/pdf' AND ia.parentItemID IS NOT NULL""").fetchone()[0]
# annotations
try:
    n_ann = c.execute("SELECT COUNT(*) FROM itemAnnotations").fetchone()[0]
    n_ann_parents = c.execute("""SELECT COUNT(DISTINCT ia.parentItemID)
      FROM itemAnnotations an JOIN itemAttachments ia ON ia.itemID=an.parentItemID""").fetchone()[0]
except Exception as e:
    n_ann, n_ann_parents = "?", str(e)
print("Zotero PDF attachments:", n_pdf)
print("Zotero items with >=1 PDF child:", n_parent_pdf)
print("Zotero existing annotations:", n_ann, "| on distinct parent items:", n_ann_parents)

# how many matched zotero items already have a PDF
rec = json.load(open("extract/reconcile.json", encoding="utf-8"))
# map zid(itemID) -> key already in zotero_ids; matched gives zid=itemID
matched_zids = {zid for _,zid,_ in rec["matched"]}
q = ",".join(str(z) for z in matched_zids)
have = c.execute(f"""SELECT COUNT(DISTINCT parentItemID) FROM itemAttachments
   WHERE contentType='application/pdf' AND parentItemID IN ({q})""").fetchone()[0]
print(f"\nMatched Zotero items ({len(matched_zids)}) that ALREADY have a PDF: {have}")
con.close()
