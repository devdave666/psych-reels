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
BASE_URL = "https://devdave666.github.io/psych-reels/editorial/output"

with open('_selected_index.txt') as f:
    idx = f.read().strip()
with open('_selected_hashtags.txt') as f:
    hashtags = f.read()
with open('_total_slides.txt') as f:
    total_slides = int(f.read().strip())
try:
    with open('_selected_cta.txt') as f:
        cta = f.read().strip()
except FileNotFoundError:
    cta = ''

# Build the caption from the first paragraph of the body (a natural hook) + CTA + hashtags
with open('_selected_body.txt') as f:
    body = f.read()
first_para = body.split('\n\n')[0]
cta_block = f"\n\n{cta}" if cta else ""
caption = f"{first_para}{cta_block}\n\n{hashtags}"

slide_urls = [f"{BASE_URL}/row-{idx}-slide{i}.png" for i in range(1, total_slides + 1)]

def ig_request(endpoint, params):
    resp = requests.post(f"https://graph.instagram.com/v23.0/{endpoint}", data=params)
    data = resp.json()
    if "error" in data:
        raise Exception(f"Instagram error: {data['error']}")
    return data

# --- Instagram ---
if total_slides == 1:
    container = ig_request(f"{IG_USER_ID}/media", {
        "image_url": slide_urls[0],
        "caption": caption,
        "access_token": IG_TOKEN
    })
    creation_id = container["id"]
else:
    child_ids = []
    for url in slide_urls:
        child = ig_request(f"{IG_USER_ID}/media", {
            "image_url": url,
            "is_carousel_item": "true",
            "access_token": IG_TOKEN
        })
        child_ids.append(child["id"])
        time.sleep(2)
    container = ig_request(f"{IG_USER_ID}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(child_ids),
        "caption": caption,
        "access_token": IG_TOKEN
    })
    creation_id = container["id"]

# Poll for status
for _ in range(15):
    time.sleep(5)
    status = requests.get(
        f"https://graph.instagram.com/v23.0/{creation_id}",
        params={"fields": "status_code", "access_token": IG_TOKEN}
    ).json()
    if status.get("status_code") == "FINISHED":
        break
else:
    raise Exception("Instagram container never finished processing")

publish = ig_request(f"{IG_USER_ID}/media_publish", {
    "creation_id": creation_id,
    "access_token": IG_TOKEN
})
print(f"Instagram published: {publish['id']}")

# --- Buffer: X, Threads, Pinterest ---
def buffer_post(channel_id, text, image_url=None, board_id=None):
    query_input = {
        "text": text,
        "channelId": channel_id,
        "schedulingType": "automatic",
        "mode": "shareNow",
    }
    gql_parts = [
        f'text: "{text}"'.replace("\n", "\\n"),
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

caption_escaped = caption.replace('"', '\\"')
x_id = buffer_post(X_CHANNEL_ID, caption_escaped)
print(f"X posted: {x_id}")

threads_id = buffer_post(THREADS_CHANNEL_ID, caption_escaped)
print(f"Threads posted: {threads_id}")

pin_id = buffer_post(PINTEREST_CHANNEL_ID, caption_escaped, image_url=slide_urls[0], board_id=PINTEREST_BOARD_ID)
print(f"Pinterest posted: {pin_id}")

print("ALL_PLATFORMS_SUCCESS")
