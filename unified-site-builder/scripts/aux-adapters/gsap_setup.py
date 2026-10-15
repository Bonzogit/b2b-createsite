#!/usr/bin/env python3
"""Install the GSAP runtime into a project and emit the guarded loader snippet.

GSAP Skills is an instruction set, not a runtime. When a project actually needs
motion, this script puts the real runtime in place and writes the include plus
the reduced-motion guard that the workflow requires.

Exit codes:
  0  runtime installed (or already present) and snippet written
  2  runtime unavailable -> NOT integrated
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

VENDOR = Path(__file__).resolve().parents[3] / "vendor" / "gsap.min.js"
KNOWN_SHA256 = None  # filled on first successful install

SNIPPET = """<!-- GSAP runtime (loaded deferred). Motion is opt-in: the site script
     checks prefers-reduced-motion and the data-motion flag before animating. -->
<script src="/assets/vendor/gsap.min.js" defer></script>
"""


def main():
    p = argparse.ArgumentParser(description="Install the GSAP runtime into a project")
    p.add_argument("--project", required=True, help="project root")
    p.add_argument("--source", help="path to a local gsap.min.js (default: skill vendor copy)")
    p.add_argument("--out", help="write JSON record to this file")
    args = p.parse_args()

    project = Path(args.project)
    source = Path(args.source) if args.source else VENDOR
    if not source.exists():
        for base in (Path.home() / ".workbuddy" / "binaries" / "node" / "workspace" / "node_modules" / "gsap" / "dist",
                     Path.cwd() / "node_modules" / "gsap" / "dist"):
            candidate = base / "gsap.min.js"
            if candidate.exists():
                source = candidate
                break
    if not source.exists():
        print(json.dumps({"ok": False, "reason": "runtime_missing",
                          "detail": "gsap.min.js not found; place it in <skill>/vendor/ "
                                    "or pass --source"}, ensure_ascii=False))
        return 2

    target_dir = project / "public" / "assets" / "vendor"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "gsap.min.js"
    shutil.copyfile(source, target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()

    record = {"ok": True, "capability": "gsapSkills", "action": "install-runtime",
              "source": str(source), "installed": str(target.relative_to(project)).replace("\\", "/"),
              "sha256": digest, "bytes": target.stat().st_size,
              "snippet": SNIPPET,
              "requirements": ["honour prefers-reduced-motion",
                               "verify mobile and RTL", "no text occlusion", "no click interception"]}
    text = json.dumps(record, ensure_ascii=False, indent=2)
    if args.out:
        out = Path(args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8", newline="\n")
        print(f"written: {out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
