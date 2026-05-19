#!/usr/bin/env python3
"""
upload_to_youtube.py
Batch-upload rendered videos to YouTube with metadata from *_meta.json.

Prerequisites:
  1. Create a Google Cloud project, enable YouTube Data API v3.
  2. Create OAuth 2.0 Desktop credentials, download client_secret.json.
  3. Place client_secret.json in the yt_factory/ directory.
  4. Run this script. First run opens a browser for OAuth consent.
     Subsequent runs use the stored token (token.pickle).

Saves OAuth token to: token.pickle (do NOT commit to git)
"""

import json
import os
import pickle
import sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

BASE = Path(__file__).parent.resolve()
FINAL_DIR = BASE / "assets" / "final"
THUMB_DIR = BASE / "assets" / "thumbnails"
META_DIR = BASE / "scripts"
CAPTION_DIR = BASE / "assets" / "captions"
CLIENT_SECRET = BASE / "client_secret.json"
TOKEN_PATH = BASE / "token.pickle"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]

def get_credentials():
    """Load or create OAuth credentials."""
    creds = None
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET.exists():
                print(f"ERROR: {CLIENT_SECRET.name} not found.")
                print("1. Go to https://console.cloud.google.com/")
                print("2. Create project → Enable YouTube Data API v3")
                print("3. APIs & Services → Credentials → Create OAuth 2.0 Desktop app")
                print("4. Download JSON and save as client_secret.json in yt_factory/")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "wb") as token:
            pickle.dump(creds, token)
    return creds


def upload_video(service, video_path: Path, meta: dict, slug: str) -> str:
    """Upload video with metadata. Returns video ID."""
    title = meta.get("title_options", [""])[0] if meta.get("title_options") else slug
    description = meta.get("description", "")
    tags = meta.get("tags", [])

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:500],
            "categoryId": "28",  # Science & Technology
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": "private",  # Change to "public" or "unlisted" when ready
            "selfDeclaredMadeForKids": False,
        }
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    request = service.videos().insert(part="snippet,status", body=body, media_body=media)

    print(f"  Uploading {video_path.name} ...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"    {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"    -> uploaded: https://youtube.com/watch?v={video_id}")
    return video_id


def upload_thumbnail(service, video_id: str, thumb_path: Path) -> None:
    """Upload custom thumbnail for a video."""
    media = MediaFileUpload(str(thumb_path), mimetype="image/png")
    service.thumbnails().set(videoId=video_id, media_body=media).execute()
    print(f"    -> thumbnail set")


def upload_caption(service, video_id: str, caption_path: Path) -> None:
    """Upload SRT caption file."""
    body = {
        "snippet": {
            "videoId": video_id,
            "language": "en",
            "name": "English (auto)",
            "isDraft": False,
        }
    }
    media = MediaFileUpload(str(caption_path))
    service.captions().insert(part="snippet", body=body, media_body=media).execute()
    print(f"    -> captions uploaded")


def slug_from_filename(name: str) -> str:
    m = re.match(r"^(\d+)_", name)
    if m:
        return f"video_{m.group(1).zfill(2)}"
    m = re.match(r"^(video_\d+)", name)
    return m.group(1) if m else name.replace("_meta.json", "")


def main():
    if not FINAL_DIR.exists() or not any(FINAL_DIR.glob("*.mp4")):
        print(f"No MP4 files in {FINAL_DIR}. Render videos first.")
        sys.exit(1)

    print("Authenticating with YouTube API ...")
    creds = get_credentials()
    service = build("youtube", "v3", credentials=creds, cache_discovery=False)

    meta_files = sorted(META_DIR.glob("*_meta.json"))
    print(f"Uploading {len(meta_files)} videos ...\n")

    for mf in meta_files:
        slug = slug_from_filename(mf.name)
        print(f"[{slug}]")

        video_path = FINAL_DIR / f"{slug}.mp4"
        thumb_path = THUMB_DIR / f"{slug}.png"
        caption_path = CAPTION_DIR / f"{slug}.srt"

        if not video_path.exists():
            print(f"  ! Missing video: {video_path}")
            continue

        meta = json.loads(mf.read_text())

        try:
            video_id = upload_video(service, video_path, meta, slug)
            if thumb_path.exists():
                upload_thumbnail(service, video_id, thumb_path)
            if caption_path.exists():
                upload_caption(service, video_id, caption_path)
        except HttpError as e:
            print(f"  ! Upload failed: {e.resp.status} {e._get_reason()}")
        except Exception as e:
            print(f"  ! Unexpected error: {e}")

    print("\nAll uploads complete.")


if __name__ == "__main__":
    main()
