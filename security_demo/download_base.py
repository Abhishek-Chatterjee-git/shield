"""Restore the pinned public base weights omitted from the Git repository."""
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    manifest = json.loads((ROOT/'manifest.json').read_text())
    revision = manifest['base_revision']
    for entry in manifest['files']:
        relative = entry['path']
        if not relative.startswith('models/qwen-base/') or not relative.endswith('.safetensors'):
            continue
        target = ROOT/relative
        if target.exists():
            with target.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if digest == entry['sha256']:
                print(f'Already verified: {target.name}')
                continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix('.download')
        url = f'https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/resolve/{revision}/{target.name}'
        print(f'Downloading {target.name} ({entry["bytes"]/1e9:.2f} GB). Please wait.', flush=True)
        try:
            urllib.request.urlretrieve(url, temporary)
            with temporary.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if temporary.stat().st_size != entry['bytes'] or digest != entry['sha256']:
                raise ValueError('Downloaded base model failed manifest verification')
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        print(f'Verified: {target.name}')


if __name__ == '__main__':
    main()
