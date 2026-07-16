import os, sys, string
sys.stdout.reconfigure(encoding="utf-8")
cands=[
 r"C:\Users\Viorel Proteasa\AppData\Local\Mendeley Ltd.\Mendeley Desktop\Downloaded",
 r"C:\Users\Viorel Proteasa\AppData\Local\Mendeley Ltd.",
 r"C:\Users\Viorel Proteasa\AppData\Roaming\Mendeley Ltd.",
 r"C:\Users\Viorel Proteasa\Documents\Mendeley Desktop",
 r"J:\My Literatures",
]
for c in cands:
    if os.path.isdir(c):
        n=sum(1 for _,_,fs in os.walk(c) for f in fs if f.lower().endswith(".pdf"))
        print("EXISTS ", c, "->", n, "PDFs")
    else:
        print("absent ", c)
drives=[d+":\\" for d in string.ascii_uppercase if os.path.exists(d+":\\")]
print("\nDrives present:", drives)
