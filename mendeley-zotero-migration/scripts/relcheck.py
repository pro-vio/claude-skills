import sqlite3, sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot
c = sqlite3.connect(f"file:{os.path.join(zot.ZDIR,'zotero.sqlite')}?mode=ro", uri=True).cursor()
print("itemRelations schema:")
for r in c.execute("PRAGMA table_info(itemRelations)").fetchall(): print("  ", r[1], r[2])
print("\nrelationPredicates:")
for r in c.execute("SELECT * FROM relationPredicates").fetchall(): print("  ", r)
print("\nsample itemRelations:", c.execute("SELECT * FROM itemRelations LIMIT 5").fetchall())
print("\nlibrary userID/groupID:", c.execute("SELECT * FROM libraries").fetchall())
print("settings account:", c.execute("SELECT key,value FROM settings WHERE setting='account'").fetchall())
