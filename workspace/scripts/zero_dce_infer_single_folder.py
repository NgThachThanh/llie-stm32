import argparse
from pathlib import Path
import time

import numpy as np
import torch
import torchvision
from PIL import Image


def load_teacher(repo_root: Path, weights_path: Path, device: torch.device):
    import sys
    zero_dce_code = repo_root / 'Zero-DCE_code'
    if str(zero_dce_code) not in sys.path:
        sys.path.insert(0, str(zero_dce_code))
    import model

    net = model.enhance_net_nopool().to(device)
    state = torch.load(str(weights_path), map_location=device)
    net.load_state_dict(state)
    net.eval()
    return net


def collect_images(root: Path):
    files = []
    for ext in ('*.png', '*.jpg', '*.jpeg', '*.bmp'):
        files.extend(sorted(root.glob(ext)))
    return files


def run_one(net, image_path: Path, output_path: Path, device: torch.device):
    data_lowlight = Image.open(image_path).convert('RGB')
    arr = np.asarray(data_lowlight, dtype=np.float32) / 255.0
    ten = torch.from_numpy(arr).float().permute(2, 0, 1).unsqueeze(0).to(device)
    start = time.time()
    with torch.no_grad():
        _, enhanced_image, _ = net(ten)
    elapsed = time.time() - start
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torchvision.utils.save_image(enhanced_image, str(output_path))
    return elapsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--teacher-repo', type=str, required=True)
    parser.add_argument('--weights', type=str, required=True)
    parser.add_argument('--input-dir', type=str, required=True)
    parser.add_argument('--output-dir', type=str, required=True)
    parser.add_argument('--device', type=str, default='cuda')
    args = parser.parse_args()

    repo_root = Path(args.teacher_repo)
    weights_path = Path(args.weights)
    if not weights_path.is_absolute():
        weights_path = repo_root / weights_path
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    device = torch.device(args.device if args.device == 'cpu' or torch.cuda.is_available() else 'cpu')
    if not repo_root.exists():
        raise FileNotFoundError(repo_root)
    if not weights_path.exists():
        raise FileNotFoundError(weights_path)
    if not input_dir.exists():
        raise FileNotFoundError(input_dir)

    images = collect_images(input_dir)
    if not images:
        raise RuntimeError(f'No images found in {input_dir}')

    net = load_teacher(repo_root, weights_path, device)
    total = 0.0
    for img in images:
        out = output_dir / img.name
        elapsed = run_one(net, img, out, device)
        total += elapsed
        print(f'{img.name}: {elapsed:.6f}s')

    print(f'processed {len(images)} images -> {output_dir}')
    print(f'total_infer_seconds={total:.6f}')
    print(f'avg_infer_seconds={total/len(images):.6f}')


if __name__ == '__main__':
    main()
