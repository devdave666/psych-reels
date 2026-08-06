# Starting a new chat? Read this first.

This is the short version, for you (not the AI). If you're picking this
project back up in a new Claude chat, or trying a different AI entirely,
here's exactly what to do.

## The one message to paste into a new chat

```
I'm continuing work on my automated social media pipeline. The full
context is in this GitHub repo's llms.txt file: read it first, in full,
before doing anything else.

Repo: https://github.com/devdave666/psych-reels

[paste your actual request/task here]
```

If the AI you're using can't browse GitHub directly, instead paste this:

```
I'm continuing work on an automated social pipeline. Fetch and read
https://raw.githubusercontent.com/devdave666/psych-reels/main/llms.txt
in full before doing anything else - it has the complete project context.

[paste your actual request/task here]
```

## Do you need to give it anything else?

**For routine stuff** (checking on posts, adding content, tweaking
copy, asking questions) - no. The llms.txt covers it, and the actual
pipeline runs itself regardless of what AI you're talking to.

**If something needs a live fix** (posting manually, debugging a stuck
run, adding a new integration) - the AI will tell you exactly which
credential it needs and why. The most commonly needed one is a **GitHub
Personal Access Token** with repo write access, since almost everything
here is "edit a file, push it, the automation picks it up."

To get a fresh GitHub token if the old one's context is gone:
GitHub.com -> Settings -> Developer settings -> Personal access tokens ->
generate one scoped to the `psych-reels` repo with read/write on
Contents, Actions, and Workflows.

## What's already running without you touching anything

- Daily post: every day, ~9am EDT-ish (sometimes late, GitHub's own
  scheduler isn't perfectly punctual, this is expected and self-corrects)
- Editorial long-form post: Mondays and Thursdays
- Self-healing check: if a day's post genuinely fails to go out, it
  auto-retries and emails you either way
- Token/content-running-low warnings: emailed to you automatically

You should only ever need to open a chat because you *want* to change
something, not because something quietly broke.

## If you genuinely don't know where something stands

Just ask the new AI to check directly rather than trusting old chat
history (which may be stale) - it can pull live status from GitHub
Actions, Instagram's own API, etc. and give you the real current state
in under a minute.
