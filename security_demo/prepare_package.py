"""Run on the source computer; copies real files, never cache symlinks."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent

def main():
    cache = Path.home()/'.cache/huggingface/hub/models--Qwen--Qwen2.5-1.5B-Instruct'
    ref = cache/'refs/main'
    revision = ref.read_text().strip() if ref.exists() else None
    snapshots = list((cache/'snapshots').glob('*'))
    snapshot = cache/'snapshots'/revision if revision else (snapshots[0] if len(snapshots)==1 else None)
    if snapshot is None or not snapshot.exists():
        raise SystemExit('Cannot identify complete cached model snapshot.')
    destination = ROOT/'models/qwen-base'
    destination.mkdir(parents=True, exist_ok=True)
    for source in snapshot.iterdir():
        if source.is_file() and (source.suffix in ('.json','.safetensors','.jinja','.txt','.md') or source.name=='LICENSE'):
            target = destination/source.name
            if not target.exists() or target.stat().st_size != source.stat().st_size:
                shutil.copyfile(source.resolve(), target)
    if not list(destination.glob('*.safetensors')):
        raise SystemExit('Base model weights are missing from the cache.')
    adapter = ROOT/'artifacts/badstyle_adapter'
    adapter.mkdir(parents=True, exist_ok=True)
    for source in (ROOT.parent/'artifacts/badstyle_adapter').iterdir():
        if source.is_file():
            shutil.copyfile(source, adapter/source.name)
    rows = [json.loads(line) for line in (ROOT.parent/'data/style_dataset.jsonl').read_text(encoding='utf-8').splitlines()]
    selected = []
    for style in sorted({r['style'] for r in rows}):
        candidates = [r for r in rows if r['style']==style]
        clean_candidates = [r for r in candidates if '(note:' not in r['trigger_text'].lower() and 'rewritten:' not in r['trigger_text'].lower()]
        selected.append(min(clean_candidates or candidates, key=lambda r:len(r['trigger_text'])))
    (ROOT/'data').mkdir(exist_ok=True)
    (ROOT/'data/demo_examples.json').write_text(json.dumps(selected,indent=2),encoding='utf-8')
    files = []
    candidates = [p for p in ROOT.iterdir() if p.is_file() and p.name != 'manifest.json']
    for folder in ('models','artifacts','data','results','ui'):
        candidates.extend((ROOT/folder).rglob('*'))
    for path in sorted(candidates):
        if path.is_file():
            h = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda:stream.read(8*1024*1024), b''):
                    h.update(block)
            files.append({'path':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size,'sha256':h.hexdigest()})
    (ROOT/'manifest.json').write_text(json.dumps({'base_revision':snapshot.name,'files':files},indent=2))
    print(f'Packaged {len(files)} files, {sum(f["bytes"] for f in files)/1e9:.2f} GB. Revision: {snapshot.name}')

if __name__ == '__main__':
    main()
