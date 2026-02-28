"""Supprime les fichiers en double sur le Drive (mise à la corbeille)."""
import os
from pathlib import Path
from collections import defaultdict

os.environ["STORAGE_MODE"] = "gdrive"
os.environ["GDRIVE_DOCS_FOLDER_ID"] = "13yJ3buMzf03ZzLvV4aVqvVZHfyBxoCHM"
os.environ["GDRIVE_DATA_FOLDER_ID"] = "1iAd50S-eZU1YE5gn7PYkaKf9N9jeQ28b"
os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"] = str(
    Path(__file__).parent.parent / "memoires-tech-index-db8b0704b979.json"
)

from google.oauth2 import service_account
from googleapiclient.discovery import build
import config

creds = service_account.Credentials.from_service_account_file(
    os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"],
    scopes=["https://www.googleapis.com/auth/drive"],
)
service = build("drive", "v3", credentials=creds)

# Charger l'index pour savoir quels IDs garder
storage = config.get_storage()
index = storage.read_json("index")
keep_ids = set()
for doc in index.get("documents", []):
    gid = doc.get("gdrive_file_id")
    if gid:
        keep_ids.add(gid)

print(f"IDs references dans l'index: {len(keep_ids)}")

# Lister tous les fichiers du dossier documents (sans cache)
docs_folder_id = config.GDRIVE_DOCS_FOLDER_ID
all_files = []
page_token = None
while True:
    resp = (
        service.files()
        .list(
            q=f"'{docs_folder_id}' in parents and trashed = false",
            spaces="drive",
            fields="nextPageToken, files(id, name)",
            pageSize=1000,
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    all_files.extend(resp.get("files", []))
    page_token = resp.get("nextPageToken")
    if not page_token:
        break

print(f"Fichiers dans le Drive: {len(all_files)}")

# Grouper par nom, identifier les doublons non référencés
by_name = defaultdict(list)
for f in all_files:
    by_name[f["name"]].append(f)

to_delete = []
for name, files in by_name.items():
    if len(files) <= 1:
        continue
    for f in files:
        if f["id"] not in keep_ids:
            to_delete.append(f)

print(f"Fichiers a mettre a la corbeille: {len(to_delete)}")

trashed = 0
errors = 0
for f in to_delete:
    try:
        service.files().update(
            fileId=f["id"],
            body={"trashed": True},
            supportsAllDrives=True,
        ).execute()
        trashed += 1
        if trashed % 20 == 0:
            print(f"  {trashed} mis a la corbeille...")
    except Exception as e:
        errors += 1
        print(f"  ERREUR {f['name']}: {e}")

print(f"\nTermine: {trashed} mis a la corbeille, {errors} erreurs")
