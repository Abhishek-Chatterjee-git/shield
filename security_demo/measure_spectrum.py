"""Artifact-linked energy and entropy measurement for plain LoRA updates."""
import hashlib
import json
import math
from pathlib import Path
import torch
from safetensors.torch import load_file


def measure(path):
    torch.set_num_threads(4)
    weights = load_file(str(path), device='cpu')
    rows = []
    for key, value in sorted(weights.items()):
        if not key.endswith('.lora_A.weight'):
            continue
        a = value.double()
        b = weights[key.replace('.lora_A.weight', '.lora_B.weight')].double()
        if not torch.isfinite(a).all() or not torch.isfinite(b).all():
            raise ValueError('Nonfinite adapter weights')
        _, ra = torch.linalg.qr(a.T, mode='reduced')
        _, rb = torch.linalg.qr(b, mode='reduced')
        singular = torch.linalg.svdvals(rb @ ra.T)
        energy = singular.square()
        if float(energy.sum()) == 0:
            raise ValueError('Zero update has no defined normalized energy entropy')
        p = energy / energy.sum()
        positive = p[p > 0]
        entropy = float(-(positive * positive.log()).sum())
        rows.append(dict(layer=int(key.split('layers.')[1].split('.')[0]),
                         projection=key.split('.self_attn.')[1].split('.')[0],
                         top_energy=float(p[0]), entropy_nats=entropy,
                         normalized_entropy=entropy/math.log(len(p)),
                         effective_rank=math.exp(entropy),
                         singular_values=singular.tolist(), energy_probabilities=p.tolist()))
    if not rows:
        raise ValueError('No LoRA pairs')
    maximum = max(rows, key=lambda row: row['top_energy'])
    layers = sorted({row['layer'] for row in rows})
    peaks = [max(row['top_energy'] for row in rows if row['layer'] == layer) for layer in layers]
    middle = len(peaks)//2
    return dict(adapter_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                method='float64 reduced QR and small-core SVD; energy probabilities sigma^2/sum(sigma^2)',
                entropy_normalization='H / ln(number of low-rank core singular values), here 16; not dense matrix dimension',
                projections=len(rows), layers=len(layers),
                mean_top_energy=sum(row['top_energy'] for row in rows)/len(rows),
                mean_normalized_entropy=sum(row['normalized_entropy'] for row in rows)/len(rows),
                mean_effective_rank=sum(row['effective_rank'] for row in rows)/len(rows),
                strongest_projection=maximum,
                minimum_normalized_entropy=min(row['normalized_entropy'] for row in rows),
                maximum_normalized_entropy=max(row['normalized_entropy'] for row in rows),
                projections_at_or_above_0_8=sum(row['top_energy'] >= .8 for row in rows),
                deep_to_shallow_layer_max_ratio=(sum(peaks[middle:])/len(peaks[middle:]))/(sum(peaks[:middle])/len(peaks[:middle])),
                limitation='Descriptive measurements on one adapter, not calibrated detection accuracy or proof of compromise.',
                rows=rows)


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    report = measure(root/'artifacts/badstyle_adapter/adapter_model.safetensors')
    (root/'results/spectral_entropy.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'rows'}, indent=2))
