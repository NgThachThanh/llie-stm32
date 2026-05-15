#include "camera.h"
#include "ov5640.h"

Camera_HandleTypeDef hcamera;

const uint16_t dvp_cam_resolution[][2] = {
  {0, 0},
  {88, 72},
  {176, 144},
  {352, 288},
  {88, 60},
  {176, 120},
  {352, 240},
  {40, 30},
  {80, 60},
  {160, 120},
  {320, 240},
  {640, 480},
  {60, 40},
  {120, 80},
  {240, 160},
  {480, 320},
  {64, 32},
  {64, 64},
  {128, 64},
  {128, 128},
  {128, 160},
  {128, 160},
  {720, 480},
  {752, 480},
  {800, 600},
  {1024, 768},
  {1280, 1024},
  {1600, 1200},
  {1280, 720},
  {1920, 1080},
  {1280, 960},
  {2592, 1944},
};

int32_t Camera_WriteRegb2(Camera_HandleTypeDef *hov, uint16_t reg_addr, uint8_t reg_data)
{
  return (HAL_I2C_Mem_Write(hov->hi2c, hov->addr + 1U, reg_addr,
                            I2C_MEMADD_SIZE_16BIT, &reg_data, 1, hov->timeout) == HAL_OK)
           ? Camera_OK : camera_ERROR;
}

int32_t Camera_ReadRegb2(Camera_HandleTypeDef *hov, uint16_t reg_addr, uint8_t *reg_data)
{
  return (HAL_I2C_Mem_Read(hov->hi2c, hov->addr + 1U, reg_addr,
                           I2C_MEMADD_SIZE_16BIT, reg_data, 1, hov->timeout) == HAL_OK)
           ? Camera_OK : camera_ERROR;
}

int32_t Camera_read_id(Camera_HandleTypeDef *hov)
{
  uint8_t idh = 0;
  uint8_t idl = 0;

  Camera_ReadRegb2(hov, 0x300A, &idh);
  Camera_ReadRegb2(hov, 0x300B, &idl);
  hov->manuf_id = 0;
  hov->device_id = ((uint16_t)idh << 8) | idl;
  return 0;
}

void Camera_Init_Device(I2C_HandleTypeDef *hi2c, framesize_t framesize)
{
  hcamera.hi2c = hi2c;
  hcamera.addr = OV5640_ADDRESS;
  hcamera.timeout = 100;

  Camera_read_id(&hcamera);
  if (hcamera.device_id == 0x5640U)
  {
    ov5640_init(framesize);
  }
}
