import argparse
import subprocess
from pathlib import Path

import cv2
import numpy as np


def collect_images(root: Path):
    files = []
    for ext in ('*.png', '*.jpg', '*.jpeg', '*.bmp'):
        files.extend(sorted(root.glob(ext)))
    return files


def rgb_to_y(img_rgb: np.ndarray) -> np.ndarray:
    img = img_rgb.astype(np.float32) / 255.0
    y = 0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]
    return y.astype(np.float32)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--teacher-repo', type=str, required=True)
    parser.add_argument('--weights', type=str, default='Zero-DCE_code/snapshots/Epoch99.pth')
    parser.add_argument('--input-dir', type=str, required=True)
    parser.add_argument('--output-dir', type=str, required=True)
    parser.add_argument('--venv-python', type=str, default='/home/stonies/venvs/llie-train/bin/python')
    parser.add_argument('--out-h', type=int, default=120)
    parser.add_argument('--out-w', type=int, default=160)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--fail-on-missing', action='store_true')
    parser.add_argument('--device', type=str, default='cuda')
    args = parser.parse_args()

    teacher_repo = Path(args.teacher_repo)
    infer_script = Path(__file__).resolve().parent / 'zero_dce_infer_single_folder.py'
    weights_path = Path(args.weights)
    if not weights_path.is_absolute():
        weights_path = teacher_repo / args.weights
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not teacher_repo.exists():
        raise FileNotFoundError(f'Missing teacher repo: {teacher_repo}')
    if not infer_script.exists():
        raise FileNotFoundError(f'Missing inference helper: {infer_script}')
    if not weights_path.exists():
        raise FileNotFoundError(f'Missing teacher weights: {weights_path}')
    if not Path(args.venv_python).exists():
        raise FileNotFoundError(f'Missing python interpreter: {args.venv_python}')

    images = collect_images(input_dir)
    if args.limit > 0:
        images = images[: args.limit]
    if not images:
        raise RuntimeError(f'No images found in {input_dir}')

    tmp_input = output_dir.parent / f'{output_dir.name}__tmp_input_manifest'
    tmp_output = output_dir.parent / f'{output_dir.name}__tmp_rgb_outputs'
    tmp_input.mkdir(parents=True, exist_ok=True)
    tmp_output.mkdir(parents=True, exist_ok=True)

    for p in tmp_input.glob('*'):
        if p.is_file() or p.is_symlink():
            p.unlink()
    for p in tmp_output.glob('*'):
        if p.is_file() or p.is_symlink():
            p.unlink()

    import shutil
    for img in images:
        shutil.copy2(img, tmp_input / img.name)

    print(f'prepared {len(images)} isolated teacher inputs -> {tmp_input}')

    subprocess.run(
        [
            args.venv_python,
            str(infer_script),
            '--teacher-repo', str(teacher_repo),
            '--weights', str(weights_path),
            '--input-dir', str(tmp_input),
            '--output-dir', str(tmp_output),
            '--device', args.device,
        ],
        check=True,
    )

    success = 0
    missing = 0
    failed = 0
    for img_path in images:
        result_path = tmp_output / img_path.name
        if not result_path.exists():
            print(f'warning: missing teacher output for {img_path.name}')
            missing += 1
            continue

        bgr = cv2.imread(str(result_path), cv2.IMREAD_COLOR)
        if bgr is None:
            print(f'warning: failed to read teacher output for {img_path.name}')
            failed += 1
            continue

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        y = rgb_to_y(rgb)
        if y.shape != (args.out_h, args.out_w):
            y = cv2.resize(y, (args.out_w, args.out_h), interpolation=cv2.INTER_AREA)
        np.save(output_dir / f'{img_path.stem}.npy', y)
        success += 1

    print('teacher target summary:')
    print(f'  input images   : {len(images)}')
    print(f'  success saved  : {success}')
    print(f'  missing output : {missing}')
    print(f'  failed decode  : {failed}')
    print(f'  saved dir      : {output_dir}')

    if args.fail_on_missing and (missing > 0 or failed > 0):
        raise RuntimeError('Teacher generation incomplete and --fail-on-missing was set')


if __name__ == '__main__':
    main()
