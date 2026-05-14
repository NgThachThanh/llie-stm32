



#include "main.h"
#include "dcmi.h"
#include "dma.h"
#include "i2c.h"
#include "spi.h"
#include "tim.h"
#include "gpio.h"



#include "camera.h"
#include "lcd.h"























void SystemClock_Config(void);

#define LLIE_BASELINE_GAIN_Q8  320U
#define LLIE_BASELINE_LIFT_R5  1U
#define LLIE_BASELINE_LIFT_G6  2U
#define LLIE_BASELINE_LIFT_B5  1U

#ifdef TFT96

#define FrameWidth 160
#define FrameHeight 120
#elif TFT18

#define FrameWidth 128
#define FrameHeight 160
#endif

__ALIGNED(32) uint16_t pic[FrameWidth][FrameHeight];
volatile uint32_t DCMI_FrameIsReady;
uint32_t Camera_FPS=0;
static uint8_t EnhanceEnabled = 0;

static uint32_t LLIE_ClampU32(uint32_t value, uint32_t max_value)
{
  return value > max_value ? max_value : value;
}

static uint16_t LLIE_ApplyBaselinePixel(uint16_t pixel)
{
  uint32_t red = (pixel >> 11) & 0x1FU;
  uint32_t green = (pixel >> 5) & 0x3FU;
  uint32_t blue = pixel & 0x1FU;

  red = ((red * LLIE_BASELINE_GAIN_Q8) >> 8) + LLIE_BASELINE_LIFT_R5;
  green = ((green * LLIE_BASELINE_GAIN_Q8) >> 8) + LLIE_BASELINE_LIFT_G6;
  blue = ((blue * LLIE_BASELINE_GAIN_Q8) >> 8) + LLIE_BASELINE_LIFT_B5;

  red = LLIE_ClampU32(red, 0x1FU);
  green = LLIE_ClampU32(green, 0x3FU);
  blue = LLIE_ClampU32(blue, 0x1FU);

  return (uint16_t)((red << 11) | (green << 5) | blue);
}

static void LLIE_InvalidateFrameBuffer(void)
{
  uint32_t addr = (uint32_t)&pic[0][0];
  uint32_t aligned_addr = addr & ~31U;
  uint32_t byte_count = FrameWidth * FrameHeight * sizeof(uint16_t);
  uint32_t aligned_byte_count = (byte_count + (addr - aligned_addr) + 31U) & ~31U;

  SCB_InvalidateDCache_by_Addr((void *)aligned_addr, (int32_t)aligned_byte_count);
}

static void LLIE_ProcessFrame(uint16_t *frame, uint32_t pixel_count)
{
  uint32_t index;

  if (!EnhanceEnabled)
  {
    return;
  }

  for (index = 0; index < pixel_count; index++)
  {
    frame[index] = LLIE_ApplyBaselinePixel(frame[index]);
  }
}

static void LLIE_PollButton(void)
{
  static GPIO_PinState last_state = GPIO_PIN_RESET;
  static uint32_t last_toggle_tick = 0;
  GPIO_PinState state = HAL_GPIO_ReadPin(KEY_GPIO_Port, KEY_Pin);
  uint32_t now = HAL_GetTick();

  if (state == GPIO_PIN_SET && last_state == GPIO_PIN_RESET && (now - last_toggle_tick) > 250U)
  {
    EnhanceEnabled = !EnhanceEnabled;
    last_toggle_tick = now;
  }

  last_state = state;
}





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
  MPU_InitStruct.BaseAddress      = D1_AXISRAM_BASE;
  MPU_InitStruct.Size             = MPU_REGION_SIZE_512KB;
  MPU_InitStruct.AccessPermission = MPU_REGION_FULL_ACCESS;
  MPU_InitStruct.IsBufferable     = MPU_ACCESS_BUFFERABLE;
  MPU_InitStruct.IsCacheable      = MPU_ACCESS_CACHEABLE;
  MPU_InitStruct.IsShareable      = MPU_ACCESS_SHAREABLE;
  MPU_InitStruct.Number           = MPU_REGION_NUMBER2;
  MPU_InitStruct.TypeExtField     = MPU_TEX_LEVEL1;
  MPU_InitStruct.SubRegionDisable = 0x00;
  MPU_InitStruct.DisableExec      = MPU_INSTRUCTION_ACCESS_ENABLE;
  HAL_MPU_ConfigRegion(&MPU_InitStruct);
	
  
  HAL_MPU_Enable(MPU_PRIVILEGED_DEFAULT);
}

static void CPU_CACHE_Enable(void)
{
  
  SCB_EnableICache();

  
  SCB_EnableDCache();
}

void LED_Blink(uint32_t Hdelay, uint32_t Ldelay)
{
  HAL_GPIO_WritePin(PE3_GPIO_Port, PE3_Pin, GPIO_PIN_SET);
  HAL_Delay(Hdelay - 1);
  HAL_GPIO_WritePin(PE3_GPIO_Port, PE3_Pin, GPIO_PIN_RESET);
  HAL_Delay(Ldelay - 1);
}



int main(void)
{
  

#ifdef W25Qxx
  SCB->VTOR = QSPI_BASE;
#endif
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
  
  LCD_Test();

  
  
  #ifdef TFT96
	Camera_Init_Device(&hi2c1, FRAMESIZE_QQVGA);
	#elif TFT18
	Camera_Init_Device(&hi2c1, FRAMESIZE_QQVGA2);
	#endif

	ST7735_FillRect(&st7735_pObj, 0, 0, ST7735Ctx.Width, ST7735Ctx.Height, BLACK);

  HAL_DCMI_Start_DMA(&hdcmi, DCMI_MODE_CONTINUOUS, (uint32_t)&pic, FrameWidth * FrameHeight * 2 / 4);

  

  
  
  while (1)
  {
    

    
    LLIE_PollButton();

    if (DCMI_FrameIsReady)
    {
      DCMI_FrameIsReady = 0;

      LLIE_InvalidateFrameBuffer();
      LLIE_ProcessFrame(&pic[0][0], FrameWidth * FrameHeight);

      #ifdef TFT96
			ST7735_FillRGBRect(&st7735_pObj,0,0,(uint8_t *)&pic[20][0], ST7735Ctx.Width, 80);
			#elif TFT18
			ST7735_FillRGBRect(&st7735_pObj,0,0,(uint8_t *)&pic[0][0], ST7735Ctx.Width, ST7735Ctx.Height);
			#endif
			
			LED_Blink(1, 1);
    }
    
  }
  
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
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }
  
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2
                              |RCC_CLOCKTYPE_D3PCLK1|RCC_CLOCKTYPE_D1PCLK1;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.SYSCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB3CLKDivider = RCC_APB3_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV1;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_APB2_DIV1;
  RCC_ClkInitStruct.APB4CLKDivider = RCC_APB4_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_1) != HAL_OK)
  {
    Error_Handler();
  }
  HAL_RCC_MCOConfig(RCC_MCO1, RCC_MCO1SOURCE_HSI48, RCC_MCODIV_4);
}



void HAL_DCMI_FrameEventCallback(DCMI_HandleTypeDef *hdcmi)
{
	static uint32_t count = 0,tick = 0;
	
	if(HAL_GetTick() - tick >= 1000)
	{
		tick = HAL_GetTick();
		Camera_FPS = count;
		count = 0;
	}
	count ++;
	
  DCMI_FrameIsReady = 1;
}




void Error_Handler(void)
{
  
  
  while (1)
  {
    LED_Blink(5, 250);
  }
  
}

#ifdef  USE_FULL_ASSERT

void assert_failed(uint8_t *file, uint32_t line)
{
  
  
  
}
#endif 

