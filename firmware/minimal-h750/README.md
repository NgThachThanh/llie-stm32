# Minimal STM32H750 camera-to-LCD firmware

Branch: `firmware/minimal-h750`

## Goal

Power on the board and show OV5640 camera frames on the 0.96 inch ST7735 LCD immediately.

No menu, logo, text overlay, countdown, SD path, or multi-camera probing.

## Behavior

- Power on -> init clock/GPIO/DMA/DCMI/I2C/SPI/TIM/LCD/camera.
- Start DCMI DMA into RGB565 frame buffer.
- Draw each ready frame to LCD.
- `KEY` toggles enhancement mode.
- Default mode is raw camera.
- Enhancement mode currently uses a tiny RGB565 gain/lift baseline; model C inference can replace this later.

## Keil project

Open:

```text
firmware/minimal-h750/MDK-ARM/08-DCMI2LCD.uvprojx
```

Try target first:

```text
08-DCMI2LCD0_96_W25Qxx
```

Use ARM Compiler 6 if ARM Compiler 5 is unavailable.

## Kept from manufacturer code

- STM32H750 startup/system/clock/peripheral init.
- GPIO, DCMI, DMA, I2C1, SPI4, TIM init.
- OV5640 register path.
- ST7735 low-level LCD path.

## Removed

- OV7670 / OV2640 / OV7725 support.
- Logo bitmap files.
- Font and text rendering.
- `sprintf` / FPS overlay.
- Button wait/menu flow.
- LCD readback path.

## Test order

1. Build clean in Keil.
2. If `L6050U` appears, record new code size.
3. Flash board.
4. Verify camera appears immediately after power/reset.
5. Press `KEY`; image should switch raw/enhanced.
6. Record raw FPS visually if available from external measurement; firmware no longer prints FPS.
