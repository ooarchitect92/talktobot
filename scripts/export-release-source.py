"""Export reviewable repository files, excluding ignored credentials and build state."""
from __future__ import annotations

import hashlib
import argparse
import json
from pathlib import Path
import shutil
import subprocess


root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--output", default="reports/readiness/security-source")
arguments = parser.parse_args()
destination = (root / arguments.output).resolve()
destination.relative_to(root / "reports" / "readiness")
if destination.exists():
    raise SystemExit("Use a fresh export directory; existing scan inputs must not be overwritten.")
names = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root).decode("utf-8").split("\0")
digest = hashlib.sha256()
count = 0
for name in sorted(set(filter(None, names))):
    source = root / name
    if not source.is_file():
        continue
    source.resolve().relative_to(root)
    payload = source.read_bytes()
    digest.update(name.encode("utf-8") + b"\0" + hashlib.sha256(payload).digest())
    target = destination / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    count += 1
receipt = {"sourceTreeSha256": digest.hexdigest(), "files": count, "qualified": False, "note": "Diagnostic worktree export; not an immutable release commit."}
(destination.parent / f"{destination.name}-receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps(receipt))
