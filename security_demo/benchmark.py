"""Save real model traces; never fabricate successful attacks or normalization."""
import argparse
import json
import platform
import time
from datetime import datetime, timezone
from runtime import Engine, ROOT
from controller import Controller, parse_action

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pairs', type=int, default=1)
    parser.add_argument('--normalize', action='store_true', help='Adds a base-model inference pass per case')
    args = parser.parse_args()
    import psutil
    engine = Engine()
    examples = json.loads((ROOT/'data/demo_examples.json').read_text(encoding='utf-8'))
    results = []
    for row in examples[:max(1,args.pairs)]:
        for variant in ('clean_text','trigger_text'):
            modes = (False,True) if args.normalize else (False,)
            for normalized in modes:
                print(f"Running {row['style']} {variant}, normalization={normalized}", flush=True)
                result = engine.run(row[variant], normalized)
                result.update({'style':row['style'], 'variant':variant, 'expected_label':row['label']})
                result['protected_execution'] = Controller().execute(result['proposal']['text'])
                result['unprotected_execution'] = Controller().execute(result['proposal']['text'], protected=False)
                result['rss_bytes_after_case'] = psutil.Process().memory_info().rss
                results.append(result)
    report = {'created_utc':datetime.now(timezone.utc).isoformat(), 'platform':platform.platform(),
              'processor':platform.processor(), 'load_seconds':engine.load_seconds, 'results':results,
              'limitations':'Training examples, not held-out evaluation. RSS is sampled, not peak memory. Simulator is not hardware.'}
    directory = ROOT/'results'
    directory.mkdir(exist_ok=True)
    output = directory/f'benchmark_{time.time_ns()}.json'
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'Saved real traces to {output}', flush=True)

if __name__ == '__main__':
    main()
