# Training Workspace

This directory contains the training, preview, and export code for the STM32H750 low-light student model.

Run commands from `workspace/` unless noted otherwise.

## Setup

```bash
cd llie-stm32
python3 -m venv .venv
source .venv/bin/activate
pip install torch torchvision numpy scipy pyyaml opencv-python-headless
cd workspace
```

Optional teacher/reference repos can be cloned under `../repos/`.

## Layout

```text
configs/   YAML configs
src/       data, model, renderer, losses
scripts/   dataset, train, preview, export helpers
outputs/   local generated artifacts, mostly ignored by git
```

## Dataset Layout

Expected paired dataset:

```text
../datasets/lol/
  train/low/
  train/high/
  val/low/
  val/high/
```

Optional generated folders:

```text
../datasets/lol/train/teacher_y/
../datasets/lol/train/pseudo_ctrl_v2/
```

## Canonical Config

```text
configs/image_first.yaml
```

Current baseline model type:

```text
student_global_only
```

Included baseline artifacts:

```text
outputs/checkpoints_image_first/
outputs/previews_image_first/
outputs/export_image_first_full/
```

## Train

```bash
python scripts/train_float.py \
  --config configs/image_first.yaml \
  --low-dir ../datasets/lol/train/low \
  --high-dir ../datasets/lol/train/high \
  --teacher-dir ../datasets/lol/train/teacher_y \
  --param-dir ../datasets/lol/train/pseudo_ctrl_v2 \
  --val-low-dir ../datasets/lol/val/low \
  --val-high-dir ../datasets/lol/val/high \
  --val-teacher-dir ../datasets/lol/val/teacher_y \
  --outdir outputs/checkpoints_image_first
```

If teacher targets are unavailable, omit `--teacher-dir` and `--val-teacher-dir`.

## Preview

```bash
python scripts/eval_preview.py \
  --config configs/image_first.yaml \
  --checkpoint outputs/checkpoints_image_first/best.pt \
  --low-dir ../datasets/lol/val/low \
  --high-dir ../datasets/lol/val/high \
  --teacher-dir ../datasets/lol/val/teacher_y \
  --output-dir outputs/previews_image_first
```

## Export

```bash
python scripts/export_tflite.py \
  --config configs/image_first.yaml \
  --checkpoint outputs/checkpoints_image_first/best.pt \
  --output-dir outputs/export_image_first_full
```

## Verify Export

```bash
python scripts/test_export_sanity.py \
  --config configs/image_first.yaml \
  --checkpoint outputs/checkpoints_image_first/best.pt \
  --tflite outputs/export_image_first_full/model.tflite \
  --image ../datasets/lol/val/low/1.png
```

## Notes

- `eval_preview.py` should be used for visual inspection; loss alone is not enough.
- The baseline export is a float path, not an INT8/QAT MCU-ready runtime.
- Firmware integration should start with a bypass hook and non-AI baseline before neural inference.
