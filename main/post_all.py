import os
import sys
import time
import requests

IG_TOKEN = os.environ['INSTAGRAM_ACCESS_TOKEN']
IG_USER_ID = os.environ['INSTAGRAM_USER_ID']
BUFFER_TOKEN = os.environ['BUFFER_API_KEY']
X_CHANNEL_ID = os.environ['BUFFER_X_CHANNEL_ID']
THREADS_CHANNEL_ID = os.environ['BUFFER_THREADS_CHANNEL_ID']
PINTEREST_CHANNEL_ID = os.environ['BUFFER_PINTEREST_CHANNEL_ID']
PINTEREST_BOARD_ID = os.environ['BUFFER_PINTEREST_BOARD_ID']
BASE_URL = "https://devdave666.github.io/psych-reels"

with open('_selected_id.txt') as f:
    row_id = f.read().strip()
with open('_selected_text.txt') as f:
    text = f.read()
with open('_selected_type.txt') as f:
    content_type = f.read().strip()

if content_type == "quote":
    hashtags = "#philosophy #psychology"
else:
    hashtags = "#psychology #philosophy"

caption = f"{text}\n\n{hashtags}"
video_url = f"{BASE_URL}/videos/main-{row_id}.mp4"
pin_url = f"{BASE_URL}/pins/main-{row_id}.png"


def ig_request(endpoint, params):
    resp = requests.post(f"https://graph.instagram.com/v23.0/{endpoint}", data=params)
    data = resp.json()
    if "error" in data:
        raise Exception(f"Instagram error: {data['error']}")
    return data


# --- Instagram Reel ---
container = ig_request(f"{IG_USER_ID}/media", {
    "media_type": "REELS",
    "video_url": video_url,
    "caption": caption,
    "access_token": IG_TOKEN
})
creation_id = container["id"]
print(f"Instagram container created: {creation_id}")

for _ in range(20):
    time.sleep(6)
    status = requests.get(
        f"https://graph.instagram.com/v23.0/{creation_id}",
        params={"fields": "status_code", "access_token": IG_TOKEN}
    ).json()
    if status.get("status_code") == "FINISHED":
        break
    if status.get("status_code") == "ERROR":
        raise Exception(f"Instagram container errored: {status}")
else:
    raise Exception("Instagram container never finished processing")

publish = ig_request(f"{IG_USER_ID}/media_publish", {
    "creation_id": creation_id,
    "access_token": IG_TOKEN
})
print(f"Instagram published: {publish['id']}")


# --- Buffer: X, Threads, Pinterest ---
def buffer_post(channel_id, text_content, image_url=None, board_id=None):
    gql_parts = [
        f'text: "{text_content}"'.replace("\n", "\\n"),
        f'channelId: "{channel_id}"',
        'schedulingType: automatic',
        'mode: shareNow',
    ]
    if image_url:
        gql_parts.append(f'assets: {{ image: {{ url: "{image_url}" }} }}')
    if board_id:
        gql_parts.append(f'metadata: {{ pinterest: {{ boardServiceId: "{board_id}" }} }}')
    query = (
        "mutation CreatePost { createPost(input: { " + ", ".join(gql_parts) +
        " }) { ... on PostActionSuccess { post { id } } ... on MutationError { message } } }"
    )
    resp = requests.post(
        "https://api.buffer.com",
        headers={"Authorization": f"Bearer {BUFFER_TOKEN}", "Content-Type": "application/json"},
        json={"query": query}
    )
    data = resp.json()
    if "errors" in data:
        raise Exception(f"Buffer error: {data['errors']}")
    result = data["data"]["createPost"]
    if "message" in result:
        raise Exception(f"Buffer post failed: {result['message']}")
    return result["post"]["id"]


def buffer_post_with_retry(channel_id, text_content, image_url=None, board_id=None, retries=3):
    last_error = None
    for attempt in range(retries):
        try:
            return buffer_post(channel_id, text_content, image_url, board_id)
        except Exception as e:
            last_error = e
            print(f"Attempt {attempt+1} failed: {e}, retrying in {(attempt+1)*8}s...")
            time.sleep((attempt + 1) * 8)
    raise last_error


caption_escaped = caption.replace('"', '\\"')

x_id = buffer_post_with_retry(X_CHANNEL_ID, caption_escaped)
print(f"X posted: {x_id}")

threads_id = buffer_post_with_retry(THREADS_CHANNEL_ID, caption_escaped)
print(f"Threads posted: {threads_id}")

pin_id = buffer_post_with_retry(PINTEREST_CHANNEL_ID, caption_escaped, image_url=pin_url, board_id=PINTEREST_BOARD_ID)
print(f"Pinterest posted: {pin_id}")

print("ALL_PLATFORMS_SUCCESS")
