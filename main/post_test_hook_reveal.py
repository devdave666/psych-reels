import os
import time
import requests

IG_TOKEN = os.environ['INSTAGRAM_ACCESS_TOKEN']
IG_USER_ID = os.environ['INSTAGRAM_USER_ID']
BASE_URL = "https://devdave666.github.io/psych-reels"

with open('_selected_id.txt') as f:
    row_id = f.read().strip()
with open('_selected_text.txt') as f:
    text = f.read()
with open('_selected_type.txt') as f:
    content_type = f.read().strip()

hashtags = "#philosophy #psychology" if content_type == "quote" else "#psychology #philosophy"
caption = f"{text}\n\n{hashtags}"
video_url = f"{BASE_URL}/videos/hook-{row_id}.mp4"


def ig_request(endpoint, params):
    resp = requests.post(f"https://graph.instagram.com/v23.0/{endpoint}", data=params)
    data = resp.json()
    if "error" in data:
        raise Exception(f"Instagram error: {data['error']}")
    return data


# Same create+poll-with-retry shape as main/post_all.py - IG container
# processing occasionally errors transiently, a fresh retry has always
# resolved it.
def create_and_poll_instagram_container(max_attempts=3):
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            container = ig_request(f"{IG_USER_ID}/media", {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "access_token": IG_TOKEN
            })
            creation_id = container["id"]
            print(f"Instagram container created (attempt {attempt}): {creation_id}")
            for _ in range(50):
                time.sleep(6)
                status = requests.get(
                    f"https://graph.instagram.com/v23.0/{creation_id}",
                    params={"fields": "status_code", "access_token": IG_TOKEN}
                ).json()
                if status.get("status_code") == "FINISHED":
                    return creation_id
                if status.get("status_code") == "ERROR":
                    raise Exception(f"Instagram container errored: {status}")
            else:
                raise Exception("Instagram container never finished processing")
        except Exception as e:
            last_error = e
            print(f"Attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                wait = 20 * attempt
                print(f"Retrying with a fresh container in {wait}s...")
                time.sleep(wait)
    raise last_error


creation_id = create_and_poll_instagram_container()
publish = ig_request(f"{IG_USER_ID}/media_publish", {
    "creation_id": creation_id,
    "access_token": IG_TOKEN
})
media_id = publish['id']
print(f"Instagram published: {media_id}")

permalink = requests.get(
    f"https://graph.instagram.com/v23.0/{media_id}",
    params={"fields": "permalink", "access_token": IG_TOKEN}
).json()
print(f"Permalink: {permalink.get('permalink', '(unavailable, check profile grid)')}")
