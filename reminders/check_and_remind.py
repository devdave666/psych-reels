import json
import subprocess
from datetime import date, datetime

with open('state.json') as f:
    state = json.load(f)

sent_any = False

# --- Check 1: Instagram token expiry (60-day lifespan, warn starting 5 days before) ---
issued = datetime.strptime(state['token_issued'], '%Y-%m-%d').date()
days_elapsed = (date.today() - issued).days
days_remaining = 60 - days_elapsed

if days_remaining <= 5:
    subject = f"Action needed: Instagram token expires in {max(days_remaining, 0)} day(s)"
    body = f"""Your Instagram access token for @the_higher_being is about to expire (estimated {max(days_remaining,0)} day(s) remaining).

What to do:
1. Go to https://developers.facebook.com/apps/ and open your app
2. Go to "API setup with Instagram login" (or the Instagram Graph API setup section)
3. Generate a new long-lived access token for the account
4. Come back to Claude and share the new token - I'll update it in:
   - GitHub Secrets (INSTAGRAM_ACCESS_TOKEN) for both the main and editorial workflows
   - Any other place it's referenced

Direct link: https://developers.facebook.com/apps/

Once you've shared the new token with me, I'll also reset the expiry tracker so this reminder doesn't fire again until the next cycle.
"""
    with open('_email_body.txt', 'w') as f:
        f.write(body)
    subprocess.run(['python3', 'send_email.py', subject, '_email_body.txt'], check=True)
    sent_any = True
    print(f"Sent token expiry reminder ({days_remaining} days remaining)")

# --- Check 2: Main content pool running low ---
with open('../main/content.json') as f:
    main_content = json.load(f)
main_unused = sum(1 for e in main_content if not e['used'])

if main_unused < 10 and not state['main_low_alerted']:
    subject = f"Action needed: Main content pool running low ({main_unused} left)"
    body = f"""Your daily quote/fact pipeline (@the_higher_being main pipeline) only has {main_unused} unused pieces left in main/content.json.

Copy and paste the message below into Claude (a new chat is fine) to top it up:

---
My Instagram/X/Threads/Pinterest account @the_higher_being runs on an automated content pipeline hosted at github.com/devdave666/psych-reels. It posts once daily via a GitHub Actions workflow (.github/workflows/main-daily-post.yml) pulling from main/content.json in that repo, which is now running low on unused entries.

Please do the following:
1. Read main/content.json from that repo to see the current entries and confirm how many are unused (used: false).
2. Add 40-50 new entries to keep it well-stocked. Each entry needs: id (next sequential number), type ("quote" or "fact"), text, attribution, source, used (false), date_used ("").
3. For quotes: use real, carefully verified philosopher quotes (public domain philosophers only - Marcus Aurelius, Epictetus, Seneca, Descartes, Nietzsche, Kant, Spinoza, Plato, Aristotle, Schopenhauer, Kierkegaard, Hume, Locke, Mill, Voltaire, Rousseau, Pascal, Montaigne, Cicero, Francis Bacon, Thomas Hobbes, Hegel, Emerson, Thoreau, Benjamin Franklin, or similar). Avoid commonly-circulated fake/misattributed quotes - verify authenticity before including anything.
4. For facts: genuine, well-established psychology findings (not fragile/unreplicated claims), similar style to existing entries (spacing effect, Zeigarnik effect, IKEA effect, etc.)
5. Check the attribution against composite_card.py's IMAGE_MAP at the repo root - if a quote's philosopher isn't already in that map, either pick a philosopher who IS already covered, or let me know you need a new background image generated for them (that requires a separate image-generation step, don't skip it silently).
6. Keep quotes and facts reasonably balanced/interleaved, not clustered.
7. Validate the JSON, then push directly to the repo (you'll need a GitHub token from me - ask if you don't have one already).
8. Confirm the new total count and how much runway that adds at 1 post/day.

Let me know before pushing if anything is ambiguous rather than guessing.
---

Direct link to the file: https://github.com/devdave666/psych-reels/blob/main/main/content.json
"""
    with open('_email_body.txt', 'w') as f:
        f.write(body)
    subprocess.run(['python3', 'send_email.py', subject, '_email_body.txt'], check=True)
    state['main_low_alerted'] = True
    sent_any = True
    print(f"Sent main pool low reminder ({main_unused} left)")
elif main_unused >= 10 and state['main_low_alerted']:
    state['main_low_alerted'] = False
    print("Main pool topped up, reset alert flag")

# --- Check 3: Editorial content pool running low ---
with open('../editorial/content.json') as f:
    editorial_content = json.load(f)
editorial_unused = sum(1 for e in editorial_content if not e['used'])

if editorial_unused < 10 and not state['editorial_low_alerted']:
    subject = f"Action needed: Editorial content pool running low ({editorial_unused} left)"
    body = f"""Your twice-weekly long-form pipeline (@the_higher_being editorial pipeline) only has {editorial_unused} unused pieces left in editorial/content.json.

Copy and paste the message below into Claude (a new chat is fine) to top it up:

---
My Instagram/X/Threads/Pinterest account @the_higher_being runs an automated "long-form" content pipeline (separate from the daily quote pipeline) hosted at github.com/devdave666/psych-reels, in the /editorial/ folder. It posts twice a week via .github/workflows/editorial-post.yml, pulling from editorial/content.json, which is now running low on unused entries.

Please do the following:
1. Read editorial/content.json to see current entries and confirm how many are unused (used: false).
2. Read editorial/render_essay.py and editorial/render_pinterest_teaser.py to understand the exact format required.
3. Add 15-20 new entries. Each needs: id, title, label ("ANCIENT INTUITION. MODERN PROOF." for philosopher/psychology pairings, or "A STORY WORTH KEEPING" for biographical stories), body (paragraphs separated by \\n\\n), cta, hashtags, used (false), date_used (""), pinterest_hook.

Format and quality standards, all of which took real iteration to get right - please follow closely rather than reverting to defaults:
- Prose should feel literary and specific: real settings, sensory detail, varied sentence rhythm (including short punchy fragments), not "explain the mechanism" textbook tone. Ground abstract psychology connections in a concrete detail or real-world application where possible.
- CTA must be a LOW-STAKES INVITATION, never a demand to publicly expose something vulnerable. Pattern: "If [situation], comment '[one word]'." Never "comment your biggest fear" style.
- pinterest_hook: a separate, shorter teaser excerpt that stops mid-scene/mid-thought at a genuine cliffhanger point - this becomes a standalone teaser image on Pinterest that links back to the full Instagram post, so it must NOT give away the resolution.
- Mix "ancient intuition/modern proof" pairings (a philosopher's real, verified idea paired with a genuine, well-established psychology finding or documented historical lineage - like Epictetus directly influencing Aaron Beck's CBT) with biographical story pieces (real historical anecdotes, verified against reputable sources, not embellished beyond what's documented).
- Avoid content involving self-harm or suicide even when historically factual (e.g. skip stories about philosophers' deaths by suicide, even if philosophically framed).
- Double-check every quote/attribution for authenticity - several widely-circulated philosopher quotes are actually fake/misattributed. When in doubt, skip it or verify via search first.

4. Check attribution against composite_card.py's IMAGE_MAP (repo root) if introducing a new philosopher not yet covered in /backgrounds/ - flag if a new background image needs generating rather than skipping silently.
5. Test-render at least 2 of the new entries locally (using render_from_selection.py's logic) before pushing, to catch title-wrapping or pagination issues.
6. Validate the JSON, then push to the repo (ask me for a GitHub token if you don't already have one).
7. Confirm new total count and runway added at 2 posts/week.

Ask me before pushing if anything is ambiguous rather than guessing.
---

Direct link to the file: https://github.com/devdave666/psych-reels/blob/main/editorial/content.json
"""
    with open('_email_body.txt', 'w') as f:
        f.write(body)
    subprocess.run(['python3', 'send_email.py', subject, '_email_body.txt'], check=True)
    state['editorial_low_alerted'] = True
    sent_any = True
    print(f"Sent editorial pool low reminder ({editorial_unused} left)")
elif editorial_unused >= 10 and state['editorial_low_alerted']:
    state['editorial_low_alerted'] = False
    print("Editorial pool topped up, reset alert flag")

with open('state.json', 'w') as f:
    json.dump(state, f, indent=2)

print(f"Check complete. Any reminder sent: {sent_any}")
