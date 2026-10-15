#!/usr/bin/env python3
"""Run the Impeccable detector over real pages and record the findings.

Impeccable ships 60 deterministic detector rules that run with no LLM and no
API key. This wrapper invokes the real binary and stores its output as review
evidence, so "reviewed with Impeccable" means the detector actually ran.

Exit codes:
  0  detector ran (findings may be zero)
  2  capability unavailable (binary missing) -> NOT integrated
  3  detector ran but reported at least one anti-pattern
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_BIN = Path.home() / ".impeccable" / "bin" / "impeccable.exe"


def resolve_binary(explicit=None):
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None
    env = __import__("os").environ.get("IMPECCABLE_BIN")
    if env and Path(env).exists():
        return Path(env)
    if DEFAULT_BIN.exists():
        return DEFAULT_BIN
    # npm-installed platform package inside a node workspace
    for base in (Path.home() / ".workbuddy" / "binaries" / "node" / "workspace" / "node_modules",
                 Path.cwd() / "node_modules"):
        for hit in base.rglob("impeccable.exe"):
            return hit
    return None


def parse(text):
    """Turn the detector's human output into structured findings."""
    findings = []
    current_file = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^[A-Za-z]:\\|^\/", stripped) and stripped.endswith((".html", ".css", ".js")):
            current_file = stripped
            continue
        m = re.match(r"^\[([a-z0-9\-]+)\]\s+(.*)$", stripped)
        if m:
            findings.append({"file": current_file, "rule": m.group(1), "detail": m.group(2)})
            continue
        if findings and stripped.startswith("→"):
            findings[-1]["advice"] = stripped.lstrip("→ ").strip()
            continue
        m2 = re.match(r"^(\d+)\s+anti-patterns?\s+found\.?$", stripped)
        if m2:
            findings.append({"summary": {"count": int(m2.group(1))}})
    return findings


def main():
    p = argparse.ArgumentParser(description="Run Impeccable's deterministic UI detector")
    p.add_argument("targets", nargs="+", help="files, directories or URLs")
    p.add_argument("--bin", help="path to impeccable binary")
    p.add_argument("--out", help="write JSON result to this file")
    p.add_argument("--strict", action="store_true",
                   help="exit 3 when anti-patterns are found")
    args = p.parse_args()

    binary = resolve_binary(args.bin)
    if binary is None:
        print(json.dumps({"ok": False, "reason": "binary_missing",
                          "detail": "Impeccable binary not found; install "
                                    "@impeccable/cli-<platform> or set IMPECCABLE_BIN"},
                         ensure_ascii=False))
        return 2

    cmd = [str(binary), "detect", *args.targets]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    combined = (proc.stdout or "") + (proc.stderr or "")
    findings = parse(combined)
    count = 0
    for f in findings:
        if isinstance(f.get("summary"), dict):
            count = f["summary"]["count"]
    if count == 0:
        count = len([f for f in findings if "rule" in f])

    result = {"ok": True, "capability": "impeccable", "command": "detect",
              "binary": str(binary), "targets": args.targets,
              "findings": findings, "count": count, "raw": combined}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8", newline="\n")
        print(f"written: {out}")
    else:
        print(text)
    if count and args.strict:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
