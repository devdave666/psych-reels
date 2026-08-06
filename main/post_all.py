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
LANDING_PAGE_URL = "https://thb.kit.com/ac3784a0f7"

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

# Every 6th post, add a soft CTA to the social caption pointing at the free guide.
# Not every post, so it doesn't read as spam, but frequent enough to actually convert.
try:
    _id_num = int(row_id)
except ValueError:
    _id_num = 0
SOFT_CTA_DUE = (_id_num % 6 == 0)
SOFT_CTA_LINE = "\n\nFree guide - 12 ancient practices modern psychology confirmed. Link in bio."

caption = f"{text}\n\n{hashtags}"
if SOFT_CTA_DUE:
    caption += SOFT_CTA_LINE

video_url = f"{BASE_URL}/videos/main-{row_id}.mp4"
pin_url = f"{BASE_URL}/pins/main-{row_id}.png"


def ig_request(endpoint, params):
    resp = requests.post(f"https://graph.instagram.com/v23.0/{endpoint}", data=params)
    data = resp.json()
    if "error" in data:
        raise Exception(f"Instagram error: {data['error']}")
    return data


# --- Instagram Reel ---
# Container creation + processing occasionally errors transiently on
# Instagram's own side (confirmed August 6: the exact same video file
# succeeded immediately on a fresh retry with no changes at all). So the
# whole create+poll cycle gets a few attempts with a fresh container each
# time, rather than giving up after the first failure.
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

            for _ in range(20):
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

# Mark that the primary platform succeeded, independent of the secondary
# platforms below - update_state.py checks this before advancing the cursor.
with open('_instagram_success.txt', 'w') as f:
    f.write('true')


# --- Buffer: X, Threads, Pinterest ---
def buffer_post(channel_id, text_content, image_url=None, board_id=None, pin_title=None, dest_url=None):
    gql_parts = [
        f'text: "{text_content}"'.replace("\n", "\\n"),
        f'channelId: "{channel_id}"',
        'schedulingType: automatic',
        'mode: shareNow',
    ]
    if image_url:
        gql_parts.append(f'assets: {{ image: {{ url: "{image_url}" }} }}')
    if board_id:
        meta = f'metadata: {{ pinterest: {{ boardServiceId: "{board_id}"'
        if pin_title:
            meta += f', title: "{pin_title}"'
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


def buffer_post_with_retry(channel_id, text_content, image_url=None, board_id=None, pin_title=None, dest_url=None, retries=3):
    last_error = None
    for attempt in range(retries):
        try:
            return buffer_post(channel_id, text_content, image_url, board_id, pin_title, dest_url)
        except Exception as e:
            last_error = e
            print(f"Attempt {attempt+1} failed: {e}, retrying in {(attempt+1)*8}s...")
            time.sleep((attempt + 1) * 8)
    raise last_error


caption_escaped = caption.replace('"', '\\"')

# Safety net: even though no current entry exceeds X's 280-char limit, this
# protects against any future longer content (e.g. a soft-CTA line pushing
# a borderline-length quote over) without needing to notice it manually.
X_LIMIT = 280
if len(caption) <= X_LIMIT:
    x_caption = caption
else:
    reserve = len(f"\n\n{hashtags}")
    available = X_LIMIT - reserve - 1
    trimmed = text[:available].rsplit(" ", 1)[0].rstrip(",.;: ") + "..."
    x_caption = f"{trimmed}\n\n{hashtags}"
    if len(x_caption) > X_LIMIT:
        x_caption = x_caption[:X_LIMIT]

failures = []

try:
    x_id = buffer_post_with_retry(X_CHANNEL_ID, x_caption.replace('"', '\\"'))
    print(f"X posted: {x_id}")
except Exception as e:
    print(f"X FAILED (continuing anyway): {e}")
    failures.append(f"X: {e}")

try:
    threads_id = buffer_post_with_retry(THREADS_CHANNEL_ID, caption_escaped)
    print(f"Threads posted: {threads_id}")
except Exception as e:
    print(f"Threads FAILED (continuing anyway): {e}")
    failures.append(f"Threads: {e}")

try:
    # Pinterest ranks on keywords in titles/descriptions, not hashtags (~1% of ranking).
    # So Pinterest gets its own SEO-optimized copy rather than reusing the social caption.
    import pinterest_seo
    import board_router

    with open('_selected_attribution.txt') as f:
        attribution = f.read()
    with open('_selected_source.txt') as f:
        source = f.read()

    pin_title = pinterest_seo.build_title(text, attribution, content_type, row_id)
    pin_description = pinterest_seo.build_description(text, attribution, source, content_type, row_id)
    routed_board_id = board_router.route(attribution, content_type, text, row_id)

    pin_id = buffer_post_with_retry(
        PINTEREST_CHANNEL_ID,
        pin_description.replace('"', '\\"'),
        image_url=pin_url,
        board_id=routed_board_id,
        pin_title=pin_title.replace('"', '\\"'),
        dest_url=LANDING_PAGE_URL
    )
    print(f"Pinterest posted: {pin_id}")
    print(f"  title: {pin_title}")
    print(f"  board: {routed_board_id}")
except Exception as e:
    print(f"Pinterest FAILED (continuing anyway): {e}")
    failures.append(f"Pinterest: {e}")

if failures:
    print("ALL_PLATFORMS_PARTIAL_FAILURE: " + " | ".join(failures))
    sys.exit(1)

print("ALL_PLATFORMS_SUCCESS")
