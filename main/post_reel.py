import os
import time
import requests

# Generic one-off Instagram reel post: videos/<NAME>.mp4 with caption captions/<NAME>.txt (NAME comes from the workflow input).
# Does not touch main/content.json or main/state.json.
IG_TOKEN = os.environ['INSTAGRAM_ACCESS_TOKEN']
IG_USER_ID = os.environ['INSTAGRAM_USER_ID']
NAME = os.environ['REEL_NAME']
BASE_URL = "https://devdave666.github.io/psych-reels"
video_url = f"{BASE_URL}/videos/{NAME}.mp4"
with open(f"../captions/{NAME}.txt", encoding="utf-8") as f:
    caption = f.read().strip()


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
                "media_type": "REELS", "video_url": video_url, "caption": caption, "access_token": IG_TOKEN})["id"]
            print(f"Container created (attempt {attempt}): {creation_id}")
            for _ in range(50):
                time.sleep(6)
                status = requests.get(f"https://graph.instagram.com/v23.0/{creation_id}",
                                      params={"fields": "status_code", "access_token": IG_TOKEN}).json()
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


creation_id = create_and_poll()
published = ig_request(f"{IG_USER_ID}/media_publish", {"creation_id": creation_id, "access_token": IG_TOKEN})
print("Published to Instagram:", published)
