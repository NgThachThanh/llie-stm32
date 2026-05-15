# GCC STM32H750 camera LCD minimal project

This folder is self-contained for GNU Arm GCC. It does not use Keil and has no 32 KB Keil license limit.

## Build from PowerShell / terminal

```powershell
cd firmware\gcc-h750-cam-lcd-min
make
```

Expected outputs:

```text
build/h750_cam_lcd_min.elf
build/h750_cam_lcd_min.hex
build/h750_cam_lcd_min.bin
```

## Build in STM32CubeIDE

Use one path:

1. `File` -> `Import...`
2. `C/C++` -> `Existing Code as Makefile Project`
3. Existing Code Location: this folder
4. Toolchain: `MCU ARM GCC`
5. Finish
6. Right click project -> `Build Project`

## Flash

Use STM32CubeProgrammer and flash:

```text
build/h750_cam_lcd_min.hex
```

## Runtime

Power/reset -> OV5640 camera appears on 0.96 inch ST7735 LCD immediately.
No menu, logo, text, SD, model, or button mode.
