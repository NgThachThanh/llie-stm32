import argparse
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import minimize


def read_y(path: Path, out_h: int, out_w: int) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    y = 0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]
    y = cv2.resize(y, (out_w, out_h), interpolation=cv2.INTER_AREA)
    return y.astype(np.float32)


def read_teacher_y(path: Path, out_h: int, out_w: int) -> np.ndarray:
    y = np.load(str(path)).astype(np.float32)
    if y.ndim != 2:
        raise ValueError(f'Expected 2D teacher array, got shape {y.shape} from {path}')
    if y.shape != (out_h, out_w):
        y = cv2.resize(y, (out_w, out_h), interpolation=cv2.INTER_AREA)
    y = np.clip(y, 0.0, 1.0)
    return y.astype(np.float32)


def render_global(y: np.ndarray, gain: float, gamma: float, lift: float) -> np.ndarray:
    x = np.clip(y + lift / 255.0, 0.0, 1.0)
    x = np.clip(x * gain, 1e-4, 1.0)
    x = np.power(x, gamma)
    return np.clip(x, 0.0, 1.0)


def fit_global_controls(y_low: np.ndarray, y_tgt: np.ndarray, bounds, x0):
    def objective(v):
        gain, gamma, lift = v
        pred = render_global(y_low, gain, gamma, lift)
        return np.mean(np.abs(pred - y_tgt))

    res = minimize(objective, x0=np.array(x0, dtype=np.float64), bounds=bounds, method='L-BFGS-B')
    return res.x.astype(np.float32)


def make_gain_map(y_low: np.ndarray, y_tgt: np.ndarray, map_size: int, gain: float, gamma: float, lift: float, ratio_min: float, ratio_max: float) -> np.ndarray:
    base = render_global(y_low, gain, gamma, lift)
    ratio = y_tgt / np.clip(base, 1e-4, 1.0)
    ratio = np.clip(ratio, ratio_min, ratio_max)
    ratio_small = cv2.resize(ratio, (map_size, map_size), interpolation=cv2.INTER_AREA)
    return ratio_small.astype(np.float32)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--low-dir', type=str, required=True)
    parser.add_argument('--teacher-dir', type=str, required=True)
    parser.add_argument('--output-dir', type=str, required=True)
    parser.add_argument('--out-h', type=int, default=120)
    parser.add_argument('--out-w', type=int, default=160)
    parser.add_argument('--map-size', type=int, default=8)
    parser.add_argument('--gain-min', type=float, default=1.0)
    parser.add_argument('--gain-max', type=float, default=4.0)
    parser.add_argument('--gamma-min', type=float, default=0.45)
    parser.add_argument('--gamma-max', type=float, default=1.6)
    parser.add_argument('--lift-min', type=float, default=0.0)
    parser.add_argument('--lift-max', type=float, default=40.0)
    parser.add_argument('--ratio-min', type=float, default=0.6)
    parser.add_argument('--ratio-max', type=float, default=1.8)
    parser.add_argument('--fail-on-missing', action='store_true')
    args = parser.parse_args()

    low_dir = Path(args.low_dir)
    teacher_dir = Path(args.teacher_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    bounds = [
        (args.gain_min, args.gain_max),
        (args.gamma_min, args.gamma_max),
        (args.lift_min, args.lift_max),
    ]
    x0 = [min(max(1.5, args.gain_min), args.gain_max), min(max(0.8, args.gamma_min), args.gamma_max), min(max(6.0, args.lift_min), args.lift_max)]

    success = 0
    skipped = 0
    bound_hits = 0
    for low_path in sorted(low_dir.glob('*')):
        if low_path.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.bmp'}:
            continue
        teacher_path = teacher_dir / f'{low_path.stem}.npy'
        if not teacher_path.exists():
            print(f'skip {low_path.name}: no teacher target')
            skipped += 1
            continue

        y_low = read_y(low_path, args.out_h, args.out_w)
        y_tgt = read_teacher_y(teacher_path, args.out_h, args.out_w)
        gain, gamma, lift = fit_global_controls(y_low, y_tgt, bounds=bounds, x0=x0)
        gain_map = make_gain_map(y_low, y_tgt, args.map_size, float(gain), float(gamma), float(lift), ratio_min=args.ratio_min, ratio_max=args.ratio_max)

        if np.isclose(gain, args.gain_min) or np.isclose(gain, args.gain_max) or np.isclose(gamma, args.gamma_min) or np.isclose(gamma, args.gamma_max) or np.isclose(lift, args.lift_min) or np.isclose(lift, args.lift_max):
            bound_hits += 1

        np.savez(
            output_dir / f'{low_path.stem}.npz',
            gain_global=gain,
            gamma_global=gamma,
            lift_black=lift,
            gain_map=gain_map,
        )
        success += 1
        print(f'fitted {low_path.name}')

    print('fit summary:')
    print(f'  success   : {success}')
    print(f'  skipped   : {skipped}')
    print(f'  boundhits : {bound_hits}')
    print(f'  outdir    : {output_dir}')
    print('fit config:')
    print(f'  gain  : [{args.gain_min}, {args.gain_max}]')
    print(f'  gamma : [{args.gamma_min}, {args.gamma_max}]')
    print(f'  lift  : [{args.lift_min}, {args.lift_max}]')
    print(f'  ratio : [{args.ratio_min}, {args.ratio_max}]')

    if args.fail_on_missing and skipped > 0:
        raise RuntimeError('Pseudo-control fitting incomplete and --fail-on-missing was set')


if __name__ == '__main__':
    main()
