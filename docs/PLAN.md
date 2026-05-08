# Project Plan

## Goal

Build a practical low-light enhancement path for `STM32H750VBT6`:

```text
camera -> lightweight enhancement -> LCD
```

The target is a stable board demo, not a SOTA image restoration benchmark.

## Current Direction

- Use `08-DCMI2LCD` as the firmware base.
- Keep enhancement luma-centric.
- Use a tiny `Student-G` model to predict global controls.
- Apply enhancement in firmware with fast gain/gamma style rendering.
- Keep non-AI baseline as fallback.

## Current Baseline

- Model: `student_global_only`
- Config: `workspace/configs/image_first.yaml`
- Checkpoint: `workspace/outputs/checkpoints_image_first/best.pt`
- Preview: `workspace/outputs/previews_image_first/`
- Export: `workspace/outputs/export_image_first_full/`
- Firmware base: `firmware/08-DCMI2LCD/`

## Dataset

Included local dataset layout:

```text
datasets/lol/
  train/low/
  train/high/
  val/low/
  val/high/

datasets/lol_v2_real/
datasets/lol_v2_synthetic/
```

Useful counts:

- `lol`: 486 train pairs, 15 val pairs
- `lol_v2_real`: 689 train pairs, 100 val pairs
- `lol_v2_synthetic`: 900 train pairs, 100 val pairs

## Training Flow

Run from `workspace/`:

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

## Firmware Plan

First board work should be conservative:

1. Confirm raw `camera -> LCD` works.
2. Add a bypass processing hook before LCD blit.
3. Fix buffer ownership and D-cache policy.
4. Add no-AI baseline: gain, gamma LUT, black lift, EMA.
5. Measure raw, bypass, baseline, and later AI modes separately.
6. Only then integrate `Student-G`.

Known hook from inspected firmware:

```text
firmware/08-DCMI2LCD/Src/main.c
```

Processing belongs in the main loop before `ST7735_FillRGBRect(...)`.
Do not put heavy work in DCMI callback or IRQ.

## Board Test Checklist

- Build and flash current `firmware/08-DCMI2LCD`.
- Verify camera sensor and LCD orientation.
- Record raw FPS.
- Add identity processing hook.
- Verify raw vs bypass output is visually identical.
- Add baseline enhancement and measure FPS again.
- Compare baseline to saved previews.
- Integrate AI only after baseline is stable.

## Risks

- Single-buffer circular DMA can tear while CPU/LCD reads.
- Cacheable AXI SRAM plus DMA can corrupt/stale frame data.
- Blocking LCD transfer may dominate frame time.
- Python preprocessing can drift from MCU RGB565/luma path.
- TFLite export parity is not the same as MCU runtime readiness.
