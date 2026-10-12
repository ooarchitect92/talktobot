"""Replace one Kustomize image tag with a verified OCI digest."""
import re
import sys
from pathlib import Path

path, name, digest = sys.argv[1:]
if not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
    raise SystemExit('Invalid digest')
target = Path(path)
source = target.read_text()
pattern = rf'(?m)(  - name: {re.escape(name)}\n    newName: [^\n]+\n)    newTag: [^\n]+'
updated, count = re.subn(pattern, rf'\g<1>    digest: {digest}', source)
if count != 1:
    raise SystemExit('Expected exactly one image declaration')
target.write_text(updated)
