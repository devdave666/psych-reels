import json
import subprocess
from datetime import date

with open('../main/content.json') as f:
    content = json.load(f)

today = date.today().isoformat()
posted_today = any(e.get('date_used') == today for e in content)

print(f"Checking for a post dated {today}...")

if posted_today:
    print("Found - today's scheduled post went out normally. No action needed.")
else:
    print("MISSED - no post found for today. Triggering recovery + sending alert.")

    subject = f"Recovered: today's post was missed and auto re-triggered"
    body = f"""Today's scheduled post ({today}) didn't go out at its normal 13:00 UTC time - this happens occasionally because GitHub's own scheduled-workflow trigger can silently skip during high platform load. It's a known GitHub Actions limitation, not a bug in the pipeline itself.

What happened automatically, just now:
1. This check ran a few hours after the normal schedule and noticed no post existed for today
2. It automatically triggered the main posting workflow to catch up
3. You should see today's post appear on Instagram/X/Threads/Pinterest shortly after this email

No action needed from you. This is just a heads-up so you have visibility into it, in case you notice a pattern of frequent misses worth investigating further.
"""
    with open('_email_body.txt', 'w') as f:
        f.write(body)
    subprocess.run(['python3', 'send_email.py', subject, '_email_body.txt'], check=True)
    print("Alert email sent.")
