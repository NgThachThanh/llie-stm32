import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import torch
import torch.nn.functional as F
import yaml
from torch.utils.data import DataLoader

from src.data.image_dataset import RGBPairedImageDataset
from src.models.diffusion_teacher import TinyDiffusionTeacher


def load_cfg(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def q_sample(clean, noise, t, steps):
    alpha_bar = 1.0 - (t.float() / max(steps - 1, 1)) * 0.95
    alpha_bar = alpha_bar.view(-1, 1, 1, 1)
    return alpha_bar.sqrt() * clean + (1.0 - alpha_bar).sqrt() * noise


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', required=True)
    p.add_argument('--low-dir', required=True)
    p.add_argument('--high-dir', required=True)
    p.add_argument('--outdir', default='')
    args = p.parse_args()
    cfg = load_cfg(args.config)
    set_seed(cfg['train']['seed'])
    device = torch.device(cfg['train']['device'] if torch.cuda.is_available() else 'cpu')
    model = TinyDiffusionTeacher(
        base_channels=cfg['model'].get('base_channels', 32),
        time_dim=cfg['model'].get('time_dim', 32),
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg['train']['lr'], weight_decay=cfg['train']['weight_decay'])
    ds = RGBPairedImageDataset(args.low_dir, args.high_dir, image_size=cfg['data']['image_size'])
    loader = DataLoader(ds, batch_size=cfg['train']['batch_size'], shuffle=True, num_workers=cfg['train']['num_workers'])
    steps = cfg['diffusion']['steps']
    outdir = Path(args.outdir or Path(cfg['paths']['outputs_root']) / 'checkpoints_teacher')
    outdir.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, cfg['train']['epochs'] + 1):
        model.train()
        running = 0.0
        for batch in loader:
            low = batch['rgb_low'].to(device)
            high = batch['rgb_high'].to(device)
            noise = torch.randn_like(high)
            t = torch.randint(0, steps, (high.shape[0],), device=device)
            noisy = q_sample(high, noise, t, steps)
            pred_noise = model(noisy, low, t)
            loss = F.mse_loss(pred_noise, noise)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            running += float(loss.item())
        payload = {'epoch': epoch, 'model': model.state_dict(), 'optimizer': optimizer.state_dict(), 'config': cfg}
        torch.save(payload, outdir / 'last.pt')
        print(f"epoch={epoch} noise_mse={running / max(1, len(loader)):.6f}")


if __name__ == '__main__':
    main()
