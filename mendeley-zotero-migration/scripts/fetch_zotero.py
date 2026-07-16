import sys, json, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://127.0.0.1:23119/api/users/1055731"

def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8")), r.headers

items = []
start = 0
while True:
    url = f"{BASE}/items?limit=100&start={start}&format=json&includeTrashed=0"
    batch, hdr = get(url)
    if not batch: break
    items.extend(batch)
    total = int(hdr.get("Total-Results", 0))
    start += 100
    if start >= total: break
print("fetched items:", len(items))
# save raw
json.dump(items, open("extract/zotero_items.json","w",encoding="utf-8"), ensure_ascii=False)

# type breakdown
from collections import Counter
print(Counter(i["data"].get("itemType") for i in items).most_common())
