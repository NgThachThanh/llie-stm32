# TODO — STM32H750 Low-Light Enhancement

## High priority — clean current state and prepare real integration
- [x] Promote canonical offline run: `configs/image_first.yaml` with `loss.param = 0.02`
- [x] Verify export artifacts exist for canonical winner
- [x] Verify PyTorch vs TFLite sanity on canonical export
- [x] Make `workspace/scripts/train_float.py` persist structured run logs automatically (`train_log.csv`, `metrics.yaml`)
- [x] Decide canonical location/format for export sanity metadata per run
- [x] Write STM32 integration checklist for `08-DCMI2LCD` (`docs/stm32-08-dcmi2lcd-integration-checklist.md`)
- [ ] Define first embedded demo strategy:
  - classical lightweight baseline first, or
  - tiny ROI neural LLIE first

## Medium priority — deployment hardening
- [ ] Harden float export handoff for firmware consumption
- [ ] Define exact path from `model.tflite` and `model_tflite.c/.h` into STM32 project
- [ ] Evaluate whether INT8/QAT is actually required for STM32H750 budget
- [ ] If needed, implement proper INT8 / QAT export path
- [ ] Add deploy-readiness checklist beyond format conversion

## Firmware path — still pending on board side
- [ ] Validate raw `camera -> LCD` path on STM32H750 example firmware
- [ ] Add processing hook / bypass path in `08-DCMI2LCD`
- [ ] Implement strong non-AI baseline on MCU: gain + gamma LUT + adaptive gamma + temporal EMA
- [ ] Measure baseline FPS / latency / RAM on board
- [ ] Integrate trained Student-G into firmware path
- [ ] Verify on-device correctness and visual quality

## Rebuild / rerun only if needed
- [ ] Regenerate teacher targets from scratch if dataset pipeline is rebuilt
- [ ] Refit pseudo-controls if teacher outputs or config change
- [ ] Rerun canonical training if loss weights / architecture change
- [ ] Refresh previews if canonical checkpoint changes

## Housekeeping
- [x] Add root `.gitignore` coverage for generated outputs and temp teacher dirs
- [ ] Keep dataset temp artifacts like `teacher_y__tmp*` ignored / cleaned when they appear
- [ ] Keep status docs aligned with surviving artifacts, not memory
