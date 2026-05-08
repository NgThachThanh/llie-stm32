import argparse
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader

from src.data.video_dataset import TemporalClipDataset
from src.losses.losses import build_image_loss, temporal_loss
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
        return StudentGlobalOnly(in_channels=mcfg.get('in_channels', 1), base_channels=mcfg.get('base_channels', 8))
    return StudentV1(
        in_channels=mcfg.get('in_channels', 1),
        base_channels=mcfg.get('base_channels', 8),
        local_hidden_channels=mcfg.get('local_hidden_channels', 4),
        map_size=mcfg.get('map_size', 8),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True)
    parser.add_argument('--clips-root', type=str, required=True)
    parser.add_argument('--teacher-root', type=str, default='')
    parser.add_argument('--checkpoint', type=str, default='')
    parser.add_argument('--outdir', type=str, default='')
    args = parser.parse_args()

    cfg = load_cfg(args.config)
    set_seed(cfg['train']['seed'])
    device = torch.device(cfg['train']['device'] if torch.cuda.is_available() else 'cpu')

    model = make_model(cfg).to(device)
    if args.checkpoint:
        ckpt = torch.load(args.checkpoint, map_location=device)
        model.load_state_dict(ckpt['model'])

    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg['train']['lr'], weight_decay=cfg['train']['weight_decay'])
    rcfg = RenderConfig(out_h=cfg['data']['out_h'], out_w=cfg['data']['out_w'], ranges=RangeConfig(**cfg['ranges']))

    dataset = TemporalClipDataset(
        clips_root=args.clips_root,
        teacher_root=args.teacher_root or None,
        input_size=cfg['data']['input_size'],
        out_h=cfg['data']['out_h'],
        out_w=cfg['data']['out_w'],
    )
    loader = DataLoader(dataset, batch_size=cfg['train']['batch_size'], shuffle=True, num_workers=cfg['train']['num_workers'])

    outdir = args.outdir or os.path.join(cfg['paths']['outputs_root'], 'temporal_checkpoints')
    os.makedirs(outdir, exist_ok=True)

    for epoch in range(cfg['train']['epochs']):
        model.train()
        running = 0.0
        for batch in loader:
            y96_t = batch['y_low_96_t'].to(device)
            yfull_t = batch['y_low_full_t'].to(device)
            y96_t1 = batch['y_low_96_t1'].to(device)
            yfull_t1 = batch['y_low_full_t1'].to(device)
            tgt_t = batch['teacher_y_full_t'].to(device) if 'teacher_y_full_t' in batch else yfull_t
            tgt_t1 = batch['teacher_y_full_t1'].to(device) if 'teacher_y_full_t1' in batch else yfull_t1

            out_t = model(y96_t)
            dec_t = decode_outputs(out_t, rcfg)
            pred_t, _ = render_luma(yfull_t, dec_t, rcfg)
            losses_t = build_image_loss(pred_t, tgt_t, dec_t, target_params=None, weights=cfg['loss'])

            out_t1 = model(y96_t1)
            dec_t1 = decode_outputs(out_t1, rcfg)
            pred_t1, _ = render_luma(yfull_t1, dec_t1, rcfg)
            losses_t1 = build_image_loss(pred_t1, tgt_t1, dec_t1, target_params=None, weights=cfg['loss'])

            loss_temp = temporal_loss(pred_t, pred_t1, tgt_t, tgt_t1)
            loss = losses_t['total'] + losses_t1['total'] + cfg['temporal'].get('weight', 0.2) * loss_temp

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            running += loss.item()

        epoch_loss = running / max(1, len(loader))
        print(f'epoch={epoch+1} temporal_loss={epoch_loss:.6f}')
        torch.save({'epoch': epoch + 1, 'model': model.state_dict(), 'loss': epoch_loss}, os.path.join(outdir, 'last.pt'))

    print('temporal training done')


if __name__ == '__main__':
    main()
