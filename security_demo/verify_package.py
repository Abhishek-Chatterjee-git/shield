import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    manifest = json.loads((ROOT/'manifest.json').read_text())
    for item in manifest['files']:
        path = ROOT/item['path']
        if not path.is_file() or path.stat().st_size != item['bytes']:
            raise SystemExit(f'Missing or incomplete: {path}')
        h = hashlib.sha256()
        with path.open('rb') as f:
            for block in iter(lambda:f.read(8*1024*1024), b''):
                h.update(block)
        if h.hexdigest() != item['sha256']:
            raise SystemExit(f'Checksum mismatch: {path}')
    print(f"Verified {len(manifest['files'])} files, including base model and adapter.")

if __name__ == '__main__':
    main()
