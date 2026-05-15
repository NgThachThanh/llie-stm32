# CubeIDE minimal overlay for STM32H750 camera LCD

Use this with a fresh STM32CubeMX-generated STM32CubeIDE project.

## One path

1. In STM32CubeMX, open `firmware/h750-cam-lcd-min/08-DCMI2LCD.ioc`.
2. Set `Toolchain / IDE = STM32CubeIDE`.
3. Generate a new project, for example `C:\STM32\h750_cam_lcd_min_cubeide`.
4. From PowerShell at repo root, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\apply_cubeide_minimal.ps1 -ProjectPath "C:\STM32\h750_cam_lcd_min_cubeide"
```

5. Open/import that project in STM32CubeIDE and build.

## What the overlay does

- Replaces `Core/Src/main.c` with the minimal camera-to-LCD app.
- Adds only `OV5640` camera files.
- Adds `st7735_min.c/.h` only.
- Removes original LCD driver/text/logo files and unused camera sensor files.

## Runtime behavior

Power/reset -> raw OV5640 camera appears on the 0.96 inch ST7735 LCD immediately.
No menu, logo, text, SD, model, or button mode yet.
