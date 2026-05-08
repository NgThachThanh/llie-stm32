# llie-stm32

Low-light enhancement project for `STM32H750VBT6`.

Goal:

```text
camera -> lightweight enhancement -> LCD
```

Main idea: keep MCU work simple and real-time. Use a tiny student model to predict control values, then let firmware apply fast gain/gamma style rendering.

## Status

- Canonical model: `Student-G`
- Canonical config: `workspace/configs/image_first.yaml`
- Canonical export metadata/C header: `workspace/outputs/export_image_first_full/`
- Firmware target to inspect: `repos/hardware/MiniSTM32H7xx/SDK/HAL/STM32H750/08-DCMI2LCD`

Large local assets are intentionally not tracked:

- `.venv/`
- `datasets/`
- `repos/`
- checkpoints, previews, model binaries

## Layout

```text
docs/        technical notes and firmware plan
reports/     project reports
papers/      reference paper
datasets/    local datasets, ignored except README
repos/       local reference/vendor repos, ignored
workspace/   training, evaluation, export code
```

## Read Next

```text
STATUS.md
TODO.md
workspace/README.md
docs/stm32-08-dcmi2lcd-integration-checklist.md
```

## Quick Check

```bash
cd /home/stonies/projects/llie-stm32
source .venv/bin/activate
python -m compileall workspace/scripts workspace/src
```

## Current Priority

1. Verify raw `camera -> LCD` on board.
2. Add firmware bypass/process hook.
3. Build non-AI baseline first.
4. Integrate Student-G only after board path is stable.
