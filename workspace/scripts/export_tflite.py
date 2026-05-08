import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch
import yaml

from src.models.student_v1 import StudentGlobalOnly, StudentV1


class ExportableStudentGlobalOnly(torch.nn.Module):
    def __init__(self, model: StudentGlobalOnly):
        super().__init__()
        self.model = model

    def forward(self, x: torch.Tensor):
        out = self.model(x)
        return out['global_raw']


class ExportableStudentV1(torch.nn.Module):
    def __init__(self, model: StudentV1):
        super().__init__()
        self.model = model

    def forward(self, x: torch.Tensor):
        out = self.model(x)
        local_raw = out['local_raw']
        global_raw = out['global_raw']
        return local_raw, global_raw


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


def main():
    parser = argparse.ArgumentParser(description='Export LLIE student model to TorchScript and, if available, ONNX/TFLite.')
    parser.add_argument('--config', type=str, required=True)
    parser.add_argument('--checkpoint', type=str, required=True)
    parser.add_argument('--output-dir', type=str, required=True)
    parser.add_argument('--opset', type=int, default=13)
    args = parser.parse_args()

    cfg = load_cfg(Path(args.config))
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_path = Path(args.checkpoint)
    ckpt = torch.load(checkpoint_path, map_location='cpu')

    model = make_model(cfg)
    state = ckpt['model'] if isinstance(ckpt, dict) and 'model' in ckpt else ckpt
    model.load_state_dict(state)
    model.eval()

    model_type = cfg['model']['type']
    if model_type == 'student_global_only':
        export_model = ExportableStudentGlobalOnly(model)
        output_names = ['global_raw']
    else:
        export_model = ExportableStudentV1(model)
        output_names = ['local_raw', 'global_raw']

    input_size = int(cfg['data']['input_size'])
    example = torch.randn(1, 1, input_size, input_size, dtype=torch.float32)

    ts_path = out_dir / 'model.ts'
    traced = torch.jit.trace(export_model, example)
    traced.save(str(ts_path))

    manifest = {
        'config': str(Path(args.config).resolve()),
        'checkpoint': str(checkpoint_path.resolve()),
        'model_type': model_type,
        'input_shape': [1, 1, input_size, input_size],
        'torchscript': str(ts_path.resolve()),
    }

    onnx_error = None
    try:
        import onnx
        onnx_path = out_dir / 'model.onnx'
        torch.onnx.export(
            export_model,
            example,
            str(onnx_path),
            input_names=['input'],
            output_names=output_names,
            opset_version=args.opset,
            do_constant_folding=True,
        )
        manifest['onnx'] = str(onnx_path.resolve())
    except Exception as e:
        onnx_error = f'{type(e).__name__}: {e}'
        manifest['onnx'] = None
        manifest['onnx_error'] = onnx_error

    tflite_error = None
    if manifest.get('onnx'):
        try:
            import tensorflow as tf
            from onnx2tf import convert

            saved_model_dir = out_dir / 'saved_model'
            convert(
                input_onnx_file_path=manifest['onnx'],
                output_folder_path=str(saved_model_dir),
                copy_onnx_input_output_names_to_tflite=True,
                non_verbose=True,
            )

            converter = tf.lite.TFLiteConverter.from_saved_model(str(saved_model_dir))
            tflite_bytes = converter.convert()
            tflite_path = out_dir / 'model.tflite'
            tflite_path.write_bytes(tflite_bytes)
            manifest['saved_model'] = str(saved_model_dir.resolve())
            manifest['tflite'] = str(tflite_path.resolve())
        except Exception as e:
            tflite_error = f'{type(e).__name__}: {e}'
            manifest['saved_model'] = None
            manifest['tflite'] = None
            manifest['tflite_error'] = tflite_error
    else:
        manifest['saved_model'] = None
        manifest['tflite'] = None
        manifest['tflite_error'] = 'Skipped because ONNX export was unavailable.'

    manifest_path = out_dir / 'export_manifest.yaml'
    with manifest_path.open('w', encoding='utf-8') as f:
        yaml.safe_dump(manifest, f, sort_keys=False)

    print('export complete')
    print('torchscript =', ts_path)
    if manifest.get('onnx'):
        print('onnx =', manifest['onnx'])
    else:
        print('onnx export unavailable:', onnx_error)
    if manifest.get('tflite'):
        print('tflite =', manifest['tflite'])
    else:
        print('tflite export unavailable:', manifest.get('tflite_error'))
    print('manifest =', manifest_path)


if __name__ == '__main__':
    main()
