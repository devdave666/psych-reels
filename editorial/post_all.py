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
def create_and_poll_instagram_container(max_attempts=3):
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
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

            print(f"Instagram container created (attempt {attempt}): {creation_id}")
            # 50 polls x 6s = 300s (5 min) per attempt - increased 2026-08-11,
            # see main/post_all.py for the reasoning (timeout, not error, was
            # the actual failure mode observed - needed more patience, not
            # more fresh containers).
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
print(f"Instagram published: {publish['id']}")

# Mark that the primary platform succeeded, independent of whatever happens
# with the secondary platforms below. update_state.py checks for this before
# advancing the cursor - so a Buffer failure can never accidentally mark
# unposted content as used, and an Instagram failure can never accidentally
# advance past content Instagram itself never received.
with open('_instagram_success.txt', 'w') as f:
    f.write('true')

# Fetch the real permalink so Pinterest can link directly to this exact post
permalink_data = requests.get(
    f"https://graph.instagram.com/v23.0/{publish['id']}",
    params={"fields": "permalink", "access_token": IG_TOKEN}
).json()
ig_permalink = permalink_data.get("permalink", "https://www.instagram.com/the_higher_being/")
print(f"Instagram permalink: {ig_permalink}")

# --- Buffer: X, Threads, Pinterest ---
def buffer_post(channel_id, text, image_url=None, board_id=None, dest_url=None):
    gql_parts = [
        f'text: "{text}"'.replace("\n", "\\n"),
        f'channelId: "{channel_id}"',
        'schedulingType: automatic',
        'mode: shareNow',
    ]
    if image_url:
        gql_parts.append(f'assets: {{ image: {{ url: "{image_url}" }} }}')
    if board_id:
        meta = f'metadata: {{ pinterest: {{ boardServiceId: "{board_id}"'
        if dest_url:
            meta += f', url: "{dest_url}"'
        meta += ' } }'
        gql_parts.append(meta)
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

# X has a hard 280-char limit; editorial captions (first paragraph + CTA + hashtags)
# regularly exceed this, unlike the short daily quotes/facts. Build a safe, shortened
# version specifically for X rather than assuming the full caption always fits.
X_LIMIT = 280
if len(caption) <= X_LIMIT:
    x_caption = caption
else:
    reserve = len(f"\n\n{hashtags}")
    available = X_LIMIT - reserve - 1
    trimmed = first_para[:available].rsplit(" ", 1)[0].rstrip(",.;: ") + "..."
    x_caption = f"{trimmed}\n\n{hashtags}"
    if len(x_caption) > X_LIMIT:
        x_caption = x_caption[:X_LIMIT]
print(f"X caption length: {len(x_caption)}")

# Each platform attempted independently: one failing must never block the others,
# and must never prevent the row from being marked used (Instagram, the primary
# platform, already succeeded by this point).
failures = []

try:
    x_id = buffer_post(X_CHANNEL_ID, x_caption.replace('"', '\\"'))
    print(f"X posted: {x_id}")
except Exception as e:
    print(f"X FAILED (continuing anyway): {e}")
    failures.append(f"X: {e}")

try:
    threads_id = buffer_post(THREADS_CHANNEL_ID, caption_escaped)
    print(f"Threads posted: {threads_id}")
except Exception as e:
    print(f"Threads FAILED (continuing anyway): {e}")
    failures.append(f"Threads: {e}")

try:
    teaser_url = f"{BASE_URL}/row-{idx}-pinterest-teaser.png"
    pinterest_caption = f"{caption}\n\nFull story on Instagram: @the_higher_being"
    pin_id = buffer_post(
        PINTEREST_CHANNEL_ID,
        pinterest_caption.replace('"', '\\"'),
        image_url=teaser_url,
        board_id=PINTEREST_BOARD_ID,
        dest_url=ig_permalink
    )
    print(f"Pinterest posted: {pin_id}")
except Exception as e:
    print(f"Pinterest FAILED (continuing anyway): {e}")
    failures.append(f"Pinterest: {e}")

if failures:
    print("ALL_PLATFORMS_PARTIAL_FAILURE: " + " | ".join(failures))
    # Non-zero exit for visibility in the Actions log, but this happens only
    # AFTER every platform was attempted, and the workflow marks state as
    # used regardless (see workflow's if: always() on that step).
    sys.exit(1)

print("ALL_PLATFORMS_SUCCESS")
