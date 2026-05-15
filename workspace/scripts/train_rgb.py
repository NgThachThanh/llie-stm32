import argparse
import csv
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader

from src.data.image_dataset import RGBPairedImageDataset
from src.losses.losses import build_rgb_loss
from src.models.rgb_models import OneStepRGBStudent, RGBCNNBaseline


def load_cfg(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def make_model(cfg):
    mcfg = cfg['model']
    if mcfg['type'] == 'rgb_cnn_baseline':
        return RGBCNNBaseline(
            base_channels=mcfg.get('base_channels', 16),
            depth=mcfg.get('depth', 4),
        )
    if mcfg['type'] == 'one_step_rgb_student':
        return OneStepRGBStudent(base_channels=mcfg.get('base_channels', 24))
    raise ValueError(f"Unsupported RGB model type: {mcfg['type']}")


def make_loader(cfg, low_dir, high_dir, teacher_dir=None, shuffle=False):
    ds = RGBPairedImageDataset(
        low_dir=low_dir,
        high_dir=high_dir,
        teacher_dir=teacher_dir or None,
        image_size=cfg['data']['image_size'],
    )
    return DataLoader(
        ds,
        batch_size=cfg['train']['batch_size'],
        shuffle=shuffle,
        num_workers=cfg['train']['num_workers'],
    )


def run_epoch(model, loader, optimizer, cfg, device, train):
    model.train(train)
    totals = {}
    with torch.set_grad_enabled(train):
        for batch in loader:
            x = batch['rgb_low'].to(device)
            y = batch['rgb_high'].to(device)
            teacher = batch['rgb_teacher'].to(device) if 'rgb_teacher' in batch else None
            pred = model(x)
            losses = build_rgb_loss(pred, y, teacher=teacher, weights=cfg['loss'])
            if train:
                optimizer.zero_grad()
                losses['total'].backward()
                optimizer.step()
            for name, value in losses.items():
                totals[name] = totals.get(name, 0.0) + float(value.item())
    return {k: v / max(1, len(loader)) for k, v in totals.items()}


def append_log(path: Path, row: dict):
    exists = path.exists()
    with path.open('a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', required=True)
    p.add_argument('--low-dir', required=True)
    p.add_argument('--high-dir', required=True)
    p.add_argument('--teacher-dir', default='')
    p.add_argument('--val-low-dir', default='')
    p.add_argument('--val-high-dir', default='')
    p.add_argument('--val-teacher-dir', default='')
    p.add_argument('--outdir', default='')
    args = p.parse_args()

    cfg = load_cfg(args.config)
    set_seed(cfg['train']['seed'])
    device = torch.device(cfg['train']['device'] if torch.cuda.is_available() else 'cpu')
    model = make_model(cfg).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg['train']['lr'], weight_decay=cfg['train']['weight_decay'])
    train_loader = make_loader(cfg, args.low_dir, args.high_dir, args.teacher_dir, shuffle=True)
    val_loader = None
    if args.val_low_dir and args.val_high_dir:
        val_loader = make_loader(cfg, args.val_low_dir, args.val_high_dir, args.val_teacher_dir, shuffle=False)

    outdir = Path(args.outdir or Path(cfg['paths']['outputs_root']) / 'checkpoints_rgb')
    outdir.mkdir(parents=True, exist_ok=True)
    log_path = outdir / 'train_log.csv'
    best = float('inf')

    for epoch in range(1, cfg['train']['epochs'] + 1):
        train_metrics = run_epoch(model, train_loader, optimizer, cfg, device, train=True)
        val_metrics = run_epoch(model, val_loader, None, cfg, device, train=False) if val_loader else None
        selected = val_metrics['total'] if val_metrics else train_metrics['total']
        payload = {
            'epoch': epoch,
            'model': model.state_dict(),
            'optimizer': optimizer.state_dict(),
            'config': cfg,
            'train_metrics': train_metrics,
            'val_metrics': val_metrics,
        }
        torch.save(payload, outdir / 'last.pt')
        if selected < best:
            best = selected
            torch.save(payload, outdir / 'best.pt')
        row = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'epoch': epoch}
        row.update({f'train_{k}': v for k, v in train_metrics.items()})
        if val_metrics:
            row.update({f'val_{k}': v for k, v in val_metrics.items()})
        append_log(log_path, row)
        print(f"epoch={epoch} train_total={train_metrics['total']:.6f}" + (f" val_total={val_metrics['total']:.6f}" if val_metrics else ''))


if __name__ == '__main__':
    main()
