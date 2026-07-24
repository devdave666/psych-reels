import json
import sys

with open('content.json') as f:
    content = json.load(f)
with open('state.json') as f:
    state = json.load(f)

cursor = state['cursor']

# Find next unused entry starting from cursor, wrapping around
n = len(content)
for offset in range(n):
    idx = (cursor + offset) % n
    if not content[idx]['used']:
        entry = content[idx]
        print(f"ENTRY_INDEX={idx}")
        print(f"ENTRY_ID={entry['id']}")
        # Write to files instead of stdout for reliable multi-line handling
        with open('_selected_title.txt', 'w') as f:
            f.write(entry['title'])
        with open('_selected_label.txt', 'w') as f:
            f.write(entry['label'])
        with open('_selected_body.txt', 'w') as f:
            f.write(entry['body'])
        with open('_selected_hashtags.txt', 'w') as f:
            f.write(entry['hashtags'])
        with open('_selected_index.txt', 'w') as f:
            f.write(str(idx))
        with open('_selected_cta.txt', 'w') as f:
            f.write(entry.get('cta', ''))
        sys.exit(0)

print("ERROR: no unused content left")
sys.exit(1)
