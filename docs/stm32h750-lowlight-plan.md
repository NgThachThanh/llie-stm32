# STM32H750 Low-Light Enhancement Plan

> For Hermes: this is a hardware-aware project plan for a realtime-ish camera -> enhance -> LCD pipeline on WeAct MiniSTM32H7xx (STM32H750VBT6).

## Goal
Build a practical low-light enhancement pipeline that continuously captures from camera, improves visibility in low light, and displays on the onboard LCD with stable perceived realtime behavior. Success is defined by practicality on hardware, not by SOTA PSNR.

## Chosen direction
Use a hybrid pipeline:
1. sensor-side downscale/exposure tuning on OV5640
2. luma-centric preprocessing on MCU
3. tiny AI model predicts enhancement parameters / coarse illumination guidance
4. fixed-function fast enhancement applies to frame
5. display to ST7735 LCD

Do NOT use a full RGB image-to-image CNN as the primary plan.

## Why this direction
- Internal flash is small; RAM is precious.
- Existing example uses continuous DCMI DMA and blocking SPI LCD writes.
- LCD bandwidth alone strongly favors 160x120 or 128x160.
- Activation memory, not just parameter count, is the main MCU bottleneck.

## Repo facts checked
- Board README: STM32H750VBT6, 1MB RAM, 8MB SPI flash, 8MB QSPI flash, ST7735 LCD, DCMI camera support.
- Camera/display example: SDK/HAL/STM32H750/08-DCMI2LCD
- Example main loop writes captured buffer directly to LCD.
- LCD path uses SPI4 1-line with HAL_SPI_Transmit blocking.
- IOC shows SYSCLK 240 MHz and SPI4 prescaler /8.

## Practical operating point
- Preferred sensor/display operating resolution: 160x120
- Secondary option: 128x160 if matching LCD layout matters more than throughput
- Avoid 320x240 for first practical version

## Theoretical display ceiling
- 160x120 RGB565 frame = 38,400 bytes; at 15 Mbit/s SPI theoretical LCD-only max ~48.8 fps
- 128x160 RGB565 frame = 40,960 bytes; theoretical LCD-only max ~45.8 fps
- 320x240 RGB565 frame = 153,600 bytes; theoretical LCD-only max ~12.2 fps

Real throughput will be lower due to CPU copies, LCD command overhead, enhancement, and synchronization.

## Recommended AI formulation
Best practical AI formulation:
- Input: luma Y only, not full RGB
- Output: either
  - global + blockwise tone mapping parameters, or
  - a coarse illumination/gain map, or
  - a tiny per-pixel curve parameter field at reduced resolution
- Enhancement application: fixed fast math / LUT on full-resolution luma

### Preferred model family
Primary: Zero-DCE++ / Self-DACE++ inspired curve-prediction student
Secondary: Multinex-nano / CPGA-Net-inspired teacher for distillation

### Concrete student model target
Version A (recommended):
- Input: 96x96 Y
- Network: depthwise-separable conv stack, channels 8-8-8
- Output: 12x12 or 16x16 coarse gain map + 1 global gamma + optional noise gate
- Runtime use: bilinear upsample gain map to 160x120 Y, apply LUT/gain, then recombine with chroma

Version B (backup if quality too low):
- Input: 96x96 Y
- Output: 96x96 enhanced Y residual or curve field
- Upsample to display size

Avoid full 160x120 RGB image-to-image output as the first model.

## Training strategy
### Teacher
Use a stronger offline enhancement target generator:
- Multinex-light or CPGA-Net/CPGA-Net+ style teacher
- or a curated non-embedded LLIE model on PC for pseudo-target generation

### Student
Train the tiny student to match teacher behavior in luma space.

### Data
- LOL / LOL-v2 for paired benchmarking
- Add unlabeled/night real camera captures from OV5640 if available
- Augment with exposure shifts, noise injection, blur, color casts, gain changes

### Losses
Core losses:
- L1 on enhanced luma vs teacher/pseudo target
- SSIM on luma
- exposure control loss
- TV / smoothness loss on coarse gain map
- temporal consistency loss on short frame pairs
- optional edge preservation loss

Optional deployment-aware losses:
- quantization-aware training loss
- monotonic curve regularization
- saturation clipping penalty

## Quantization / deployment strategy
- Quantization target: INT8
- Use QAT, not PTQ-only, if the chosen operators allow it
- Prefer ops that map cleanly to TFLM/CMSIS-NN style kernels
- Export to TFLite / TFLite Micro compatible form if feasible
- Convert final model to C array and link into firmware
- Keep backup path: hand-transcribe tiny model to pure C if TFLM overhead is too large

## Firmware architecture plan
1. Start from 08-DCMI2LCD example
2. Replace single shared capture buffer with double buffering
3. Handle D-cache coherency properly for DMA buffers
4. Keep capture in one buffer while processing the other
5. Convert input to Y (or capture Y-friendly format if possible)
6. Run preprocessing + tiny model on Y
7. Apply enhancement to Y
8. Recombine to RGB565 for LCD
9. Push to LCD line-by-line or tile-by-tile

## Memory strategy
- Double buffer capture at 160x120
- Separate luma workspace
- Tiny model activations kept under ~80-120 KiB target
- Avoid multiple full RGB intermediate tensors
- Prefer coarse maps and LUTs over dense full-frame feature tensors

## What not to do
- Do not start with full RGB image-to-image CNN
- Do not start at 320x240
- Do not capture high OV5640 resolution and resize in MCU
- Do not leave DMA buffers in cacheable memory without coherency handling
- Do not rely on single-buffer capture for continuous enhancement

## Milestones
1. Baseline camera -> LCD with double buffering and cache-safe capture
2. Non-AI baseline: Y-only gamma + denoise + local gain map
3. Tiny AI v1: predict global gamma + coarse gain map
4. QAT INT8 deployment
5. Temporal stabilization
6. Teacher-student upgrade
7. Final evaluation on low-light scenes

## Success criteria
- Continuous display feels responsive
- Low-light visibility clearly improved over raw feed
- No severe tearing or cache corruption artifacts
- FPS stable enough for demo use
- Better practicality than prior ESP32 paper: smoother pipeline, more robust deployment, and clearer improvement/latency tradeoff
