"""Run a checksum-verified Gitleaks version consistently in CI and releases."""
from __future__ import annotations

import hashlib
import io
import platform
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

VERSION = "8.30.1"
ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    operating_system = {"Linux": "linux", "Windows": "windows", "Darwin": "darwin"}[platform.system()]
    architecture = {"x86_64": "x64", "AMD64": "x64", "arm64": "arm64", "aarch64": "arm64"}[platform.machine()]
    extension = "zip" if operating_system == "windows" else "tar.gz"
    asset = f"gitleaks_{VERSION}_{operating_system}_{architecture}.{extension}"
    base = f"https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}/"
    with urllib.request.urlopen(base + asset, timeout=60) as response:
        payload = response.read()
    with urllib.request.urlopen(base + f"gitleaks_{VERSION}_checksums.txt", timeout=60) as response:
        checksums = response.read().decode()
    expected = next(line.split()[0] for line in checksums.splitlines() if line.split()[-1].lstrip("*") == asset)
    if hashlib.sha256(payload).hexdigest() != expected:
        raise RuntimeError("Gitleaks archive checksum mismatch")
    executable_name = "gitleaks.exe" if operating_system == "windows" else "gitleaks"
    with tempfile.TemporaryDirectory(prefix="talktobot-gitleaks-") as directory:
        executable = Path(directory) / executable_name
        if extension == "zip":
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                executable.write_bytes(archive.read(executable_name))
        else:
            with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
                member = archive.extractfile(executable_name)
                if member is None:
                    raise RuntimeError("Gitleaks executable missing")
                executable.write_bytes(member.read())
        executable.chmod(0o700)
        return subprocess.run(
            [str(executable), "git", "--config", str(ROOT / ".gitleaks.toml"),
             "--log-opts=HEAD", "--redact", "--no-banner"], cwd=ROOT, check=False
        ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
