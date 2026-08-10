import json
import os
import subprocess
import time
from datetime import date

import requests

with open('../main/content.json') as f:
    content = json.load(f)

today = date.today().isoformat()
posted_today = any(e.get('date_used') == today for e in content)

print(f"Checking for a post dated {today}...")

if posted_today:
    print("Found - today's scheduled post went out normally. No action needed.")
    raise SystemExit(0)

print("MISSED - no post found for today. Triggering recovery and verifying the actual outcome before emailing.")

GITHUB_TOKEN = os.environ['GH_TOKEN']
REPO = os.environ.get('GITHUB_REPOSITORY', 'devdave666/psych-reels')
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}

dispatch_time = time.time()
resp = requests.post(
    f"https://api.github.com/repos/{REPO}/actions/workflows/main-daily-post.yml/dispatches",
    headers=HEADERS,
    json={"ref": "main"}
)
print(f"Dispatch triggered: {resp.status_code}")

run_id = None
for _ in range(10):
    time.sleep(5)
    runs = requests.get(
        f"https://api.github.com/repos/{REPO}/actions/workflows/main-daily-post.yml/runs",
        headers=HEADERS,
        params={"event": "workflow_dispatch", "per_page": 1}
    ).json()
    if runs.get("workflow_runs"):
        candidate = runs["workflow_runs"][0]
        created = time.mktime(time.strptime(candidate["created_at"], "%Y-%m-%dT%H:%M:%SZ"))
        if created >= dispatch_time - 10:
            run_id = candidate["id"]
            break

if run_id is None:
    subject = "Action needed: today's post was missed, and I couldn't confirm the recovery attempt"
    body = f"""Today's scheduled post ({today}) didn't go out, and I triggered a recovery run, but couldn't find/confirm that run afterward to verify it actually worked.

Worth checking the Actions tab yourself: https://github.com/{REPO}/actions/workflows/main-daily-post.yml

If nothing posted, you may need to ask Claude to look into it directly.
"""
else:
    outcome = None
    for _ in range(36):
        time.sleep(10)
        run = requests.get(f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}", headers=HEADERS).json()
        if run.get("status") == "completed":
            outcome = run.get("conclusion")
            break

    if outcome == "success":
        subject = "Recovered: today's post was missed, auto-retry succeeded"
        body = f"""Today's scheduled post ({today}) didn't go out at its normal time - this happens occasionally, GitHub's own scheduler can skip during high platform load.

I triggered a recovery run and confirmed it completed successfully. Today's post should now be live on Instagram/X/Threads/Pinterest.

No action needed.
"""
    else:
        subject = "Action needed: today's post is still missing after an auto-retry attempt"
        body = f"""Today's scheduled post ({today}) didn't go out, and the automatic recovery attempt I triggered afterward also did not complete successfully (outcome: {outcome or 'unknown/timed out'}).

This suggests something more persistent than the usual transient GitHub-scheduler delay - possibly an ongoing issue on Instagram's own side, or something worth a closer look.

Check here: https://github.com/{REPO}/actions/workflows/main-daily-post.yml

Worth asking Claude to look into today's specific failure directly.
"""

with open('_email_body.txt', 'w') as f:
    f.write(body)
subprocess.run(['python3', 'send_email.py', subject, '_email_body.txt'], check=True)
print(f"Email sent: {subject}")
