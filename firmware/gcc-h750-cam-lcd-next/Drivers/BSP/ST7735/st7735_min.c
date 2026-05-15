#include "st7735_min.h"
#include "spi.h"
#include "tim.h"

#define LCD_RS_SET      HAL_GPIO_WritePin(LCD_WR_RS_GPIO_Port, LCD_WR_RS_Pin, GPIO_PIN_SET)
#define LCD_RS_RESET    HAL_GPIO_WritePin(LCD_WR_RS_GPIO_Port, LCD_WR_RS_Pin, GPIO_PIN_RESET)
#define LCD_CS_SET      HAL_GPIO_WritePin(LCD_CS_GPIO_Port, LCD_CS_Pin, GPIO_PIN_SET)
#define LCD_CS_RESET    HAL_GPIO_WritePin(LCD_CS_GPIO_Port, LCD_CS_Pin, GPIO_PIN_RESET)

#define ST7735_SWRESET  0x01U
#define ST7735_SLPOUT   0x11U
#define ST7735_NORON    0x13U
#define ST7735_INVON    0x21U
#define ST7735_DISPON   0x29U
#define ST7735_CASET    0x2AU
#define ST7735_RASET    0x2BU
#define ST7735_RAMWR    0x2CU
#define ST7735_MADCTL   0x36U
#define ST7735_COLMOD   0x3AU
#define ST7735_FRMCTR1  0xB1U
#define ST7735_FRMCTR2  0xB2U
#define ST7735_FRMCTR3  0xB3U
#define ST7735_INVCTR   0xB4U
#define ST7735_PWCTR1   0xC0U
#define ST7735_PWCTR2   0xC1U
#define ST7735_PWCTR3   0xC2U
#define ST7735_PWCTR4   0xC3U
#define ST7735_PWCTR5   0xC4U
#define ST7735_VMCTR1   0xC5U
#define ST7735_GMCTRP1  0xE0U
#define ST7735_GMCTRN1  0xE1U

static void lcd_write_cmd(uint8_t cmd)
{
  LCD_CS_RESET;
  LCD_RS_RESET;
  HAL_SPI_Transmit(&hspi4, &cmd, 1, 100);
  LCD_CS_SET;
}

static void lcd_write_data(const uint8_t *data, uint32_t len)
{
  if (len == 0U) return;
  LCD_CS_RESET;
  LCD_RS_SET;
  HAL_SPI_Transmit(&hspi4, (uint8_t *)data, (uint16_t)len, 500);
  LCD_CS_SET;
}

static void lcd_write_reg(uint8_t cmd, const uint8_t *data, uint32_t len)
{
  lcd_write_cmd(cmd);
  lcd_write_data(data, len);
}

static void lcd_set_window(uint16_t x, uint16_t y, uint16_t w, uint16_t h)
{
  uint16_t x0 = x + 1U;
  uint16_t y0 = y + 26U;
  uint16_t x1 = x0 + w - 1U;
  uint16_t y1 = y0 + h - 1U;
  uint8_t data[4];

  data[0] = (uint8_t)(x0 >> 8);
  data[1] = (uint8_t)x0;
  data[2] = (uint8_t)(x1 >> 8);
  data[3] = (uint8_t)x1;
  lcd_write_reg(ST7735_CASET, data, 4);

  data[0] = (uint8_t)(y0 >> 8);
  data[1] = (uint8_t)y0;
  data[2] = (uint8_t)(y1 >> 8);
  data[3] = (uint8_t)y1;
  lcd_write_reg(ST7735_RASET, data, 4);
}

void ST7735_MinInit(void)
{
  const uint8_t frmctr[] = {0x01U, 0x2CU, 0x2DU};
  const uint8_t frmctr3[] = {0x01U, 0x2CU, 0x2DU, 0x01U, 0x2CU, 0x2DU};
  const uint8_t pwctr1[] = {0xA2U, 0x02U, 0x84U};
  const uint8_t pwctr3[] = {0x0AU, 0x00U};
  const uint8_t pwctr4[] = {0x8AU, 0x2AU};
  const uint8_t pwctr5[] = {0x8AU, 0xEEU};
  const uint8_t gamma_pos[] = {0x02U,0x1CU,0x07U,0x12U,0x37U,0x32U,0x29U,0x2DU,0x29U,0x25U,0x2BU,0x39U,0x00U,0x01U,0x03U,0x10U};
  const uint8_t gamma_neg[] = {0x03U,0x1DU,0x07U,0x06U,0x2EU,0x2CU,0x29U,0x2DU,0x2EU,0x2EU,0x37U,0x3FU,0x00U,0x00U,0x02U,0x10U};
  uint8_t data;

  HAL_TIMEx_PWMN_Start(&htim1, TIM_CHANNEL_2);
  __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_2, 100U);

  lcd_write_cmd(ST7735_SWRESET);
  HAL_Delay(120);
  lcd_write_cmd(ST7735_SWRESET);
  HAL_Delay(120);
  lcd_write_cmd(ST7735_SLPOUT);
  HAL_Delay(120);

  lcd_write_reg(ST7735_FRMCTR1, frmctr, sizeof(frmctr));
  lcd_write_reg(ST7735_FRMCTR2, frmctr, sizeof(frmctr));
  lcd_write_reg(ST7735_FRMCTR3, frmctr3, sizeof(frmctr3));
  data = 0x07U; lcd_write_reg(ST7735_INVCTR, &data, 1);
  lcd_write_reg(ST7735_PWCTR1, pwctr1, sizeof(pwctr1));
  data = 0xC5U; lcd_write_reg(ST7735_PWCTR2, &data, 1);
  lcd_write_reg(ST7735_PWCTR3, pwctr3, sizeof(pwctr3));
  lcd_write_reg(ST7735_PWCTR4, pwctr4, sizeof(pwctr4));
  lcd_write_reg(ST7735_PWCTR5, pwctr5, sizeof(pwctr5));
  data = 0x0EU; lcd_write_reg(ST7735_VMCTR1, &data, 1);
  lcd_write_cmd(ST7735_INVON);
  data = 0x05U; lcd_write_reg(ST7735_COLMOD, &data, 1);
  lcd_write_reg(ST7735_GMCTRP1, gamma_pos, sizeof(gamma_pos));
  lcd_write_reg(ST7735_GMCTRN1, gamma_neg, sizeof(gamma_neg));
  data = 0xA8U; lcd_write_reg(ST7735_MADCTL, &data, 1);
  lcd_write_cmd(ST7735_NORON);
  lcd_write_cmd(ST7735_DISPON);
  HAL_Delay(10);
}

void ST7735_MinFillRect(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint16_t color)
{
  uint32_t count = (uint32_t)w * h;
  uint8_t data[2] = {(uint8_t)(color >> 8), (uint8_t)color};

  lcd_set_window(x, y, w, h);
  lcd_write_cmd(ST7735_RAMWR);
  LCD_CS_RESET;
  LCD_RS_SET;
  while (count--)
  {
    HAL_SPI_Transmit(&hspi4, data, 2, 100);
  }
  LCD_CS_SET;
}

void ST7735_MinBlitRGB565(uint16_t x, uint16_t y, const uint8_t *data, uint16_t w, uint16_t h)
{
  lcd_set_window(x, y, w, h);
  lcd_write_cmd(ST7735_RAMWR);
  lcd_write_data(data, (uint32_t)w * h * 2U);
}
