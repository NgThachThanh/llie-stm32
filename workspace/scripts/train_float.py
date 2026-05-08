import argparse
import csv
import os
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

from src.data.image_dataset import PairedImageDataset
from src.losses.losses import build_image_loss
from src.models.student_v1 import StudentGlobalOnly, StudentV1
from src.render.luma_renderer import RangeConfig, RenderConfig, decode_outputs, render_luma


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def load_cfg(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def make_model(cfg):
    mcfg = cfg['model']
    if mcfg['type'] == 'student_global_only':
        return StudentGlobalOnly(
            in_channels=mcfg.get('in_channels', 1),
            base_channels=mcfg.get('base_channels', 8),
        )
    return StudentV1(
        in_channels=mcfg.get('in_channels', 1),
        base_channels=mcfg.get('base_channels', 8),
        local_hidden_channels=mcfg.get('local_hidden_channels', 4),
        map_size=mcfg.get('map_size', 8),
    )


def build_target_params(batch, device):
    if 'gain_global_tgt' not in batch:
        return None
    target = {
        'gain_global': batch['gain_global_tgt'].to(device),
        'gamma_global': batch['gamma_global_tgt'].to(device),
        'lift_black': batch['lift_black_tgt'].to(device),
        'gain_map': batch['gain_map_tgt'].to(device) if 'gain_map_tgt' in batch else None,
    }
    return target


def append_train_log(csv_path: Path, row: dict):
    file_exists = csv_path.exists()
    with csv_path.open('a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                'timestamp_utc',
                'epoch',
                'train_loss',
                'val_loss',
                'selection_loss',
                'selection_metric',
                'best_loss_so_far',
            ],
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def write_metrics_yaml(metrics_path: Path, payload: dict):
    with metrics_path.open('w', encoding='utf-8') as f:
        yaml.safe_dump(payload, f, sort_keys=False)


def run_epoch(model, loader, optimizer, rcfg, cfg, device, train: bool):
    model.train(train)
    running = 0.0
    with torch.set_grad_enabled(train):
        for batch in loader:
            y_low_96 = batch['y_low_96'].to(device)
            y_low_full = batch['y_low_full'].to(device)
            y_target = batch['teacher_y_full'].to(device) if 'teacher_y_full' in batch else batch['y_high_full'].to(device)

            out = model(y_low_96)
            decoded = decode_outputs(out, rcfg)
            y_pred, _ = render_luma(y_low_full, decoded, rcfg)
            target_params = build_target_params(batch, device)
            losses = build_image_loss(y_pred, y_target, decoded, target_params=target_params, weights=cfg['loss'])
            loss = losses['total']

            if train:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

            running += loss.item()
    return running / max(1, len(loader))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True)
    parser.add_argument('--low-dir', type=str, required=True)
    parser.add_argument('--high-dir', type=str, required=True)
    parser.add_argument('--teacher-dir', type=str, default='')
    parser.add_argument('--param-dir', type=str, default='')
    parser.add_argument('--val-low-dir', type=str, default='')
    parser.add_argument('--val-high-dir', type=str, default='')
    parser.add_argument('--val-teacher-dir', type=str, default='')
    parser.add_argument('--val-param-dir', type=str, default='')
    parser.add_argument('--outdir', type=str, default='')
    args = parser.parse_args()

    cfg = load_cfg(args.config)
    set_seed(cfg['train']['seed'])

    device = torch.device(cfg['train']['device'] if torch.cuda.is_available() else 'cpu')
    model = make_model(cfg).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg['train']['lr'], weight_decay=cfg['train']['weight_decay'])

    rcfg = RenderConfig(
        out_h=cfg['data']['out_h'],
        out_w=cfg['data']['out_w'],
        ranges=RangeConfig(**cfg['ranges']),
    )

    dataset = PairedImageDataset(
        low_dir=args.low_dir,
        high_dir=args.high_dir,
        teacher_dir=args.teacher_dir or None,
        input_size=cfg['data']['input_size'],
        out_h=cfg['data']['out_h'],
        out_w=cfg['data']['out_w'],
        param_dir=args.param_dir or None,
        map_size=cfg['data']['map_size'],
    )
    loader = DataLoader(dataset, batch_size=cfg['train']['batch_size'], shuffle=True, num_workers=cfg['train']['num_workers'])
    val_loader = None
    if args.val_low_dir and args.val_high_dir:
        val_dataset = PairedImageDataset(
            low_dir=args.val_low_dir,
            high_dir=args.val_high_dir,
            teacher_dir=args.val_teacher_dir or None,
            input_size=cfg['data']['input_size'],
            out_h=cfg['data']['out_h'],
            out_w=cfg['data']['out_w'],
            param_dir=args.val_param_dir or None,
            map_size=cfg['data']['map_size'],
        )
        val_loader = DataLoader(val_dataset, batch_size=cfg['train']['batch_size'], shuffle=False, num_workers=cfg['train']['num_workers'])

    outdir = Path(args.outdir or os.path.join(cfg['paths']['outputs_root'], 'checkpoints'))
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / 'train_log.csv'
    metrics_path = outdir / 'metrics.yaml'

    best_loss = float('inf')
    best_epoch = None
    run_started_at = datetime.now(timezone.utc).isoformat()

    for epoch in range(cfg['train']['epochs']):
        epoch_loss = run_epoch(model, loader, optimizer, rcfg, cfg, device, train=True)
        val_loss = run_epoch(model, val_loader, None, rcfg, cfg, device, train=False) if val_loader is not None else None
        selection_loss = val_loss if val_loss is not None else epoch_loss
        selection_metric = 'val_loss' if val_loss is not None else 'train_loss'
        if val_loss is None:
            print(f'epoch={epoch+1} train_loss={epoch_loss:.6f}')
        else:
            print(f'epoch={epoch+1} train_loss={epoch_loss:.6f} val_loss={val_loss:.6f}')
        ckpt = {
            'epoch': epoch + 1,
            'model': model.state_dict(),
            'optimizer': optimizer.state_dict(),
            'loss': epoch_loss,
            'train_loss': epoch_loss,
            'val_loss': val_loss,
            'selection_loss': selection_loss,
            'selection_metric': selection_metric,
            'config': cfg,
        }
        torch.save(ckpt, outdir / 'last.pt')
        if selection_loss < best_loss:
            best_loss = selection_loss
            best_epoch = epoch + 1
            torch.save(ckpt, outdir / 'best.pt')

        append_train_log(csv_path, {
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'epoch': epoch + 1,
            'train_loss': float(epoch_loss),
            'val_loss': float(val_loss) if val_loss is not None else None,
            'selection_loss': float(selection_loss),
            'selection_metric': selection_metric,
            'best_loss_so_far': float(best_loss),
        })

        write_metrics_yaml(metrics_path, {
            'config': str(Path(args.config).resolve()),
            'low_dir': str(Path(args.low_dir).resolve()),
            'high_dir': str(Path(args.high_dir).resolve()),
            'teacher_dir': str(Path(args.teacher_dir).resolve()) if args.teacher_dir else None,
            'param_dir': str(Path(args.param_dir).resolve()) if args.param_dir else None,
            'val_low_dir': str(Path(args.val_low_dir).resolve()) if args.val_low_dir else None,
            'val_high_dir': str(Path(args.val_high_dir).resolve()) if args.val_high_dir else None,
            'val_teacher_dir': str(Path(args.val_teacher_dir).resolve()) if args.val_teacher_dir else None,
            'val_param_dir': str(Path(args.val_param_dir).resolve()) if args.val_param_dir else None,
            'outdir': str(outdir.resolve()),
            'device': str(device),
            'model_type': cfg['model']['type'],
            'seed': cfg['train']['seed'],
            'epochs_requested': cfg['train']['epochs'],
            'batch_size': cfg['train']['batch_size'],
            'selection_metric': selection_metric,
            'train_log_csv': str(csv_path.resolve()),
            'best_checkpoint': str((outdir / 'best.pt').resolve()),
            'last_checkpoint': str((outdir / 'last.pt').resolve()),
            'best_epoch': best_epoch,
            'best_loss': float(best_loss),
            'latest_epoch': epoch + 1,
            'latest_train_loss': float(epoch_loss),
            'latest_val_loss': float(val_loss) if val_loss is not None else None,
            'latest_selection_loss': float(selection_loss),
            'run_started_at_utc': run_started_at,
            'last_updated_at_utc': datetime.now(timezone.utc).isoformat(),
        })

    print('training done')
    print('train_log =', csv_path)
    print('metrics =', metrics_path)


if __name__ == '__main__':
    main()
