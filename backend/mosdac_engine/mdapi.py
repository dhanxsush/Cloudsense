import requests
import os
import json
import time
import logging
from datetime import datetime
import re
import sys

# ===================== OPTIONAL PROGRESS BAR =====================
try:
    from tqdm.auto import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("\n[INFO] tqdm not installed. Progress will be basic.\n")

# ===================== API ENDPOINTS =====================
TOKEN_URL = "https://mosdac.gov.in/download_api/gettoken"
SEARCH_URL = "https://mosdac.gov.in/apios/datasets.json"
CHECK_INTERNET_URL = "https://mosdac.gov.in/download_api/check-internet"
DOWNLOAD_URL = "https://mosdac.gov.in/download_api/download"
REFRESH_URL = "https://mosdac.gov.in/download_api/refresh-token"
LOGOUT_URL = "https://mosdac.gov.in/download_api/logout"

# ===================== JSON FIXER =====================
def preprocess_json(raw_json):
    fixed = re.sub(r'(?<!\\)\\(?![\\/"bfnrtu])', r'\\\\', raw_json)
    fixed = re.sub(r'(?<!\\)\\(?=\s*")', r'\\\\', fixed)
    return fixed

# ===================== LOAD CONFIG =====================
def load_config():
    if not os.path.exists("config.json"):
        print("[ERROR] config.json not found")
        sys.exit(1)

    raw = open("config.json", "r").read()
    try:
        cfg = json.loads(raw)
    except json.JSONDecodeError:
        cfg = json.loads(preprocess_json(raw))

    for key in ["user_credentials", "search_parameters"]:
        if key not in cfg:
            print(f"[ERROR] Missing '{key}' in config.json")
            sys.exit(1)

    cfg.setdefault("download_settings", {"download_path": ""})
    return cfg

config = load_config()

# ===================== CONFIG VALUES =====================
creds = config["user_credentials"]
username = creds.get("username/email", "")
password = creds.get("password", "")

search = config["search_parameters"]
datasetId = search.get("datasetId", "")
startTime = search.get("startTime", "")
endTime = search.get("endTime", "")
count = search.get("count", "")
boundingBox = search.get("boundingBox", "")
gId = search.get("gId", "")

if not datasetId:
    print("[ERROR] datasetId is required")
    sys.exit(1)

settings = config["download_settings"]
download_path = os.path.abspath(
    settings.get("download_path") or os.path.join(os.getcwd(), "MOSDAC_Data")
)

use_date_structure = settings.get("organize_by_date", False)
skip_user_input = settings.get("skip_user_input", False)
generate_logs = settings.get("generate_error_logs", False)

# ===================== LOGGING =====================
logger = logging.getLogger("mosdac_downloader")
logger.setLevel(logging.ERROR)

if generate_logs:
    os.makedirs("error_logs", exist_ok=True)
    handler = logging.FileHandler(
        f"error_logs/{datetime.now().strftime('%d-%m-%Y')}_error.log"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    ))
    logger.addHandler(handler)
    logger.propagate = False

# ===================== SESSION =====================
session = requests.Session()

# ===================== TOKEN =====================
def get_token():
    r = session.post(TOKEN_URL, json={"username": username, "password": password})
    if r.status_code != 200:
        print("[ERROR] Login failed:", r.text)
        sys.exit(1)
    return r.json()

# ===================== SEARCH =====================
def search_results():
    params = {"datasetId": datasetId}
    for k, v in {
        "startTime": startTime,
        "endTime": endTime,
        "count": count,
        "boundingBox": boundingBox,
        "gId": gId
    }.items():
        if v:
            params[k] = v

    r = session.get(SEARCH_URL, params=params)
    r.raise_for_status()
    data = r.json()

    total = data["itemsPerPage"] if count else data["totalResults"]
    size_mb = data["totalSizeMB"]

    print(f"\nFound {total} files | Total size: {size_mb:.2f} MB")
    return total

# ===================== DOWNLOAD =====================
def download_file(token, record_id, identifier, prod_date, idx, total):
    headers = {"Authorization": f"Bearer {token}"}
    params = {"id": record_id}

    if use_date_structure and prod_date:
        dt = datetime.strptime(prod_date, "%Y-%m-%dT%H:%M:%SZ")
        folder = os.path.join(
            download_path,
            datasetId,
            dt.strftime("%Y"),
            dt.strftime("%d%b").upper()
        )
    else:
        folder = download_path

    os.makedirs(folder, exist_ok=True)
    final_path = os.path.join(folder, identifier)
    temp_path = final_path + ".part"

    if os.path.exists(final_path):
        print(f"[SKIP] {identifier}")
        return True

    r = session.get(
        DOWNLOAD_URL,
        headers=headers,
        params=params,
        stream=True,
        timeout=(5, 300)
    )

    if r.status_code == 401:
        return "TOKEN_EXPIRED"

    r.raise_for_status()
    total_size = int(r.headers.get("Content-Length", 0))

    print(f"\n[{idx}/{total}] Downloading {identifier}")

    try:
        with open(temp_path, "wb") as f:
            if HAS_TQDM:
                with tqdm(total=total_size, unit="B", unit_scale=True) as bar:
                    for chunk in r.iter_content(1024 * 1024):
                        if chunk:
                            f.write(chunk)
                            bar.update(len(chunk))
            else:
                for chunk in r.iter_content(1024 * 1024):
                    if chunk:
                        f.write(chunk)

        os.rename(temp_path, final_path)
        return True

    except KeyboardInterrupt:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

# ===================== MAIN =====================
def main():
    total_files = search_results()

    if not skip_user_input:
        resp = input("Proceed with download? [Y/N]: ").lower()
        if resp not in ("y", "yes"):
            print("Cancelled.")
            return

    tokens = get_token()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    print(f"Logged in as {username}")

    params = {"datasetId": datasetId}
    idx = 1
    downloaded = 0

    while idx <= total_files:
        params["startIndex"] = idx
        r = session.get(SEARCH_URL, params=params)
        r.raise_for_status()
        data = r.json()

        for item in data["entries"]:
            res = download_file(
                access_token,
                item["id"],
                item["identifier"],
                item.get("updated"),
                idx,
                total_files
            )

            if res == "TOKEN_EXPIRED":
                tokens = session.post(REFRESH_URL, json={"refresh_token": refresh_token}).json()
                access_token = tokens["access_token"]
                refresh_token = tokens["refresh_token"]
                continue

            if res:
                downloaded += 1

            idx += 1

    print(f"\nDownload complete. Files downloaded: {downloaded}")
    session.post(LOGOUT_URL, json={"username": username})
    print("Logged out.")

if __name__ == "__main__":
    main()