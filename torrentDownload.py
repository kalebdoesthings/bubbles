import zipfile, os
import requests
from dotenv import load_dotenv
import time

from concurrent.futures import ThreadPoolExecutor

progress = {}









ALLOWED = {
    # video
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".flv", ".wmv",
    # audio
    ".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a",
    # captions / subtitles
    ".srt", ".vtt", ".sub", ".ass", ".ssa",
    # images
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
}




os.makedirs("downloads", exist_ok=True)

load_dotenv()
apikey = os.environ["TORBOX_API_KEY"]




    






def requestDlTorrentLink(torrentID, name):
    progress[torrentID]["state"] = "requesting dl link"
    requestDownloadResp = requests.get(
        "https://api.torbox.app/v1/api/torrents/requestdl",
        params={
            "token": apikey,
            "torrent_id": torrentID,
            "zip_link": "true",
        },
        timeout=30,
    )
    requestDownloadResp.raise_for_status()




    data = requestDownloadResp.json()
    downloadLink = data["data"]
    
    progress[torrentID]["state"] = f"received dl link {downloadLink}"
    downloadTorrent(downloadLink, name, torrentID)



def downloadTorrent(downloadLink, name, torrentID):
    progress[torrentID]["state"] = "downloading"
    path = os.path.join("downloads", f"{name}.zip")     
    with requests.get(downloadLink, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            total = int(r.headers.get("Content-Length", 0))
            done = 0
            for chunk in r.iter_content(chunk_size=1024 * 1024):  # 1 MB chunks
                f.write(chunk)
                done += len(chunk)
                if total:
                    progress[torrentID]["percent"] = done / total * 100
    progress[torrentID]["state"] = "Download Finished!"
    unzip(f"downloads/{name}.zip", dest=f"downloads/", torrentID=torrentID)
    progress[torrentID]["state"] = "removing archive"
    os.remove(f"downloads/{name}.zip")
    progress[torrentID]["state"] = "removed archive"
    removeTorrent(torrentID)


def unzip(path, torrentID, dest="downloads"):
    progress[torrentID]["state"] = "extracting"
    with zipfile.ZipFile(path, "r") as z:
        for member in z.namelist():
            if member.endswith("/"):
                continue  # skip directory entries
            ext = os.path.splitext(member)[1].lower()
            if ext in ALLOWED:
                z.extract(member, dest)
            else:
                print(f"Skipped {member}")
    print(f"Extracted media to {dest}")
    progress[torrentID]["state"] = "extracted!"

def removeTorrent(torrentID, attempts=6):
    # Right after a torrent finishes, TorBox is still finalizing it internally,
    # so a delete can race that and return 500 DATABASE_ERROR. Retry with
    # exponential backoff to give their side time to settle.
    for attempt in range(attempts):
        progress[torrentID]["state"] = f"removing torrent (try {attempt + 1}/{attempts})"
        resp = requests.post(
            "https://api.torbox.app/v1/api/torrents/controltorrent",
            headers={"Authorization": f"Bearer {apikey}"},
            json={"torrent_id": torrentID, "operation": "delete"},
            timeout=30,
        )
        if resp.ok:
            print(f"Deleted torrent {torrentID}")
            progress[torrentID]["state"] = "torrent removed!"
            return
        wait = min(2 ** attempt, 30)   # 1, 2, 4, 8, 16, 30, ... capped
        print(f"delete attempt {attempt + 1} failed: {resp.status_code} {resp.text} — retrying in {wait}s")
        time.sleep(wait)

    # all retries failed — surface it instead of freezing silently
    progress[torrentID]["state"] = f"remove failed: {resp.status_code}"
    
    



def addTorrent(magnet):
    for magnetLink in magnet:
        torrentAddResp = requests.post(
                "https://api.torbox.app/v1/api/torrents/asynccreatetorrent",
                headers={"Authorization": f"Bearer {apikey}"},
                data={"magnet": magnetLink, "seed": 3, "allow_zip": "true"},  # 3 = never seed
                timeout=30,
                )
        torrentAddResp.raise_for_status()

        data = torrentAddResp.json()
        print(data)
    processTorrent()






def processTorrent():
    submitted = set()
    pool = ThreadPoolExecutor(max_workers=4)
    while True:
        resp = requests.get(
            "https://api.torbox.app/v1/api/torrents/mylist",
            headers={"Authorization": f"Bearer {apikey}"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

       
        print("\033[2J\033[H", end="")

        all_ready = True
        for t in data["data"]:
            torrentID = t.get("id")
            name  = t.get("name", "?")
            pct   = (t.get("progress") or 0) * 100
            state = t.get("download_state", "unknown")
            ready = t.get("download_present")
            print(f"id={t.get('id')}  {name}: {pct:.1f}%  [{state}]  ready={ready}")
            if torrentID not in progress:
                progress[torrentID] = {"name": name, "torrentID": torrentID, "pct": 0, "state": "starting"}
            if not ready:
                all_ready = False
            if ready and torrentID not in submitted:
                submitted.add(torrentID)
                progress[torrentID]["state"] = "starting"
                pool.submit(handleTorrent, torrentID, name)
                

        if all_ready and data["data"]:
            print("All ready! Waiting for downloads to finish...")
            break

        time.sleep(2)

    pool.shutdown(wait=True)   # block until every download thread completes
    print("All downloads complete.")



def handleTorrent(torrentID, name):
    requestDlTorrentLink(torrentID, name)
    print(f"Finished {name}")
    progress[torrentID]["state"] = "finished"


