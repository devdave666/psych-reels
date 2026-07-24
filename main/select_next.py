import json
import sys

with open('content.json') as f:
    content = json.load(f)
with open('state.json') as f:
    state = json.load(f)

cursor = state['cursor']
n = len(content)

for offset in range(n):
    idx = (cursor + offset) % n
    if not content[idx]['used']:
        entry = content[idx]
        print(f"ENTRY_INDEX={idx}")
        with open('_selected_index.txt', 'w') as f:
            f.write(str(idx))
        with open('_selected_id.txt', 'w') as f:
            f.write(str(entry['id']))
        with open('_selected_text.txt', 'w') as f:
            f.write(entry['text'])
        with open('_selected_attribution.txt', 'w') as f:
            f.write(entry['attribution'])
        with open('_selected_source.txt', 'w') as f:
            f.write(entry['source'])
        with open('_selected_type.txt', 'w') as f:
            f.write(entry['type'])
        sys.exit(0)

print("ERROR: no unused content left")
sys.exit(1)
