import urllib.request
import urllib.parse
import json
from datetime import datetime

TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.tracker.cl:1337/announce",
    "udp://tracker.openbittorrent.com:6969/announce",
    "udp://exodus.desync.com:6969/announce",
]

CATEGORIES = {
    "101": "Audio - Music", "102": "Audio - Audiobooks", "104": "Audio - FLAC",
    "201": "Video - Movies", "202": "Video - Movie DVDR", "205": "Video - TV shows",
    "207": "Video - HD Movies", "208": "Video - HD TV shows", "209": "Video - 3D",
    "301": "Apps - Windows", "302": "Apps - Mac", "306": "Apps - Android",
    "401": "Games - PC", "402": "Games - Mac", "408": "Games - Android",
    "601": "Other - E-books", "602": "Other - Comics", "699": "Other",
}

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "test/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)

def human_size(n):
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024

def fmt_date(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError):
        return ts

def make_magnet(info_hash, name):
    params = [("xt", f"urn:btih:{info_hash}"), ("dn", name)]
    params += [("tr", t) for t in TRACKERS]
    return "magnet:?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)

# --- search (q.php) ---
results = get_json("https://apibay.org/q.php?q=inception")
results = [r for r in results if r["info_hash"] != "0" * 40]
results.sort(key=lambda r: int(r["seeders"]), reverse=True)

print(f"{len(results)} results\n")

for i, r in enumerate(results, 1):
    cat = r.get("category", "")
    print(f"=== [{i}] {r['name']} ===")
    print(f"  size:      {human_size(r['size'])}  ({r['size']} bytes)")
    print(f"  seeders:   {r['seeders']}")
    print(f"  leechers:  {r['leechers']}")
    print(f"  files:     {r.get('num_files', '?')}")
    print(f"  added:     {fmt_date(r.get('added', ''))}")
    print(f"  uploader:  {r.get('username', '?')}")
    print(f"  category:  {cat} ({CATEGORIES.get(cat, 'unknown')})")
    print(f"  imdb:      {r.get('imdb') or '—'}")
    print(f"  id:        {r.get('id', '?')}")
    print(f"  hash:      {r['info_hash']}")
    print(f"  magnet:    {make_magnet(r['info_hash'], r['name'])}")
    print()

# --- deepest layer: description (t.php) + file list (f.php) for top result ---
if results:
    top = results[0]
    tid = top["id"]
    print("=" * 60)
    print(f"FULL DETAIL for top result (id {tid})\n")

    detail = get_json(f"https://apibay.org/t.php?id={tid}")
    print("description:")
    print(f"  {detail.get('descr', '').strip() or '(none)'}\n")

    print("files inside:")
    for f in get_json(f"https://apibay.org/f.php?id={tid}"):
        print(f"  {f['name'][0]}  —  {human_size(f['size'][0])}")