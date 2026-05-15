#ifndef LLIE_PIPELINE_H
#define LLIE_PIPELINE_H

#include <stdint.h>

typedef enum
{
  LLIE_MODE_BYPASS = 0,
  LLIE_MODE_BASELINE = 1,
  LLIE_MODE_AI = 2,
} LLIE_Mode;

typedef struct
{
  uint16_t gain_q8;
  uint16_t gamma_q8;
  uint8_t lift;
} LLIE_Controls;

void LLIE_Init(void);
void LLIE_UpdateAIControls(const uint16_t *full_frame_rgb565, uint32_t width, uint32_t height);
void LLIE_ProcessFrame(uint16_t *rgb565, uint32_t pixel_count);
void LLIE_SetMode(LLIE_Mode mode);
LLIE_Mode LLIE_GetMode(void);
LLIE_Controls LLIE_GetControls(void);

#endif
