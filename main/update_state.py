import json
from datetime import date

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
