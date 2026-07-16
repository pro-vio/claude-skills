import sys, os, re
sys.stdout.reconfigure(encoding="utf-8")
base = r"C:\Users\Viorel Proteasa\AppData\Roaming\Mendeley Reference Manager\IndexedDB\file__0.indexeddb.blob"
for rel in [r"1\1d\1d23", r"1\1d\1d26", r"1\1d\1d27", r"1\1d\1d29"]:
    raw = open(os.path.join(base, rel), "rb").read()
    txt = raw.decode("utf-16-le", errors="ignore")
    hits = [m.start() for m in re.finditer(r'folder', txt, re.I)]
    print(rel, "len(txt)=", len(txt), "folder hits:", len(hits))
    for h in hits[:5]:
        print("   ...", txt[max(0,h-120):h+200].replace("\n"," ")[:320])
    print()
