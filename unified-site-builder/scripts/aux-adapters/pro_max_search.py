#!/usr/bin/env python3
"""Run the UI/UX Pro Max CIP design search tool and record the result.

The Pro Max repository is a *source of design guidance*, not a skill we load
wholesale. This wrapper calls its real search tool (pure Python standard
library) so a project's design spec is produced by an actual search instead of
the agent's recollection.

Exit codes:
  0  search ran and results were written
  2  capability unavailable (source missing / tool missing) -> NOT integrated
  3  no results for the query
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_SOURCE = Path.home() / ".aux" / "ui-ux-pro-max-skill"


def find_tool(source: Path):
    candidates = list(source.rglob("scripts/cip/search.py"))
    candidates += list(source.rglob("cip/search.py"))
    return candidates[0] if candidates else None


def main():
    p = argparse.ArgumentParser(description="Search UI/UX Pro Max CIP design guidelines")
    p.add_argument("--source", default=str(DEFAULT_SOURCE),
                   help="path to the ui-ux-pro-max-skill checkout")
    p.add_argument("--query", required=True)
    p.add_argument("--domain", choices=["deliverable", "style", "industry", "mockup"])
    p.add_argument("--all-domains", action="store_true")
    p.add_argument("--max", type=int, default=3)
    p.add_argument("--out", help="write JSON result to this file")
    p.add_argument("--python", default=sys.executable)
    args = p.parse_args()

    source = Path(args.source)
    if not source.exists():
        print(json.dumps({"ok": False, "reason": "source_missing",
                          "detail": f"Pro Max checkout not found at {source}"},
                         ensure_ascii=False))
        return 2
    tool = find_tool(source)
    if tool is None:
        print(json.dumps({"ok": False, "reason": "tool_missing",
                          "detail": "scripts/cip/search.py not found in checkout"},
                         ensure_ascii=False))
        return 2

    cmd = [args.python, str(tool), args.query, "--max", str(args.max), "--json"]
    if args.all_domains:
        cmd.append("--all")
    elif args.domain:
        cmd += ["--domain", args.domain]

    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        print(json.dumps({"ok": False, "reason": "tool_failed",
                          "detail": (proc.stderr or proc.stdout)[-500:]}, ensure_ascii=False))
        return 2

    raw = proc.stdout.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"raw": raw}

    result = {"ok": True, "capability": "uiUxProMax", "tool": str(tool),
              "query": args.query, "domain": args.domain or "all",
              "result": data}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8", newline="\n")
        print(f"written: {out}")
    else:
        print(text)
    return 0 if data else 3


if __name__ == "__main__":
    sys.exit(main())
