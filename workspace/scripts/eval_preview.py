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

from src.data.image_dataset import read_rgb, rgb_to_y, resize_hw
from src.models.student_v1 import StudentGlobalOnly, StudentV1
from src.render.luma_renderer import RangeConfig, RenderConfig, decode_outputs, render_luma


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


def collect_images(root: Path):
    files = []
    for ext in ('*.png', '*.jpg', '*.jpeg', '*.bmp'):
        files.extend(sorted(root.glob(ext)))
    return files


def to_u8(y01: np.ndarray) -> np.ndarray:
    y01 = np.clip(y01, 0.0, 1.0)
    return (y01 * 255.0).round().astype(np.uint8)


def gray3(y01: np.ndarray) -> np.ndarray:
    g = to_u8(y01)
    return np.stack([g, g, g], axis=-1)


def put_text(img: np.ndarray, text: str):
    out = img.copy()
    cv2.putText(out, text, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1, cv2.LINE_AA)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True)
    parser.add_argument('--checkpoint', type=str, required=True)
    parser.add_argument('--low-dir', type=str, required=True)
    parser.add_argument('--output-dir', type=str, required=True)
    parser.add_argument('--high-dir', type=str, default='')
    parser.add_argument('--teacher-dir', type=str, default='')
    parser.add_argument('--limit', type=int, default=20)
    args = parser.parse_args()

    cfg = load_cfg(args.config)
    device = torch.device(cfg['train']['device'] if torch.cuda.is_available() else 'cpu')
    model = make_model(cfg).to(device)
    ckpt = torch.load(args.checkpoint, map_location=device)
    model.load_state_dict(ckpt['model'])
    model.eval()

    rcfg = RenderConfig(
        out_h=cfg['data']['out_h'],
        out_w=cfg['data']['out_w'],
        ranges=RangeConfig(**cfg['ranges']),
    )

    low_dir = Path(args.low_dir)
    high_dir = Path(args.high_dir) if args.high_dir else None
    teacher_dir = Path(args.teacher_dir) if args.teacher_dir else None
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = collect_images(low_dir)
    if args.limit > 0:
        files = files[: args.limit]

    count = 0
    with torch.no_grad():
        for low_path in files:
            low_rgb = read_rgb(str(low_path))
            low_y = rgb_to_y(low_rgb)
            low_y_full = resize_hw(low_y, rcfg.out_h, rcfg.out_w)
            low_y_96 = resize_hw(low_y_full, cfg['data']['input_size'], cfg['data']['input_size'], interpolation=cv2.INTER_AREA)

            x96 = torch.from_numpy(low_y_96[None, None, ...]).to(device)
            yfull = torch.from_numpy(low_y_full[None, None, ...]).to(device)

            out = model(x96)
            decoded = decode_outputs(out, rcfg)
            pred, _ = render_luma(yfull, decoded, rcfg)
            pred_np = pred[0, 0].detach().cpu().numpy()

            pred_img = gray3(pred_np)
            low_img = gray3(low_y_full)
            panels = [put_text(low_img, 'low'), put_text(pred_img, 'pred')]

            if high_dir:
                hp = high_dir / low_path.name
                if hp.exists():
                    high_y = rgb_to_y(read_rgb(str(hp)))
                    high_y = resize_hw(high_y, rcfg.out_h, rcfg.out_w)
                    panels.append(put_text(gray3(high_y), 'high'))

            if teacher_dir:
                tp = teacher_dir / f'{low_path.stem}.npy'
                if tp.exists():
                    ty = np.load(str(tp)).astype(np.float32)
                    if ty.shape != (rcfg.out_h, rcfg.out_w):
                        ty = resize_hw(ty, rcfg.out_h, rcfg.out_w)
                    panels.append(put_text(gray3(ty), 'teacher'))

            canvas = np.concatenate(panels, axis=1)
            cv2.imwrite(str(out_dir / f'{low_path.stem}_preview.png'), cv2.cvtColor(canvas, cv2.COLOR_RGB2BGR))
            cv2.imwrite(str(out_dir / f'{low_path.stem}_pred.png'), cv2.cvtColor(pred_img, cv2.COLOR_RGB2BGR))
            count += 1

    print(f'saved previews: {count} -> {out_dir}')


if __name__ == '__main__':
    main()
