# Project Status — STM32H750 Low-Light Enhancement

## Current overall state
Project đã có **offline image-first path chạy end-to-end** cho vòng đầu tiên:
- teacher target generation đã dùng được
- pseudo-control fitting đã dùng được
- đã có training run thực tế và canonical winner
- đã có preview artifacts
- đã có TorchScript / ONNX / TFLite / `.c/.h`
- đã có sanity check PyTorch vs TFLite pass

Phần **firmware integration trên STM32H750** thì vẫn *chưa bắt đầu deploy thực chiến trên board*.

---

## Done offline
- project root organized
- report/proposal collected
- technical plan collected
- reference paper collected
- STM32H750 hardware repo collected
- teacher repo collected
- training workspace prepared
- Python/CUDA environment prepared
- datasets downloaded and rearranged
- teacher target generation path exercised
- pseudo-control fitting exercised
- first student training path exercised
- canonical previews generated
- float export path exercised
- TFLite export sanity verified

## Canonical current run
- Config: `workspace/configs/image_first.yaml`
- Winner setting: `loss.param = 0.02`
- Canonical checkpoint: `workspace/outputs/checkpoints_image_first/best.pt`
- Best checkpoint stats available from artifact:
  - epoch: `15`
  - loss: `0.1912352213116943`
- Last checkpoint stats available from artifact:
  - epoch: `20`
  - loss: `0.1914016606866336`
- Canonical previews: `workspace/outputs/previews_image_first/`
- Canonical export dir: `workspace/outputs/export_image_first_full/`

---

## Verified export state
Artifacts currently present:
- `model.ts`
- `model.onnx`
- `model.tflite`
- `model_tflite.c`
- `model_tflite.h`
- `export_manifest.yaml`

Sanity verification currently confirmed:
- script: `workspace/scripts/test_export_sanity.py`
- TFLite input shape: `[1, 96, 96, 1]`
- TFLite output shape: `[1, 3]`
- max abs diff: `1.9073486328125e-06`
- mean abs diff: `1.112619997911679e-06`

Meaning:
- export hiện khớp PyTorch ở mức float-rounding
- artifact TFLite hiện tại đáng tin cho bước tích hợp tiếp theo
- **nhưng đây vẫn là float export, chưa phải INT8/QAT deploy-ready path cho STM32**

---

## STM32 integration status
Target firmware side:
- Root project: `.`
- Training workspace: `workspace/`
- Teacher repo: `repos/Zero-DCE`
- STM32H750 repo: `repos/hardware/MiniSTM32H7xx`
- Example firmware path inspected separately: `08-DCMI2LCD`

Current integration understanding:
- best hook point for LLIE stage là trong `if (DCMI_FrameIsReady)` trước LCD blit
- STM32 integration checklist đã được viết tại `docs/stm32-08-dcmi2lcd-integration-checklist.md`
- main blockers trước khi cấy model:
  - D-cache coherency cho DMA frame buffer
  - single-buffer ownership hazard
  - RGB565 -> model input conversion strategy
  - latency/FPS budget trên board

---

## What is still not started
### Not started on embedded side
- firmware raw camera -> LCD timing validation on board
- bypass / identity processing path on firmware
- strong non-AI baseline on MCU
- FPS / latency / RAM measurement on board
- firmware integration with trained model
- on-device correctness validation
- INT8/QAT path nếu thật sự cần cho STM32 budget

### Not yet hardened enough on training/tooling side
- current canonical run still lacks original raw per-epoch historical log because that run predated structured logging
- canonical deploy checklist from exported TFLite/C array to STM32 firmware

---

## Current execution choice
Hiện tại narrative tổng vẫn là **system-first / firmware-first**.
Nhưng execution practical đang là:
- **AI-first offline** để khóa model/export trước
- sau đó quay lại firmware integration khi chạm board path

---

## Important caveats
- `workspace/scripts/export_tflite.py` **không còn là placeholder**; nó đã export artifact thật.
- Export hiện tại là **float model export**, chưa chứng minh được deploy-ready theo kiểu INT8/QAT hoặc chạy thật trên STM32 runtime.
- `workspace/scripts/train_float.py` now emits `train_log.csv` and `metrics.yaml` for future runs.
- The current canonical run still lacks original raw per-epoch history because it predated that logging change.
- Vì vậy chỉ nên khẳng định những gì được suy ra từ artifact còn sống; không được fabricate lịch sử training cũ.

---

## Success criteria for next milestone
Một milestone hợp lý tiếp theo là:
- training script tự sinh `train_log.csv` / `metrics.yaml`
- project docs không còn stale
- export sanity được lưu thành artifact metadata
- xác định rõ đường cấy `model.tflite` / `model_tflite.c/.h` vào firmware STM32
- có integration plan rõ cho `08-DCMI2LCD`
