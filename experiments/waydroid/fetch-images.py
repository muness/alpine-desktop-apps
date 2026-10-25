#!/usr/bin/env python3
"""Download the pinned official images and verify size and SHA256, without installing."""
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

pins = json.loads(Path(__file__).with_name('images.json').read_text())
if len(sys.argv) != 2:
    raise SystemExit('usage: fetch-images.py OUTPUT_DIRECTORY')
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
for pin in pins.values():
    target = out / pin['filename']
    if not target.exists():
        partial = target.with_suffix('.partial')
        with urllib.request.urlopen(pin['url'], timeout=60) as src, partial.open('wb') as dst:
            while chunk := src.read(1024 * 1024):
                dst.write(chunk)
        candidate = partial
    else:
        candidate = target
    with candidate.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if candidate.stat().st_size != pin['size'] or digest != pin['id']:
        raise SystemExit(f'Image verification failed: {candidate}')
    if candidate != target:
        candidate.rename(target)
    print(f'Verified {target}')
