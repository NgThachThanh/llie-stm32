import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2
import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader

from src.data.image_dataset import RGBPairedImageDataset
from src.losses.losses import simple_ssim_loss
from src.models.rgb_models import OneStepRGBStudent, RGBCNNBaseline


def load_cfg(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def make_model(cfg):
    mcfg = cfg['model']
    if mcfg['type'] == 'rgb_cnn_baseline':
        return RGBCNNBaseline(mcfg.get('base_channels', 16), mcfg.get('depth', 4))
    if mcfg['type'] == 'one_step_rgb_student':
        return OneStepRGBStudent(mcfg.get('base_channels', 24))
    raise ValueError(mcfg['type'])


def psnr(pred, target):
    mse = torch.mean((pred - target) ** 2).item()
    return float('inf') if mse == 0 else 10.0 * math.log10(1.0 / mse)


def to_u8(x):
    arr = x.detach().cpu().clamp(0, 1).numpy().transpose(1, 2, 0)
    return (arr * 255.0).round().astype(np.uint8)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', required=True)
    p.add_argument('--checkpoint', required=True)
    p.add_argument('--low-dir', required=True)
    p.add_argument('--high-dir', required=True)
    p.add_argument('--output-dir', default='')
    p.add_argument('--limit', type=int, default=0)
    args = p.parse_args()

    cfg = load_cfg(args.config)
    device = torch.device(cfg['train']['device'] if torch.cuda.is_available() else 'cpu')
    ds = RGBPairedImageDataset(args.low_dir, args.high_dir, image_size=cfg['data']['image_size'])
    loader = DataLoader(ds, batch_size=1, shuffle=False)
    model = make_model(cfg).to(device)
    ckpt = torch.load(args.checkpoint, map_location=device)
    model.load_state_dict(ckpt['model'])
    model.eval()
    out_dir = Path(args.output_dir) if args.output_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    metrics = []
    with torch.no_grad():
        for i, batch in enumerate(loader):
            if args.limit and i >= args.limit:
                break
            x = batch['rgb_low'].to(device)
            y = batch['rgb_high'].to(device)
            pred = model(x)
            metrics.append((psnr(pred, y), 1.0 - simple_ssim_loss(pred, y).item()))
            if out_dir:
                low = to_u8(x[0])
                enh = to_u8(pred[0])
                high = to_u8(y[0])
                canvas = np.concatenate([low, enh, high], axis=1)
                cv2.imwrite(str(out_dir / f"{batch['name'][0]}_preview.png"), cv2.cvtColor(canvas, cv2.COLOR_RGB2BGR))
    print(f'count={len(metrics)} psnr={np.mean([m[0] for m in metrics]):.4f} ssim={np.mean([m[1] for m in metrics]):.4f}')


if __name__ == '__main__':
    main()
