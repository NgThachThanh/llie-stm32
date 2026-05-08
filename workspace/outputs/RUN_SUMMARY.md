# LLIE workspace run summary

## Current canonical winner
- Config: `configs/image_first.yaml`
- Winner setting: `loss.param = 0.02`
- Canonical checkpoints: `outputs/checkpoints_image_first/`
- Canonical previews: `outputs/previews_image_first/`

## Compared runs
- `outputs/checkpoints_image_first_param0/` -> test run with `param=0.0`
- `outputs/checkpoints_image_first_param002/` -> winner run with `param=0.02`
- historical comparisons remain under `outputs/comparisons/`

## Decision note
- `param=0.05` looked slightly better than `0.0` visually.
- `param=0.02` matched `0.05` visually on sampled previews while achieving lower training loss.
- Baseline was therefore promoted from `0.05` to `0.02`.

## Export / deployment status
- `scripts/export_tflite.py` is active and has produced real export artifacts for the current canonical winner.
- Canonical export directory:
  - `outputs/export_image_first_full/`
- Verified artifacts present:
  - `model.ts`
  - `model.onnx`
  - `model.tflite`
  - `model_tflite.c`
  - `model_tflite.h`
  - `export_manifest.yaml`
- Manifest currently points to:
  - config: `configs/image_first.yaml`
  - checkpoint: `outputs/checkpoints_image_first/best.pt`

## Sanity check status
- Reusable checker script:
  - `scripts/test_export_sanity.py`
- Latest verified result:
  - image: `datasets/lol/val/low/1.png`
  - TFLite input shape: `[1, 96, 96, 1]`
  - TFLite output shape: `[1, 3]`
  - `max_abs_diff = 1.9073486328125e-06`
  - `mean_abs_diff = 1.112619997911679e-06`
- Conclusion:
  - PyTorch and TFLite outputs match at float-rounding level only.
  - Current TFLite artifact is trustworthy for downstream STM32 integration work.
  - However, this is still a float export path, not yet an INT8/QAT deploy-ready STM32 path.

## Integration status
- STM32 side target remains:
  - `WeActStudio MiniSTM32H7xx / STM32H750VBT6`
  - example path: `repos/hardware/MiniSTM32H7xx/SDK/HAL/STM32H750/08-DCMI2LCD/`
- Current best insertion point for LLIE stage:
  - in `main.c`, inside `if (DCMI_FrameIsReady)` and before `ST7735_FillRGBRect(...)`
- Main technical blockers before firmware integration:
  - D-cache coherency for DMA frame buffer
  - single-buffer ownership hazard during continuous capture
  - RGB565 -> model input conversion strategy
  - latency budget for first embedded demo
