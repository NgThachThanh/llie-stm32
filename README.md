# llie-stm32

Low-light enhancement research workspace for `STM32H750VBT6`.

Target pipeline:

```text
camera -> lightweight enhancement -> LCD
```

The project explores a deployable path for microcontrollers: a tiny student model predicts global enhancement controls, while firmware applies fast gain/gamma style rendering.

## What Is Included

- Training and export code in `workspace/`
- Technical notes in `docs/`
- Project reports in `reports/`
- Dataset folder skeleton in `datasets/`
- Firmware integration checklist for STM32H750 DCMI/LCD flow

Large local assets are not tracked: virtual environments, datasets, cloned reference repos, checkpoints, previews, and model binaries.

## Quick Start

```bash
git clone git@github.com:NgThachThanh/llie-stm32.git
cd llie-stm32

python3 -m venv .venv
source .venv/bin/activate
pip install torch torchvision numpy scipy pyyaml opencv-python-headless

python -m compileall workspace/scripts workspace/src
```

## Repository Layout

```text
docs/        technical notes and firmware plan
reports/     project reports
papers/      reference paper
datasets/    local datasets, ignored except README
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

## Current Baseline

- Model: `Student-G`
- Config: `workspace/configs/image_first.yaml`
- Export metadata and generated C array: `workspace/outputs/export_image_first_full/`

See `workspace/README.md` for train, preview, and export commands.

## Next Engineering Work

1. Verify raw `camera -> LCD` on the target board.
2. Add a firmware bypass/process hook.
3. Build and measure a non-AI baseline.
4. Integrate `Student-G` only after the board path is stable.
