"""Record completed local gates without mistaking a partial log for a pass."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source_digest() -> str:
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
    ).decode("utf-8").split("\0")
    digest = hashlib.sha256()
    for name in sorted(set(filter(None, names))):
        source = ROOT / name
        if source.is_file():
            source.resolve().relative_to(ROOT)
            digest.update(name.encode("utf-8") + b"\0" + hashlib.sha256(source.read_bytes()).digest())
    return digest.hexdigest()


def main() -> int:
    python = ROOT / "backend/.venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    node = shutil.which("node")
    npm = shutil.which("npm")
    npm_cli = Path(npm).resolve().parent / "node_modules/npm/bin/npm-cli.js" if npm else None
    # On Windows invoke the installed JavaScript entrypoint directly; no shell or interpolated commands.
    npm_command = [node, str(npm_cli)] if node and npm_cli and npm_cli.is_file() else [npm or "npm"]
    gates = {
        "backend-lint": [str(python), "-m", "ruff", "check", "backend"],
        "backend-format": [str(python), "-m", "ruff", "format", "--check", "backend"],
        "backend-types": [str(python), "-m", "mypy", "--config-file", "backend/pyproject.toml", "backend/src"],
        "backend-tests": [str(python), "-m", "pytest", "-c", "backend/pyproject.toml", "backend/tests", "-q"],
        "frontend-lint": [*npm_command, "run", "lint"],
        "frontend-types": [*npm_command, "run", "typecheck"],
        "frontend-tests": [*npm_command, "test"],
        "frontend-build": [*npm_command, "run", "build"],
        "website-build": [*npm_command, "run", "build", "--prefix", "website"],
        "website-tests": [*npm_command, "test", "--prefix", "website"],
    }
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checks", nargs="+", choices=list(gates), default=list(gates))
    args = parser.parse_args()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    directory = ROOT / "reports/readiness" / f"gates-{stamp}"
    directory.mkdir(parents=True, exist_ok=False)
    receipt = {
        "startedAt": datetime.now(UTC).isoformat(),
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "sourceTreeSha256": source_digest(),
        "qualified": False,
        "checks": [],
    }
    for name in args.checks:
        started = time.monotonic()
        logfile = directory / f"{name}.log"
        print(f"Running {name}", flush=True)
        with logfile.open("wb") as output:
            try:
                process = subprocess.run(gates[name], cwd=ROOT, stdout=output, stderr=subprocess.STDOUT, timeout=1800, check=False)
                status, code = "completed", process.returncode
            except subprocess.TimeoutExpired:
                status, code = "timed_out", None
            except OSError as error:
                output.write(f"Cannot start check: {type(error).__name__}\n".encode())
                status, code = "start_failed", None
        receipt["checks"].append({"name": name, "status": status, "exitCode": code, "seconds": round(time.monotonic() - started, 2), "logSha256": hashlib.sha256(logfile.read_bytes()).hexdigest()})
        print(f"{name}: {status}, exit={code}", flush=True)
    receipt["completedAt"] = datetime.now(UTC).isoformat()
    receipt["sourceUnchanged"] = source_digest() == receipt["sourceTreeSha256"]
    receipt["selectedChecksPassed"] = receipt["sourceUnchanged"] and all(item["exitCode"] == 0 for item in receipt["checks"])
    receipt["allLocalGatesPassed"] = receipt["selectedChecksPassed"] and set(args.checks) == set(gates)
    pending = directory / "receipt.pending"
    pending.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    pending.replace(directory / "receipt.json")
    print(f"Completed receipt: {directory / 'receipt.json'}", flush=True)
    return 0 if receipt["selectedChecksPassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
