# H750 camera LCD minimal firmware

This is the true rebuild path for the STM32H750 + OV5640 + 0.96 inch ST7735 demo.

## Goal

Fit under the Keil Lite 32 KB link limit while keeping the board-specific GPIO/peripheral init from the manufacturer project.

## Behavior

- Power/reset -> camera starts immediately.
- No logo, menu, countdown, text, FPS overlay, or SD path.
- Default display mode is raw camera.
- `KEY` toggles a tiny RGB565 gain/lift baseline placeholder.
- Later model C inference replaces the baseline hook.

## Keil project

Open:

```text
firmware/h750-cam-lcd-min/MDK-ARM/08-DCMI2LCD.uvprojx
```

Build target:

```text
08-DCMI2LCD0_96_W25Qxx
```

Use ARM Compiler 6 if ARM Compiler 5 is unavailable.

## What is kept

- Startup/system/clock from manufacturer firmware.
- GPIO, DCMI, DMA, I2C1, SPI4, TIM init from manufacturer firmware.
- OV5640 register table/path.
- HAL for required peripherals only.

## What is rebuilt

- LCD path uses `st7735_min.c` only:
  - init
  - set address window
  - fill rect
  - RGB565 blit
- No original `lcd.c`, `st7735.c`, `st7735_reg.c`, font, or logo.

## Test

1. Clean target in Keil.
2. Build `08-DCMI2LCD0_96_W25Qxx`.
3. If link still fails, report exact image size.
4. If build passes, flash and confirm camera appears on LCD immediately.
5. Press `KEY` to toggle raw/baseline.
