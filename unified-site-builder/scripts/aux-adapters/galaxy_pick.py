#!/usr/bin/env python3
"""Select concrete components from the Galaxy library and copy them into a project.

Galaxy is a component resource library (~3800 HTML files), not a callable
skill. This tool searches a category for a component, prints its source, and
can stage it next to the project so the agent can adapt it to the design spec
and wire it to real data.

Exit codes:
  0  component found (and copied when --copy-to is given)
  2  library unavailable -> NOT integrated
  3  no match
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

DEFAULT_SOURCE = Path.home() / ".aux" / "galaxy"
CATEGORIES = ["Buttons", "Cards", "Checkboxes", "Forms", "Inputs", "Notifications",
              "Patterns", "Radio-buttons", "Toggle-switches", "Tooltips", "loaders"]


def main():
    p = argparse.ArgumentParser(description="Pick a component from the Galaxy library")
    p.add_argument("--source", default=str(DEFAULT_SOURCE))
    p.add_argument("--category", default="Cards", choices=CATEGORIES)
    p.add_argument("--query", default="", help="substring match on the file name")
    p.add_argument("--name", help="exact file name inside the category")
    p.add_argument("--list", type=int, nargs="?", const=20,
                   help="list the first N components in the category and exit")
    p.add_argument("--copy-to", help="destination directory")
    p.add_argument("--print", dest="show", action="store_true", help="print the component source")
    p.add_argument("--out", help="write JSON record to this file")
    args = p.parse_args()

    source = Path(args.source) / args.category
    if not source.exists():
        print(json.dumps({"ok": False, "reason": "source_missing",
                          "detail": f"Galaxy category not found: {source}"}, ensure_ascii=False))
        return 2

    files = sorted(source.glob("*.html"))
    if args.list:
        print(json.dumps({"ok": True, "capability": "galaxy", "category": args.category,
                          "total": len(files),
                          "components": [f.name for f in files[:args.list]]},
                         ensure_ascii=False, indent=2))
        return 0
    if args.name:
        match = source / args.name
        if not match.exists():
            print(json.dumps({"ok": False, "reason": "not_found",
                              "detail": f"{args.name} not in {args.category}"}, ensure_ascii=False))
            return 3
    elif args.query:
        needle = args.query.lower()
        hits = [f for f in files if needle in f.name.lower()]
        if not hits:
            print(json.dumps({"ok": False, "reason": "no_match",
                              "detail": f"no {args.category} component matching {args.query!r}"},
                             ensure_ascii=False))
            return 3
        match = hits[0]
    else:
        match = files[0]

    body = match.read_text(encoding="utf-8", errors="replace")
    styles = re.findall(r"<style[^>]*>(.*?)</style>", body, re.S)
    markup = re.findall(r"<body[^>]*>(.*?)</body>", body, re.S)
    record = {"ok": True, "capability": "galaxy", "category": args.category,
              "component": match.name, "path": str(match),
              "bytes": match.stat().st_size,
              "hasStyle": bool(styles), "styleChars": sum(len(s) for s in styles),
              "markupChars": sum(len(m) for m in markup)}

    if args.copy_to:
        dest_dir = Path(args.copy_to).resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir.resolve() / f"galaxy-{args.category.lower()}-{match.stem}.html"
        shutil.copyfile(match, dest)
        record["copiedTo"] = str(dest)

    text = json.dumps(record, ensure_ascii=False, indent=2)
    if args.out:
        out = Path(args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8", newline="\n")
        print(f"written: {out}")
    else:
        print(text)
    if args.show:
        print("\n--- component source ---\n" + body[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
