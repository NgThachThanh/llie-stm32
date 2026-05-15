#include "main.h"
#include "dcmi.h"
#include "dma.h"
#include "i2c.h"
#include "spi.h"
#include "tim.h"
#include "gpio.h"

#include "camera.h"
#include "st7735_min.h"
#include "llie_pipeline.h"

#define FRAME_WIDTH   160U
#define FRAME_HEIGHT  120U

static uint16_t frame_buffer[FRAME_HEIGHT][FRAME_WIDTH] __attribute__((aligned(32)));
static volatile uint8_t frame_ready = 0;
static uint16_t fps_value = 0;

void SystemClock_Config(void);

static void MPU_Config(void)
{
  MPU_Region_InitTypeDef MPU_InitStruct = {0};

  HAL_MPU_Disable();

  MPU_InitStruct.Enable           = MPU_REGION_ENABLE;
  MPU_InitStruct.Number           = MPU_REGION_NUMBER0;
  MPU_InitStruct.BaseAddress      = QSPI_BASE;
  MPU_InitStruct.Size             = MPU_REGION_SIZE_256MB;
  MPU_InitStruct.AccessPermission = MPU_REGION_NO_ACCESS;
  MPU_InitStruct.IsBufferable     = MPU_ACCESS_NOT_BUFFERABLE;
  MPU_InitStruct.IsCacheable      = MPU_ACCESS_NOT_CACHEABLE;
  MPU_InitStruct.IsShareable      = MPU_ACCESS_NOT_SHAREABLE;
  MPU_InitStruct.DisableExec      = MPU_INSTRUCTION_ACCESS_DISABLE;
  MPU_InitStruct.TypeExtField     = MPU_TEX_LEVEL1;
  MPU_InitStruct.SubRegionDisable = 0x00;
  HAL_MPU_ConfigRegion(&MPU_InitStruct);

  MPU_InitStruct.Enable           = MPU_REGION_ENABLE;
  MPU_InitStruct.Number           = MPU_REGION_NUMBER1;
  MPU_InitStruct.BaseAddress      = QSPI_BASE;
  MPU_InitStruct.Size             = MPU_REGION_SIZE_8MB;
  MPU_InitStruct.AccessPermission = MPU_REGION_PRIV_RO;
  MPU_InitStruct.IsBufferable     = MPU_ACCESS_BUFFERABLE;
  MPU_InitStruct.IsCacheable      = MPU_ACCESS_CACHEABLE;
  MPU_InitStruct.IsShareable      = MPU_ACCESS_NOT_SHAREABLE;
  MPU_InitStruct.DisableExec      = MPU_INSTRUCTION_ACCESS_ENABLE;
  MPU_InitStruct.TypeExtField     = MPU_TEX_LEVEL1;
  MPU_InitStruct.SubRegionDisable = 0x00;
  HAL_MPU_ConfigRegion(&MPU_InitStruct);

  MPU_InitStruct.Enable           = MPU_REGION_ENABLE;
  MPU_InitStruct.Number           = MPU_REGION_NUMBER2;
  MPU_InitStruct.BaseAddress      = D1_AXISRAM_BASE;
  MPU_InitStruct.Size             = MPU_REGION_SIZE_512KB;
  MPU_InitStruct.AccessPermission = MPU_REGION_FULL_ACCESS;
  MPU_InitStruct.IsBufferable     = MPU_ACCESS_BUFFERABLE;
  MPU_InitStruct.IsCacheable      = MPU_ACCESS_CACHEABLE;
  MPU_InitStruct.IsShareable      = MPU_ACCESS_SHAREABLE;
  MPU_InitStruct.DisableExec      = MPU_INSTRUCTION_ACCESS_ENABLE;
  MPU_InitStruct.TypeExtField     = MPU_TEX_LEVEL1;
  MPU_InitStruct.SubRegionDisable = 0x00;
  HAL_MPU_ConfigRegion(&MPU_InitStruct);

  HAL_MPU_Enable(MPU_PRIVILEGED_DEFAULT);
}

static void CPU_CACHE_Enable(void)
{
  SCB_EnableICache();
  SCB_EnableDCache();
}

static uint16_t rgb565_wire(uint8_t r5, uint8_t g6, uint8_t b5)
{
  uint16_t p = (uint16_t)((r5 << 11) | (g6 << 5) | b5);
  return (uint16_t)((p << 8) | (p >> 8));
}

static const uint8_t glyphs_5x7[][5] = {
  /* 0-9 */
  {0x3EU,0x51U,0x49U,0x45U,0x3EU}, {0x00U,0x42U,0x7FU,0x40U,0x00U},
  {0x42U,0x61U,0x51U,0x49U,0x46U}, {0x21U,0x41U,0x45U,0x4BU,0x31U},
  {0x18U,0x14U,0x12U,0x7FU,0x10U}, {0x27U,0x45U,0x45U,0x45U,0x39U},
  {0x3CU,0x4AU,0x49U,0x49U,0x30U}, {0x01U,0x71U,0x09U,0x05U,0x03U},
  {0x36U,0x49U,0x49U,0x49U,0x36U}, {0x06U,0x49U,0x49U,0x29U,0x1EU},
  /* F, P, S */
  {0x7FU,0x09U,0x09U,0x09U,0x01U}, {0x7FU,0x09U,0x09U,0x09U,0x06U},
  {0x46U,0x49U,0x49U,0x49U,0x31U},
};

static const uint8_t *glyph_for(char c)
{
  if ((c >= '0') && (c <= '9')) return glyphs_5x7[c - '0'];
  if (c == 'F') return glyphs_5x7[10];
  if (c == 'P') return glyphs_5x7[11];
  if (c == 'S') return glyphs_5x7[12];
  return 0;
}

static void draw_char(uint16_t *dst, uint16_t stride, uint16_t x, uint16_t y, char c, uint16_t color)
{
  const uint8_t *g = glyph_for(c);
  if (g == 0) return;
  for (uint16_t col = 0; col < 5U; ++col)
  {
    for (uint16_t row = 0; row < 7U; ++row)
    {
      if ((g[col] >> row) & 1U)
      {
        dst[(y + row) * stride + x + col] = color;
      }
    }
  }
}

static void draw_fps_overlay(uint16_t *dst, uint16_t stride, uint16_t fps)
{
  const uint16_t black = rgb565_wire(0U, 0U, 0U);
  const uint16_t white = rgb565_wire(31U, 63U, 31U);
  char text[7] = {'F','P','S',' ', '0', '0', '\0'};

  if (fps > 99U) fps = 99U;
  text[4] = (char)('0' + (fps / 10U));
  text[5] = (char)('0' + (fps % 10U));

  for (uint16_t yy = 0; yy < 9U; ++yy)
  {
    for (uint16_t xx = 0; xx < 40U; ++xx)
    {
      dst[yy * stride + xx] = black;
    }
  }

  for (uint16_t i = 0; text[i] != '\0'; ++i)
  {
    draw_char(dst, stride, 1U + i * 6U, 1U, text[i], white);
  }
}

int main(void)
{
  MPU_Config();
  CPU_CACHE_Enable();
  HAL_Init();
  SystemClock_Config();

  MX_GPIO_Init();
  MX_DMA_Init();
  MX_DCMI_Init();
  MX_I2C1_Init();
  MX_SPI4_Init();
  MX_TIM1_Init();

  ST7735_MinInit();
  LLIE_Init();
  Camera_Init_Device(&hi2c1, FRAMESIZE_QQVGA);

  if (hcamera.device_id != 0x5640U)
  {
    Error_Handler();
  }

  if (HAL_DCMI_Start_DMA(&hdcmi, DCMI_MODE_CONTINUOUS, (uint32_t)&frame_buffer,
                         FRAME_WIDTH * FRAME_HEIGHT * sizeof(uint16_t) / sizeof(uint32_t)) != HAL_OK)
  {
    Error_Handler();
  }

  while (1)
  {
    static uint32_t fps_tick_start = 0U;
    static uint16_t fps_frames = 0U;
    static GPIO_PinState last_key = GPIO_PIN_RESET;
    GPIO_PinState key = HAL_GPIO_ReadPin(KEY_GPIO_Port, KEY_Pin);
    if ((key == GPIO_PIN_SET) && (last_key == GPIO_PIN_RESET))
    {
      LLIE_SetMode((LLIE_Mode)((LLIE_GetMode() + 1U) % 3U));
    }
    last_key = key;

    if (frame_ready)
    {
      frame_ready = 0;
      SCB_InvalidateDCache_by_Addr((void *)((uint32_t)&frame_buffer[0][0] & ~31U), sizeof(frame_buffer));
      LLIE_UpdateAIControls(&frame_buffer[0][0], FRAME_WIDTH, FRAME_HEIGHT);
      LLIE_ProcessFrame(&frame_buffer[20][0], ST7735_MIN_WIDTH * ST7735_MIN_HEIGHT);
      ++fps_frames;
      if (fps_tick_start == 0U)
      {
        fps_tick_start = HAL_GetTick();
      }
      else
      {
        uint32_t elapsed = HAL_GetTick() - fps_tick_start;
        if (elapsed >= 1000U)
        {
          fps_value = (uint16_t)(((uint32_t)fps_frames * 1000U) / elapsed);
          fps_frames = 0U;
          fps_tick_start = HAL_GetTick();
        }
      }
      draw_fps_overlay(&frame_buffer[20][0], ST7735_MIN_WIDTH, fps_value);
      ST7735_MinBlitRGB565(0, 0, (uint8_t *)&frame_buffer[20][0], ST7735_MIN_WIDTH, ST7735_MIN_HEIGHT);
    }
  }
}

void HAL_DCMI_FrameEventCallback(DCMI_HandleTypeDef *hdcmi)
{
  (void)hdcmi;
  frame_ready = 1;
}

void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY);
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE0);
  while(!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) {}

  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI48|RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.HSI48State = RCC_HSI48_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLM = 5;
  RCC_OscInitStruct.PLL.PLLN = 96;
  RCC_OscInitStruct.PLL.PLLP = 2;
  RCC_OscInitStruct.PLL.PLLQ = 2;
  RCC_OscInitStruct.PLL.PLLR = 2;
  RCC_OscInitStruct.PLL.PLLRGE = RCC_PLL1VCIRANGE_2;
  RCC_OscInitStruct.PLL.PLLVCOSEL = RCC_PLL1VCOWIDE;
  RCC_OscInitStruct.PLL.PLLFRACN = 0;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) Error_Handler();

  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              | RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2
                              | RCC_CLOCKTYPE_D3PCLK1|RCC_CLOCKTYPE_D1PCLK1;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.SYSCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB3CLKDivider = RCC_APB3_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV1;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_APB2_DIV1;
  RCC_ClkInitStruct.APB4CLKDivider = RCC_APB4_DIV1;
  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_1) != HAL_OK) Error_Handler();

  HAL_RCC_MCOConfig(RCC_MCO1, RCC_MCO1SOURCE_HSI48, RCC_MCODIV_4);
}

void Error_Handler(void)
{
  while (1) {}
}
