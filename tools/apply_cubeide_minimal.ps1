param(
  [Parameter(Mandatory=$true)]
  [string]$ProjectPath
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$overlay = Join-Path $repoRoot "firmware/cubeide-h750-cam-lcd-min"
$project = Resolve-Path $ProjectPath

if (!(Test-Path (Join-Path $project ".project")) -or !(Test-Path (Join-Path $project ".cproject"))) {
  throw "ProjectPath must point to a generated STM32CubeIDE project containing .project and .cproject"
}

$dirs = @(
  "Core/Src",
  "Drivers/BSP/Camera",
  "Drivers/BSP/ST7735"
)
foreach ($dir in $dirs) {
  New-Item -ItemType Directory -Force -Path (Join-Path $project $dir) | Out-Null
}

Copy-Item -Force (Join-Path $overlay "Core/Src/main.c") (Join-Path $project "Core/Src/main.c")
Copy-Item -Force (Join-Path $overlay "Drivers/BSP/Camera/*") (Join-Path $project "Drivers/BSP/Camera/")
Copy-Item -Force (Join-Path $overlay "Drivers/BSP/ST7735/*") (Join-Path $project "Drivers/BSP/ST7735/")

$remove = @(
  "Drivers/BSP/ST7735/lcd.c",
  "Drivers/BSP/ST7735/lcd.h",
  "Drivers/BSP/ST7735/st7735.c",
  "Drivers/BSP/ST7735/st7735.h",
  "Drivers/BSP/ST7735/st7735_reg.c",
  "Drivers/BSP/ST7735/st7735_reg.h",
  "Drivers/BSP/ST7735/font.h",
  "Drivers/BSP/ST7735/logo.c",
  "Drivers/BSP/ST7735/logo_128_160.c",
  "Drivers/BSP/ST7735/logo_160_80.c",
  "Drivers/BSP/Camera/ov7670.c",
  "Drivers/BSP/Camera/ov7670.h",
  "Drivers/BSP/Camera/ov7670_regs.c",
  "Drivers/BSP/Camera/ov7670_regs.h",
  "Drivers/BSP/Camera/ov2640.c",
  "Drivers/BSP/Camera/ov2640.h",
  "Drivers/BSP/Camera/ov2640_regs.c",
  "Drivers/BSP/Camera/ov2640_regs.h",
  "Drivers/BSP/Camera/ov7725.c",
  "Drivers/BSP/Camera/ov7725.h",
  "Drivers/BSP/Camera/ov7725_regs.c",
  "Drivers/BSP/Camera/ov7725_regs.h"
)
foreach ($item in $remove) {
  $path = Join-Path $project $item
  if (Test-Path $path) { Remove-Item -Force $path }
}

Write-Host "Applied minimal H750 camera LCD overlay to $project"
Write-Host "Now open/import this project in STM32CubeIDE and build."
