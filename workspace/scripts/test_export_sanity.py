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

from src.models.student_v1 import StudentGlobalOnly, StudentV1


def load_cfg(path: Path):
    with path.open('r', encoding='utf-8') as f:
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


def rgb_to_y(rgb: np.ndarray) -> np.ndarray:
    rgb = rgb.astype(np.float32) / 255.0
    y = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    return y.astype(np.float32)


def preprocess(image_path: Path, input_size: int) -> np.ndarray:
    bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(image_path)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    y = rgb_to_y(rgb)
    y96 = cv2.resize(y, (input_size, input_size), interpolation=cv2.INTER_AREA)
    return y96.astype(np.float32)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--tflite', required=True)
    parser.add_argument('--image', required=True)
    args = parser.parse_args()

    cfg = load_cfg(Path(args.config))
    input_size = int(cfg['data']['input_size'])
    x = preprocess(Path(args.image), input_size)

    model = make_model(cfg)
    ckpt = torch.load(args.checkpoint, map_location='cpu')
    state = ckpt['model'] if isinstance(ckpt, dict) and 'model' in ckpt else ckpt
    model.load_state_dict(state)
    model.eval()

    x_pt = torch.from_numpy(x[None, None, :, :])
    with torch.no_grad():
        out_pt = model(x_pt)
        pt_global = out_pt['global_raw'].detach().cpu().numpy()[0]

    import tensorflow as tf
    interpreter = tf.lite.Interpreter(model_path=args.tflite)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()[0]
    output_details = interpreter.get_output_details()[0]

    x_tf = x[None, :, :, None].astype(np.float32)
    interpreter.set_tensor(input_details['index'], x_tf)
    interpreter.invoke()
    tf_global = interpreter.get_tensor(output_details['index'])[0]

    abs_diff = np.abs(pt_global - tf_global)

    print('image =', args.image)
    print('pytorch_global_raw =', pt_global.tolist())
    print('tflite_global_raw =', tf_global.tolist())
    print('abs_diff =', abs_diff.tolist())
    print('max_abs_diff =', float(abs_diff.max()))
    print('mean_abs_diff =', float(abs_diff.mean()))
    print('tflite_input_shape =', list(input_details['shape']))
    print('tflite_output_shape =', list(output_details['shape']))


if __name__ == '__main__':
    main()
