import os, sys
sys.stdout.reconfigure(encoding="utf-8")
# 1. walk userfiles for nested pdfs
ud=r"C:\Users\Viorel Proteasa\AppData\Roaming\Mendeley Reference Manager\userfiles"
walk_n=sum(1 for _,_,fs in os.walk(ud) for f in fs if f.lower().endswith(".pdf"))
subdirs=[d for d in os.listdir(ud) if os.path.isdir(os.path.join(ud,d))]
print(f"userfiles walk PDFs: {walk_n} | subdirs: {len(subdirs)}")
# 2. G: top-level structure
print("\nG:\ top-level:")
try:
    for e in os.listdir("G:\\")[:40]: print("  ", e)
except Exception as ex: print("  err", ex)
