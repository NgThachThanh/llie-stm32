import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch
import yaml

from src.models.rgb_models import OneStepRGBStudent, RGBCNNBaseline


def load_cfg(path: Path):
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def make_model(cfg):
    mcfg = cfg['model']
    if mcfg['type'] == 'rgb_cnn_baseline':
        return RGBCNNBaseline(mcfg.get('base_channels', 16), mcfg.get('depth', 4))
    if mcfg['type'] == 'one_step_rgb_student':
        return OneStepRGBStudent(mcfg.get('base_channels', 24))
    raise ValueError(f"Unsupported RGB model type: {mcfg['type']}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', required=True)
    p.add_argument('--checkpoint', required=True)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--opset', type=int, default=13)
    args = p.parse_args()

    cfg = load_cfg(Path(args.config))
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    ckpt = torch.load(args.checkpoint, map_location='cpu')
    model = make_model(cfg)
    model.load_state_dict(ckpt['model'])
    model.eval()

    size = int(cfg['data']['image_size'])
    example = torch.randn(1, 3, size, size)
    ts_path = outdir / 'model.ts'
    torch.jit.trace(model, example).save(str(ts_path))

    manifest = {
        'config': str(Path(args.config).resolve()),
        'checkpoint': str(Path(args.checkpoint).resolve()),
        'model_type': cfg['model']['type'],
        'input_shape_nchw': [1, 3, size, size],
        'output_shape_nchw': [1, 3, size, size],
        'torchscript': str(ts_path.resolve()),
    }

    try:
        import onnx
        onnx_path = outdir / 'model.onnx'
        torch.onnx.export(
            model,
            example,
            str(onnx_path),
            input_names=['input'],
            output_names=['rgb'],
            opset_version=args.opset,
            do_constant_folding=True,
        )
        manifest['onnx'] = str(onnx_path.resolve())
    except Exception as e:
        manifest['onnx'] = None
        manifest['onnx_error'] = f'{type(e).__name__}: {e}'

    manifest_path = outdir / 'export_manifest.yaml'
    with manifest_path.open('w', encoding='utf-8') as f:
        yaml.safe_dump(manifest, f, sort_keys=False)
    print(f'export complete -> {manifest_path}')


if __name__ == '__main__':
    main()
