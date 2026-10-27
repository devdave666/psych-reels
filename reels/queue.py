"""Daily reel queue. reels/queue.json is an ordered list of {"name", "posted"}; a reel is posted once, in order.

  python3 reels/queue.py next          print the next unposted reel name (exit 1 if the queue is empty)
  python3 reels/queue.py mark NAME     record NAME as posted today (UTC)
  python3 reels/queue.py left          print how many unposted reels remain

A reel needs videos/<name>.mp4 and captions/<name>.txt, which are checked before it is returned."""
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = Path(__file__).resolve().parent / "queue.json"


def load():
    return json.loads(QUEUE.read_text(encoding="utf-8"))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "next"
    q = load()
    pending = [r for r in q if not r.get("posted")]
    if cmd == "left":
        print(len(pending))
    elif cmd == "next":
        if not pending:
            print("queue is empty: add a reel to reels/queue.json", file=sys.stderr)
            sys.exit(1)
        name = pending[0]["name"]
        for p in (ROOT / "videos" / f"{name}.mp4", ROOT / "captions" / f"{name}.txt"):
            if not p.exists():
                print(f"missing {p}", file=sys.stderr)
                sys.exit(1)
        print(name)
    elif cmd == "mark":
        name = sys.argv[2]
        for r in q:
            if r["name"] == name and not r.get("posted"):
                r["posted"] = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
                break
        else:
            print(f"{name} not pending", file=sys.stderr)
            sys.exit(1)
        QUEUE.write_text(json.dumps(q, indent=2) + "\n", encoding="utf-8")
    else:
        sys.exit("usage: queue.py next|mark NAME|left")


if __name__ == "__main__":
    main()
