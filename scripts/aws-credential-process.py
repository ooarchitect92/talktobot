"""Refreshable SDK credential bridge to AWS CLI's browser login session.

Stdout is the AWS credential-process protocol. Never invoke this helper directly
in a terminal or capture its stdout in a report; Terraform consumes it privately.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--profile", choices=["northstar-iam", "northstar-dev"], required=True)
arguments = parser.parse_args()
environment = os.environ.copy()
for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE"):
    environment.pop(key, None)
environment["AWS_CONFIG_FILE"] = str(Path.home() / ".aws" / "config")
result = subprocess.run([r"C:\Program Files\Amazon\AWSCLIV2\aws.exe", "configure", "export-credentials", "--profile", arguments.profile, "--format", "process"], env=environment, capture_output=True)
if result.returncode:
    print("AWS login credentials unavailable; authenticate the configured profile.", file=sys.stderr)
    raise SystemExit(result.returncode)
sys.stdout.buffer.write(result.stdout)
