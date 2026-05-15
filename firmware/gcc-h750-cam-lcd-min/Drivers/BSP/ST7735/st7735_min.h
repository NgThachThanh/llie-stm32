#ifndef ST7735_MIN_H
#define ST7735_MIN_H

#include "main.h"
#include <stdint.h>

#define ST7735_MIN_WIDTH  160U
#define ST7735_MIN_HEIGHT 80U

void ST7735_MinInit(void);
void ST7735_MinFillRect(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint16_t color);
void ST7735_MinBlitRGB565(uint16_t x, uint16_t y, const uint8_t *data, uint16_t w, uint16_t h);

#endif
