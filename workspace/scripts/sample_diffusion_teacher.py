import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2
import numpy as np
import torch
import yaml

from src.data.image_dataset import read_rgb, resize_hw
from src.models.diffusion_teacher import TinyDiffusionTeacher


def load_cfg(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def to_tensor_rgb(path: Path, image_size: int) -> torch.Tensor:
    rgb = resize_hw(read_rgb(str(path)), image_size, image_size)
    arr = rgb.astype(np.float32) / 255.0
    return torch.from_numpy(np.transpose(arr, (2, 0, 1)).copy())


def to_u8(x: torch.Tensor) -> np.ndarray:
    arr = x.detach().cpu().clamp(0, 1).numpy().transpose(1, 2, 0)
    return (arr * 255.0).round().astype(np.uint8)


def denoise(model, low, steps: int):
    x = torch.randn_like(low)
    with torch.no_grad():
        for step in reversed(range(steps)):
            t = torch.full((low.shape[0],), step, device=low.device, dtype=torch.long)
            pred_noise = model(x, low, t)
            alpha_bar = 1.0 - (float(step) / max(steps - 1, 1)) * 0.95
            alpha_bar_prev = 1.0 - (float(max(step - 1, 0)) / max(steps - 1, 1)) * 0.95
            x0 = (x - ((1.0 - alpha_bar) ** 0.5) * pred_noise) / max(alpha_bar ** 0.5, 1e-6)
            x = (alpha_bar_prev ** 0.5) * x0
    return x.clamp(0, 1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', required=True)
    p.add_argument('--checkpoint', required=True)
    p.add_argument('--low-dir', required=True)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--limit', type=int, default=0)
    args = p.parse_args()

    cfg = load_cfg(args.config)
    device = torch.device(cfg['train']['device'] if torch.cuda.is_available() else 'cpu')
    model = TinyDiffusionTeacher(
        base_channels=cfg['model'].get('base_channels', 32),
        time_dim=cfg['model'].get('time_dim', 32),
    ).to(device)
    ckpt = torch.load(args.checkpoint, map_location=device)
    model.load_state_dict(ckpt['model'])
    model.eval()

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    files = []
    for ext in ('*.png', '*.jpg', '*.jpeg', '*.bmp'):
        files.extend(sorted(Path(args.low_dir).glob(ext)))
    if args.limit > 0:
        files = files[:args.limit]

    for path in files:
        low = to_tensor_rgb(path, cfg['data']['image_size']).unsqueeze(0).to(device)
        pred = denoise(model, low, cfg['diffusion']['steps'])[0]
        cv2.imwrite(str(outdir / f'{path.stem}.png'), cv2.cvtColor(to_u8(pred), cv2.COLOR_RGB2BGR))
    print(f'saved={len(files)} -> {outdir}')


if __name__ == '__main__':
    main()
