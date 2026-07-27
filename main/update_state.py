import json
import os
import sys
from datetime import date

if not os.path.exists('_instagram_success.txt'):
    print("Instagram did not succeed on this run - leaving content/state untouched so it retries next time.")
    sys.exit(0)

with open('_selected_index.txt') as f:
    idx = int(f.read().strip())

with open('content.json') as f:
    content = json.load(f)

content[idx]['used'] = True
content[idx]['date_used'] = date.today().isoformat()

with open('content.json', 'w') as f:
    json.dump(content, f, indent=2)

with open('state.json') as f:
    state = json.load(f)

n = len(content)
state['cursor'] = (idx + 1) % n

with open('state.json', 'w') as f:
    json.dump(state, f, indent=2)

print(f"Marked entry {idx} as used, cursor advanced to {state['cursor']}")
