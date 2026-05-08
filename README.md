# llie-stm32

Low-light enhancement research workspace for `STM32H750VBT6`.

Target pipeline:

```text
camera -> lightweight enhancement -> LCD
```

The project explores a deployable path for microcontrollers: a tiny student model predicts global enhancement controls, while firmware applies fast gain/gamma style rendering.

## What Is Included

- Training and export code in `workspace/`
- One technical plan in `docs/PLAN.md`
- One project report in `reports/REPORT.md`
- Datasets in `datasets/` through Git LFS
- STM32H750 firmware base in `firmware/08-DCMI2LCD/`

The repo includes the selected baseline outputs needed for review and board bring-up:

- `workspace/outputs/checkpoints_image_first/`
- `workspace/outputs/previews_image_first/`
- `workspace/outputs/export_image_first_full/`

Not tracked:

- `.venv/`
- optional cloned reference repos under `repos/`

## Quick Start

```bash
git clone git@github.com:NgThachThanh/llie-stm32.git
cd llie-stm32

python3 -m venv .venv
source .venv/bin/activate
pip install torch torchvision numpy scipy pyyaml opencv-python-headless

python -m compileall workspace/scripts workspace/src
```

If dataset files are missing after clone:

```bash
git lfs pull
```

## Repository Layout

```text
docs/        technical notes and firmware plan
firmware/    STM32H750 firmware example prepared for board testing
reports/     project reports
papers/      reference paper
datasets/    LOL / LOL-v2 datasets tracked with Git LFS
repos/       optional local reference/vendor repos, ignored
workspace/   training, evaluation, and export code
```

## Data Layout

Place paired low-light datasets under:

```text
datasets/lol/
  train/low/
  train/high/
  val/low/
  val/high/
```

Teacher targets and pseudo-controls, when generated, live beside the dataset:

```text
datasets/lol/train/teacher_y/
datasets/lol/train/pseudo_ctrl_v2/
```

Other included datasets:

```text
datasets/lol_v2_real/
datasets/lol_v2_synthetic/
```

## Current Baseline

- Model: `Student-G`
- Config: `workspace/configs/image_first.yaml`
- Checkpoint: `workspace/outputs/checkpoints_image_first/best.pt`
- Export artifacts: `workspace/outputs/export_image_first_full/`

## Train / Preview / Export

Run from `workspace/`.

Train:

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

Preview:

```bash
python scripts/eval_preview.py \
  --config configs/image_first.yaml \
  --checkpoint outputs/checkpoints_image_first/best.pt \
  --low-dir ../datasets/lol/val/low \
  --high-dir ../datasets/lol/val/high \
  --teacher-dir ../datasets/lol/val/teacher_y \
  --output-dir outputs/previews_image_first
```

Export:

```bash
python scripts/export_tflite.py \
  --config configs/image_first.yaml \
  --checkpoint outputs/checkpoints_image_first/best.pt \
  --output-dir outputs/export_image_first_full
```

## Next Engineering Work

1. Verify raw `camera -> LCD` on the target board.
2. Add a firmware bypass/process hook.
3. Build and measure a non-AI baseline.
4. Integrate `Student-G` only after the board path is stable.
