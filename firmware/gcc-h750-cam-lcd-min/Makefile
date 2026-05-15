PROJECT := h750_cam_lcd_min
BUILD_DIR := build
PREFIX ?= arm-none-eabi-
CC := $(PREFIX)gcc
OBJCOPY := $(PREFIX)objcopy
SIZE := $(PREFIX)size

ifeq ($(OS),Windows_NT)
MKDIR_P = if not exist "$(subst /,\,$(1))" mkdir "$(subst /,\,$(1))"
RM_RF = if exist "$(subst /,\,$(1))" rmdir /s /q "$(subst /,\,$(1))"
else
MKDIR_P = mkdir -p $(1)
RM_RF = rm -rf $(1)
endif

C_DEFS := -DUSE_HAL_DRIVER -DSTM32H750xx -DTFT96
MCU := -mcpu=cortex-m7 -mthumb -mfpu=fpv5-d16 -mfloat-abi=hard
OPT := -Os -ffunction-sections -fdata-sections
WARN := -Wall -Wextra -Wno-unused-parameter -Wno-missing-field-initializers
SPECS := --specs=nano.specs --specs=nosys.specs

INCLUDES := \
  -IInc \
  -IDrivers/BSP/Camera \
  -IDrivers/BSP/ST7735 \
  -IDrivers/STM32H7xx_HAL_Driver/Inc \
  -IDrivers/STM32H7xx_HAL_Driver/Inc/Legacy \
  -IDrivers/CMSIS/Device/ST/STM32H7xx/Include \
  -IDrivers/CMSIS/Include

C_SOURCES := \
  Src/startup_stm32h750xx.c \
  Src/main.c \
  Src/system_stm32h7xx.c \
  Src/stm32h7xx_it.c \
  Src/stm32h7xx_hal_msp.c \
  Src/gpio.c \
  Src/dcmi.c \
  Src/dma.c \
  Src/i2c.c \
  Src/spi.c \
  Src/tim.c \
  Src/llie_pipeline.c \
  Src/llie_weights.c \
  Drivers/BSP/Camera/camera.c \
  Drivers/BSP/Camera/ov5640.c \
  Drivers/BSP/Camera/ov5640_regs.c \
  Drivers/BSP/ST7735/st7735_min.c \
  Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal.c \
  Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_cortex.c \
  Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_dcmi.c \
  Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_dma.c \
  Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_dma_ex.c \
  Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_flash.c \
  Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_flash_ex.c \
  Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_gpio.c \
  Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_i2c.c \
  Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_i2c_ex.c \
  Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_pwr.c \
  Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_pwr_ex.c \
  Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_rcc.c \
  Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_rcc_ex.c \
  Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_spi.c \
  Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_spi_ex.c \
  Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_tim.c \
  Drivers/STM32H7xx_HAL_Driver/Src/stm32h7xx_hal_tim_ex.c

OBJECTS := $(addprefix $(BUILD_DIR)/,$(C_SOURCES:.c=.o))
DEPS := $(OBJECTS:.o=.d)

CFLAGS := $(MCU) $(C_DEFS) $(INCLUDES) $(OPT) $(WARN) -std=gnu11 -MMD -MP
LDFLAGS := $(MCU) $(SPECS) -TSTM32H750VBTX_FLASH.ld -Wl,-Map=$(BUILD_DIR)/$(PROJECT).map,--cref -Wl,--gc-sections

all: $(BUILD_DIR)/$(PROJECT).elf $(BUILD_DIR)/$(PROJECT).hex $(BUILD_DIR)/$(PROJECT).bin
	$(SIZE) $(BUILD_DIR)/$(PROJECT).elf

$(BUILD_DIR)/$(PROJECT).elf: $(OBJECTS) STM32H750VBTX_FLASH.ld
	$(CC) $(OBJECTS) $(LDFLAGS) -o $@

$(BUILD_DIR)/%.o: %.c
	@$(call MKDIR_P,$(dir $@))
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/%.hex: $(BUILD_DIR)/%.elf
	$(OBJCOPY) -O ihex $< $@

$(BUILD_DIR)/%.bin: $(BUILD_DIR)/%.elf
	$(OBJCOPY) -O binary $< $@

clean:
	$(call RM_RF,$(BUILD_DIR))

.PHONY: all clean
-include $(DEPS)
