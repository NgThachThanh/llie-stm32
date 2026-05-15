#include "llie_pipeline.h"
#include "llie_weights.h"

#define LUT_SIZE 256U
#define MODEL_W 96U
#define MODEL_H 96U
#define MODEL_CH 8U

static LLIE_Mode s_mode = LLIE_MODE_BASELINE;
static LLIE_Controls s_controls = {
  .gain_q8 = 320U,
  .gamma_q8 = 230U,
  .lift = 6U,
};
static uint8_t s_luma_lut[LUT_SIZE];

/* Three rolling rows of block1 output are enough for streamed block2 inference. */
static float s_b1_rows[3][MODEL_CH][MODEL_W];

static uint8_t clamp_u8(int32_t value)
{
  if (value < 0) return 0U;
  if (value > 255) return 255U;
  return (uint8_t)value;
}

static float clamp_f32(float value, float lo, float hi)
{
  if (value < lo) return lo;
  if (value > hi) return hi;
  return value;
}

static float fast_absf(float x)
{
  return (x < 0.0f) ? -x : x;
}

/* Small, monotonic sigmoid approximation. Good enough for the bounded control head. */
static float fast_sigmoid(float x)
{
  return 0.5f + (x / (2.0f * (1.0f + fast_absf(x))));
}

static uint16_t swap16(uint16_t x)
{
  return (uint16_t)((x << 8) | (x >> 8));
}

static uint8_t rgb565_to_luma(uint16_t wire)
{
  uint16_t p = swap16(wire);
  uint8_t r5 = (uint8_t)((p >> 11) & 0x1FU);
  uint8_t g6 = (uint8_t)((p >> 5) & 0x3FU);
  uint8_t b5 = (uint8_t)(p & 0x1FU);
  uint8_t r8 = (uint8_t)((r5 * 255U) / 31U);
  uint8_t g8 = (uint8_t)((g6 * 255U) / 63U);
  uint8_t b8 = (uint8_t)((b5 * 255U) / 31U);
  return (uint8_t)(((77U * r8) + (150U * g8) + (29U * b8)) >> 8);
}

static float sample_luma_norm(const uint16_t *frame, uint32_t width, uint32_t height, int32_t x96, int32_t y96)
{
  if (x96 < 0) x96 = 0;
  if (y96 < 0) y96 = 0;
  if (x96 >= (int32_t)MODEL_W) x96 = MODEL_W - 1;
  if (y96 >= (int32_t)MODEL_H) y96 = MODEL_H - 1;

  uint32_t src_x = ((uint32_t)x96 * width) / MODEL_W;
  uint32_t src_y = ((uint32_t)y96 * height) / MODEL_H;
  return (float)rgb565_to_luma(frame[src_y * width + src_x]) / 255.0f;
}

static void compute_block1_row(const uint16_t *frame, uint32_t width, uint32_t height, int32_t y96, float out[MODEL_CH][MODEL_W])
{
  for (uint32_t x = 0; x < MODEL_W; ++x)
  {
    float dw = llie_b1_dw_b[0];
    for (int32_t ky = -1; ky <= 1; ++ky)
    {
      for (int32_t kx = -1; kx <= 1; ++kx)
      {
        uint32_t wi = (uint32_t)((ky + 1) * 3 + (kx + 1));
        dw += sample_luma_norm(frame, width, height, (int32_t)x + kx, y96 + ky) * llie_b1_dw_w[wi];
      }
    }

    for (uint32_t c = 0; c < MODEL_CH; ++c)
    {
      float v = dw * llie_b1_pw_w[c] + llie_b1_pw_b[c];
      out[c][x] = (v > 0.0f) ? v : 0.0f;
    }
  }
}

static uint8_t gamma_curve(uint8_t x, uint16_t gamma_q8)
{
  if (gamma_q8 >= 256U)
  {
    return x;
  }

  uint16_t brighten = (uint16_t)x + ((255U - x) >> 3);
  uint16_t blend = (uint16_t)(256U - gamma_q8);
  return (uint8_t)(((uint16_t)x * gamma_q8 + brighten * blend) >> 8);
}

static void rebuild_luma_lut(void)
{
  for (uint32_t i = 0; i < LUT_SIZE; ++i)
  {
    uint8_t y = clamp_u8((int32_t)i + s_controls.lift);
    y = clamp_u8(((uint32_t)y * s_controls.gain_q8) >> 8);
    s_luma_lut[i] = gamma_curve(y, s_controls.gamma_q8);
  }
}

void LLIE_Init(void)
{
  rebuild_luma_lut();
}

void LLIE_SetMode(LLIE_Mode mode)
{
  s_mode = mode;
}

LLIE_Mode LLIE_GetMode(void)
{
  return s_mode;
}

LLIE_Controls LLIE_GetControls(void)
{
  return s_controls;
}

void LLIE_UpdateAIControls(const uint16_t *full_frame_rgb565, uint32_t width, uint32_t height)
{
  if (s_mode != LLIE_MODE_AI)
  {
    return;
  }

  float gap[MODEL_CH] = {0};
  compute_block1_row(full_frame_rgb565, width, height, 0, s_b1_rows[0]);
  compute_block1_row(full_frame_rgb565, width, height, 0, s_b1_rows[1]);
  compute_block1_row(full_frame_rgb565, width, height, 1, s_b1_rows[2]);

  for (uint32_t y = 0; y < MODEL_H; ++y)
  {
    float *row_prev = &s_b1_rows[(y + 0U) % 3U][0][0];
    float *row_curr = &s_b1_rows[(y + 1U) % 3U][0][0];
    float *row_next = &s_b1_rows[(y + 2U) % 3U][0][0];

    for (uint32_t x = 0; x < MODEL_W; ++x)
    {
      float dw[MODEL_CH];
      for (uint32_t c = 0; c < MODEL_CH; ++c)
      {
        const float *w = &llie_b2_dw_w[c * 9U];
        float v = llie_b2_dw_b[c];
        uint32_t xm1 = (x == 0U) ? 0U : x - 1U;
        uint32_t xp1 = (x + 1U >= MODEL_W) ? MODEL_W - 1U : x + 1U;
        v += row_prev[c * MODEL_W + xm1] * w[0];
        v += row_prev[c * MODEL_W + x]   * w[1];
        v += row_prev[c * MODEL_W + xp1] * w[2];
        v += row_curr[c * MODEL_W + xm1] * w[3];
        v += row_curr[c * MODEL_W + x]   * w[4];
        v += row_curr[c * MODEL_W + xp1] * w[5];
        v += row_next[c * MODEL_W + xm1] * w[6];
        v += row_next[c * MODEL_W + x]   * w[7];
        v += row_next[c * MODEL_W + xp1] * w[8];
        dw[c] = v;
      }

      for (uint32_t oc = 0; oc < MODEL_CH; ++oc)
      {
        float v = llie_b2_pw_b[oc];
        for (uint32_t ic = 0; ic < MODEL_CH; ++ic)
        {
          v += dw[ic] * llie_b2_pw_w[oc * MODEL_CH + ic];
        }
        if (v > 0.0f)
        {
          gap[oc] += v;
        }
      }
    }

    if (y + 2U < MODEL_H)
    {
      compute_block1_row(full_frame_rgb565, width, height, (int32_t)(y + 2U), s_b1_rows[y % 3U]);
    }
  }

  for (uint32_t c = 0; c < MODEL_CH; ++c)
  {
    gap[c] /= (float)(MODEL_W * MODEL_H);
  }

  float fc1[MODEL_CH];
  for (uint32_t o = 0; o < MODEL_CH; ++o)
  {
    float v = llie_fc1_b[o];
    for (uint32_t i = 0; i < MODEL_CH; ++i)
    {
      v += gap[i] * llie_fc1_w[o * MODEL_CH + i];
    }
    fc1[o] = (v > 0.0f) ? v : 0.0f;
  }

  float raw[3];
  for (uint32_t o = 0; o < 3U; ++o)
  {
    float v = llie_fc2_b[o];
    for (uint32_t i = 0; i < MODEL_CH; ++i)
    {
      v += fc1[i] * llie_fc2_w[o * MODEL_CH + i];
    }
    raw[o] = v;
  }

  float gain = 1.0f + fast_sigmoid(raw[0]) * 1.5f;
  float gamma = 0.7f + fast_sigmoid(raw[1]) * 0.9f;
  float lift = fast_sigmoid(raw[2]) * 24.0f;

  gain = clamp_f32(gain, 1.0f, 2.5f);
  gamma = clamp_f32(gamma, 0.7f, 1.6f);
  lift = clamp_f32(lift, 0.0f, 24.0f);

  s_controls.gain_q8 = (uint16_t)(gain * 256.0f);
  s_controls.gamma_q8 = (uint16_t)(gamma * 256.0f);
  s_controls.lift = (uint8_t)(lift + 0.5f);
  rebuild_luma_lut();
}

void LLIE_ProcessFrame(uint16_t *rgb565, uint32_t pixel_count)
{
  if (s_mode == LLIE_MODE_BYPASS)
  {
    return;
  }

  for (uint32_t i = 0; i < pixel_count; ++i)
  {
    uint16_t p = swap16(rgb565[i]);
    uint8_t r5 = (uint8_t)((p >> 11) & 0x1FU);
    uint8_t g6 = (uint8_t)((p >> 5) & 0x3FU);
    uint8_t b5 = (uint8_t)(p & 0x1FU);

    uint8_t r8 = (uint8_t)((r5 * 255U) / 31U);
    uint8_t g8 = (uint8_t)((g6 * 255U) / 63U);
    uint8_t b8 = (uint8_t)((b5 * 255U) / 31U);

    uint8_t y = (uint8_t)(((77U * r8) + (150U * g8) + (29U * b8)) >> 8);
    uint8_t y_enhanced = s_luma_lut[y];

    if (y > 0U)
    {
      uint16_t scale_q8 = (uint16_t)(((uint16_t)y_enhanced << 8) / y);
      r8 = clamp_u8(((uint32_t)r8 * scale_q8) >> 8);
      g8 = clamp_u8(((uint32_t)g8 * scale_q8) >> 8);
      b8 = clamp_u8(((uint32_t)b8 * scale_q8) >> 8);
    }
    else
    {
      r8 = y_enhanced;
      g8 = y_enhanced;
      b8 = y_enhanced;
    }

    r5 = (uint8_t)((r8 * 31U) / 255U);
    g6 = (uint8_t)((g8 * 63U) / 255U);
    b5 = (uint8_t)((b8 * 31U) / 255U);

    p = (uint16_t)((r5 << 11) | (g6 << 5) | b5);
    rgb565[i] = swap16(p);
  }
}
