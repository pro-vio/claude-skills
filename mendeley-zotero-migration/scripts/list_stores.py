import sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "shims"))
from dfindexeddb.indexeddb import chromium as cidb
path = r"C:\Users\Viorel Proteasa\AppData\Roaming\Mendeley Reference Manager\IndexedDB\file__0.indexeddb.leveldb"
db = cidb.IndexedDb(path)  # guess API
print(db)
