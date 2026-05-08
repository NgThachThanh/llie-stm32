# Project Report

## Title

Low-light enhancement pipeline for near real-time display on `STM32H750VBT6`.

## Motivation

Low-light camera feeds are dark, noisy, and hard to inspect directly. Desktop low-light enhancement models are too heavy for a small MCU, so this project focuses on a practical embedded pipeline rather than a large image-to-image network.

## Hardware Target

- Board: WeAct MiniSTM32H7xx / `STM32H750VBT6`
- Camera path: DCMI
- Display: ST7735 LCD
- Firmware base: `firmware/08-DCMI2LCD/`

## System Direction

Target path:

```text
camera -> luma/control estimation -> fast enhancement -> LCD
```

The selected direction is system-centric:

- keep frame resolution modest
- avoid full RGB image-to-image CNN on MCU
- use lightweight luma preprocessing
- use tiny model output as control values
- keep a no-AI baseline as fallback

## Current AI Baseline

- Model family: `Student-G`
- Current model type: `student_global_only`
- Input: `96x96` luma
- Output: 3 global controls
- Canonical config: `workspace/configs/image_first.yaml`
- Checkpoint: `workspace/outputs/checkpoints_image_first/best.pt`
- Preview output: `workspace/outputs/previews_image_first/`
- Export output: `workspace/outputs/export_image_first_full/`

Export sanity:

- TFLite input shape: `[1, 96, 96, 1]`
- TFLite output shape: `[1, 3]`
- max absolute diff vs PyTorch: `1.9073486328125e-06`
- mean absolute diff vs PyTorch: `1.112619997911679e-06`

## Training Milestones

### Smoke Run

Goal: prove teacher target generation, pseudo-control fitting, training, and preview all run end-to-end.

Result:

- teacher generation passed
- pseudo-control generation passed
- Student-G trained
- preview generation passed
- output improved over low-light input but was still under-enhanced

Conclusion:

- smoke milestone passed
- quality milestone was not final

### Image-First Run

Goal: reduce under-enhancement by weighting image target more strongly.

Changes:

- increased `ssim`
- increased `exposure`
- reduced `param` supervision pressure

Result:

- output became visibly brighter and more useful
- no severe over-bright artifact observed in preview
- this run became the selected old/canonical baseline

### Brightness Test

A later high-target experiment was trained to make output closer to `high` images. Quantitatively it was brighter, but the user preferred the older teacher-target visual result. High-bright experiments were removed and should not be treated as canonical.

## Firmware Findings

Important facts from `08-DCMI2LCD`:

- DCMI DMA fills an RGB565 frame buffer.
- DCMI callback should only mark frame readiness.
- LCD write path is blocking and likely a major bottleneck.
- Current stock path uses a single capture/display buffer, which is risky for processing.
- The enhancement hook should be in the main loop before LCD blit.

Main firmware risks:

- DMA/cache coherency
- tearing from single-buffer circular DMA
- LCD transfer cost
- RGB565/luma preprocessing mismatch
- runtime memory for any AI inference stack

## Recommended Board Work

1. Flash and verify raw `camera -> LCD`.
2. Add identity/bypass processing hook.
3. Define buffer ownership and D-cache policy.
4. Add no-AI baseline with gain/gamma LUT.
5. Measure FPS and latency for raw, bypass, baseline.
6. Integrate Student-G only after baseline is stable.

## Current Status

Ready for collaborator board testing:

- firmware base included
- old canonical checkpoint included
- preview outputs included
- export artifacts included
- datasets included through Git LFS

The next critical work is hardware validation, not more offline training.
