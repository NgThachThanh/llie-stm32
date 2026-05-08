# STM32 `08-DCMI2LCD` Integration Checklist

> **For Hermes:** treat this as the next execution handoff for the firmware side of the LLIE project.

**Goal:** turn the inspected WeAct `08-DCMI2LCD` example into a safe camera -> process -> LCD staging path that can first run bypass/classical enhancement, then later host the tiny LLIE model.

**Architecture:** keep all heavy work out of the DCMI interrupt path. Capture continues through DCMI DMA, the frame callback only marks readiness, and the main loop owns processing plus LCD blit. Start with a bypass/classical-enhancement pipeline before attempting neural inference.

**Tech stack:** STM32H750VBT6, WeAct MiniSTM32H7xx HAL example `08-DCMI2LCD`, DCMI + DMA, ST7735 LCD, RGB565 frame path, offline export artifacts `model.tflite` and `model_tflite.c/.h`.

---

## 1. Facts already verified in source

Firmware source of record:
- `repos/hardware/MiniSTM32H7xx/SDK/HAL/STM32H750/08-DCMI2LCD/Src/main.c`
- `repos/hardware/MiniSTM32H7xx/SDK/HAL/STM32H750/08-DCMI2LCD/Src/dcmi.c`
- `repos/hardware/MiniSTM32H7xx/SDK/HAL/STM32H750/08-DCMI2LCD/Src/stm32h7xx_it.c`
- `repos/hardware/MiniSTM32H7xx/SDK/HAL/STM32H750/08-DCMI2LCD/Drivers/BSP/Camera/camera.c`

Key hook points confirmed:
- frame buffer declaration: `main.c:68` -> `uint16_t pic[FrameWidth][FrameHeight];`
- ready flag: `main.c:69` -> `uint32_t DCMI_FrameIsReady;`
- FPS counter shared with main loop: `main.c:70` -> `uint32_t Camera_FPS = 0;`
- capture start: `main.c:218` -> `HAL_DCMI_Start_DMA(..., (uint32_t)&pic, ...)`
- main-loop consumer: `main.c:229-236` -> `if (DCMI_FrameIsReady) { ... ST7735_FillRGBRect(...) }`
- TFT96 display crop: `main.c:234` -> LCD push uses `&pic[20][0]` with height `80`, not the whole capture buffer
- callback role: `main.c:307-320` -> `HAL_DCMI_FrameEventCallback(...)` only updates FPS counters and sets `DCMI_FrameIsReady = 1`
- IRQ path: `stm32h7xx_it.c:224` -> `HAL_DCMI_IRQHandler(&hdcmi);`
- DMA mode: `dcmi.c:138` -> `hdma_dcmi.Init.Mode = DMA_CIRCULAR;`
- cache-related context: `main.c:111-123` configures AXI SRAM as cacheable write-back
- camera bring-up is board/sensor-dependent through `Camera_Init_Device(...)` in `main.c:197-199` and `camera.c`

Conclusion already locked in:
- **Do processing in the main loop branch before `ST7735_FillRGBRect(...)`.**
- **Do not put LLIE work inside `HAL_DCMI_FrameEventCallback()` or IRQ context.**

---

## 2. Feasibility / budget checklist before code changes

### Throughput budget
- [ ] Treat the current path as `camera DMA -> frame-ready flag -> blocking LCD write`.
- [ ] Assume LCD transfer is already a major bottleneck; do not add expensive full-frame copies blindly.
- [ ] First demo target should prioritize stable responsiveness over maximum enhancement quality.
- [ ] Measure four modes on board later: raw, bypass, classical baseline, tiny AI.

### Memory budget
- [ ] Inventory RAM used by the current full RGB565 frame buffer.
- [ ] Treat the current single `pic` buffer under `DMA_CIRCULAR` as a known hazard, not a safe default.
- [ ] Decide whether to upgrade immediately to double-buffering or to freeze capture around CPU ownership transitions for the first patch.
- [ ] Reserve room for any extra luma scratch buffer, resized `96x96` model input, and inference arena if neural path is attempted.
- [ ] Avoid storing multiple full RGB intermediate tensors.

### Dataflow choice
- [ ] Prefer Y/luma-centric preprocessing.
- [ ] Keep the display path in RGB565 as long as possible.
- [ ] If model input is needed, derive a small grayscale/luma view rather than a full RGB888 tensor.
- [ ] Do not start with full-frame RGB image-to-image inference.

### What not to do first
- [ ] Do not move heavy math into the DCMI callback.
- [ ] Do not jump directly to `model.tflite` integration before a bypass path exists.
- [ ] Do not assume DMA buffers are cache-safe without explicit coherency handling.
- [ ] Do not assume single-buffer circular DMA is acceptable just because the stock demo displays something.
- [ ] Do not treat export success alone as proof of deploy readiness.

### Smallest practical operating point
- [ ] Phase 1: identity/bypass processing in the main loop.
- [ ] Phase 2: classical enhancement only: gain + gamma LUT + optional adaptive gamma + EMA.
- [ ] Phase 3: tiny neural path using reduced luma input only after Phase 2 is stable.

---

## 3. Execution checklist

### Task 1: Freeze the integration target

**Objective:** ensure the exact firmware example and offline artifacts are the ones all later changes reference.

**Files:**
- Inspect: `repos/hardware/MiniSTM32H7xx/SDK/HAL/STM32H750/08-DCMI2LCD/Src/main.c`
- Inspect: `repos/hardware/MiniSTM32H7xx/SDK/HAL/STM32H750/08-DCMI2LCD/Src/dcmi.c`
- Inspect: `workspace/outputs/export_image_first_full/model.tflite`
- Inspect: `workspace/outputs/export_image_first_full/model_tflite.c`
- Inspect: `workspace/outputs/export_image_first_full/model_tflite.h`
- Inspect: `workspace/outputs/export_image_first_full/sanity_metrics.yaml`

**Checklist:**
- [ ] Confirm `08-DCMI2LCD` is still the chosen base example.
- [ ] Confirm exported artifacts still exist and match the canonical run.
- [ ] Confirm `sanity_metrics.yaml` is the handoff record for PyTorch vs TFLite parity.
- [ ] Record which camera sensor path the actual board is using and freeze that assumption in notes before preprocessing decisions.

**Verification:**
- `STATUS.md` and the export directory still point to the same canonical artifacts.

### Task 2: Add a processing boundary on paper before touching code

**Objective:** define the stable software seam that all future enhancement modes share.

**Target seam:**
```c
if (DCMI_FrameIsReady) {
    DCMI_FrameIsReady = 0;
    process_frame(active_capture_buf, display_buf);
    lcd_push_frame(display_buf);
}
```

**Checklist:**
- [ ] Name the roles explicitly: capture buffer, processing source, display destination.
- [ ] Preserve the existing crop/orientation semantics when abstracting the seam, especially the TFT96 path that displays `&pic[20][0]` for 80 rows.
- [ ] Do not treat `display_buf == capture_buf` as safe until the ownership/cache policy is explicit.
- [ ] Define one processing API that supports three modes:
  - `identity`
  - `classical_baseline`
  - `tiny_ai_controls`
- [ ] Keep the callback contract unchanged: callback only marks frame readiness.
- [ ] Mark IRQ-shared state (`DCMI_FrameIsReady`, `Camera_FPS`, and any successors) with an explicit volatile/synchronization policy.

**Verification:**
- A future patch plan can point to a single seam in `main.c` without ambiguity.

### Task 3: Lock down buffer ownership and cache policy

**Objective:** prevent the most likely MCU-side corruption bugs before adding enhancement logic.

**Checklist:**
- [ ] Start from the assumption that the existing single `pic` buffer is *not* robust enough for a trustworthy enhancement pipeline.
- [ ] Choose one of these before enhancement work:
  - double-buffer capture and process/display the non-DMA-owned buffer, or
  - explicit stop/capture ownership handoff for a simpler first experiment.
- [ ] Document when DMA owns the capture buffer and when CPU processing is allowed to read/write it.
- [ ] Place DMA-visible frame buffers in a named memory region with documented alignment suitable for cache-line-safe maintenance.
- [ ] Add a concrete D-cache coherency checklist for DMA-visible buffers.
- [ ] Verify whether cache maintenance needs to happen before CPU reads, before DMA writes, or both, depending on final placement.
- [ ] Include frame-drop / overwrite behavior in the ownership note: what happens if a new frame arrives while LCD transfer or processing is still running?

**Verification:**
- A later implementation patch must name the exact ownership transition points instead of relying on intuition.

### Task 4: Ship a bypass mode first

**Objective:** prove that inserting a processing stage does not break `camera -> LCD` behavior.

**Files to modify later:**
- `repos/hardware/MiniSTM32H7xx/SDK/HAL/STM32H750/08-DCMI2LCD/Src/main.c`
- optionally a new helper pair such as:
  - `.../Src/llie_pipeline.c`
  - `.../Inc/llie_pipeline.h`

**Checklist:**
- [ ] Insert a call site before `ST7735_FillRGBRect(...)`.
- [ ] Start with pure identity/bypass.
- [ ] Keep a compile-time switch or enum mode so raw vs bypass can be compared easily.
- [ ] Do not mix baseline logic and AI logic into the first patch.

**Verification on board:**
- [ ] firmware still captures and displays frames
- [ ] no obvious tearing/corruption regression beyond current baseline
- [ ] raw mode and bypass mode both run

### Task 5: Add the strong non-AI baseline

**Objective:** create a cheap, useful enhancement path that also becomes fallback if AI is too slow.

**Baseline contents:**
- global gain
- gamma LUT
- optional black lift
- adaptive gamma from mean luma
- temporal EMA on control values

**Checklist:**
- [ ] Keep the math luma-centric and lightweight.
- [ ] Prefer LUT/fixed-point implementation over expensive per-pixel floating point.
- [ ] Separate control estimation from pixel application.
- [ ] Keep the output format compatible with the existing RGB565 LCD path.

**Verification on board:**
- [ ] visible improvement versus raw feed in dim scenes
- [ ] latency/FPS remain acceptable for demo use
- [ ] baseline can be toggled off for A/B comparison

### Task 6: Define the tiny AI ingress/egress path

**Objective:** constrain neural integration to the smallest data path that fits the project goal.

**Offline artifacts available:**
- `workspace/outputs/export_image_first_full/model.tflite`
- `workspace/outputs/export_image_first_full/model_tflite.c`
- `workspace/outputs/export_image_first_full/model_tflite.h`

**Current known tensor contract:**
- input shape: `[1, 96, 96, 1]`
- output shape: `[1, 3]`

**Checklist:**
- [ ] Define exactly how the firmware produces the `96x96x1` input from the frame.
- [ ] Define what the 3 outputs mean in firmware terms before wiring inference in.
- [ ] Decide whether to consume `model.tflite` through a runtime or link the C array directly.
- [ ] Verify the exported model operator/runtime compatibility for the intended STM32 inference stack; shapes alone are not enough.
- [ ] Budget memory for model weights plus runtime scratch/arena.
- [ ] Keep the first AI demo to control prediction, not full-frame neural rendering.

**Verification:**
- A future implementation note can explain input preprocessing, output interpretation, and runtime choice in one page.

### Task 7: Prepare the measurement matrix

**Objective:** make board testing decisive instead of anecdotal.

**Measure these modes separately:**
- [ ] raw camera -> LCD
- [ ] bypass process -> LCD
- [ ] classical baseline -> LCD
- [ ] tiny AI control path -> LCD

**Record for each mode:**
- [ ] FPS
- [ ] end-to-end latency
- [ ] processing time only
- [ ] LCD transfer time if separable
- [ ] RAM headroom / arena usage if AI path is enabled
- [ ] frame-drop / overwrite behavior under load
- [ ] visual notes: noise, banding, flicker, tearing, color shifts

**Verification:**
- results are written back into `STATUS.md` or a dedicated measurement note after the first board session.

---

## 4. First implementation order to follow

1. `camera -> LCD` board sanity using the stock example
2. lock buffer ownership + DMA-safe cache policy
3. main-loop processing seam with identity/bypass only
4. classical baseline enhancement
5. measurement pass
6. tiny AI control-path integration
7. second measurement pass
8. only then decide whether INT8/QAT/runtime changes are worth it

---

## 5. Done criteria for this checklist

This checklist has done its job when:
- the firmware patch point is unambiguous
- buffer/cache risks are named before implementation
- the first embedded demo order is fixed
- AI integration is constrained to a reduced luma/control path
- later board work can proceed without re-discovering the same architectural decisions

---

## 6. Immediate next practical task

When resuming firmware work, the first concrete patch should be:
- add an explicit processing seam in `08-DCMI2LCD/Src/main.c`
- keep mode = identity/bypass
- verify the stock display path still works

Only after that should the project add classical enhancement or neural inference.