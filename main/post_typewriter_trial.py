"""One-off Instagram-only post of the typewriter trial reel.

Same container create + poll + publish flow as post_all.py, but posts only
to Instagram (no Buffer/X/Threads/Pinterest) and never touches
content.json / state.json. Row id comes from the ROW_ID env var.
"""
import json
import os
import time

import requests

IG_TOKEN = os.environ['INSTAGRAM_ACCESS_TOKEN']
IG_USER_ID = os.environ['INSTAGRAM_USER_ID']
ROW_ID = os.environ['ROW_ID']
BASE_URL = "https://devdave666.github.io/psych-reels"

with open('content.json') as f:
    entry = next(e for e in json.load(f) if str(e['id']) == ROW_ID)

hashtags = "#philosophy #psychology" if entry['type'] == "quote" else "#psychology #philosophy"
caption = f"{entry['text']}\n\n{hashtags}"
video_url = f"{BASE_URL}/videos/typewriter-trial-{ROW_ID}.mp4"


def ig_request(endpoint, params):
    data = requests.post(f"https://graph.instagram.com/v23.0/{endpoint}", data=params).json()
    if "error" in data:
        raise Exception(f"Instagram error: {data['error']}")
    return data


def create_and_poll(max_attempts=3):
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            creation_id = ig_request(f"{IG_USER_ID}/media", {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "access_token": IG_TOKEN,
            })["id"]
            print(f"Container created (attempt {attempt}): {creation_id}")
            for _ in range(50):
                time.sleep(6)
                status = requests.get(
                    f"https://graph.instagram.com/v23.0/{creation_id}",
                    params={"fields": "status_code", "access_token": IG_TOKEN},
                ).json()
                if status.get("status_code") == "FINISHED":
                    return creation_id
                if status.get("status_code") == "ERROR":
                    raise Exception(f"Container errored: {status}")
            raise Exception("Container never finished processing")
        except Exception as e:
            last_error = e
            print(f"Attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                time.sleep(20 * attempt)
    raise last_error


print(f"Posting {video_url}")
creation_id = create_and_poll()
media_id = ig_request(f"{IG_USER_ID}/media_publish", {
    "creation_id": creation_id,
    "access_token": IG_TOKEN,
})["id"]
print(f"Instagram published: {media_id}")
permalink = requests.get(
    f"https://graph.instagram.com/v23.0/{media_id}",
    params={"fields": "permalink", "access_token": IG_TOKEN},
).json()
print(f"Permalink: {permalink.get('permalink', '(unavailable, check profile grid)')}")
