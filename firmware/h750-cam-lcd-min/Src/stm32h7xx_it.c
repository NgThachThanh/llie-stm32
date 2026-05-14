




#include "main.h"
#include "stm32h7xx_it.h"











 























extern DMA_HandleTypeDef hdma_dcmi;
extern DCMI_HandleTypeDef hdcmi;
extern TIM_HandleTypeDef htim16;








void NMI_Handler(void)
{
  

  
  

  
}


void HardFault_Handler(void)
{
  

  
  while (1)
  {
    
    
  }
}


void MemManage_Handler(void)
{
  

  
  while (1)
  {
    
    
  }
}


void BusFault_Handler(void)
{
  

  
  while (1)
  {
    
    
  }
}


void UsageFault_Handler(void)
{
  

  
  while (1)
  {
    
    
  }
}


void SVC_Handler(void)
{
  

  
  

  
}


void DebugMon_Handler(void)
{
  

  
  

  
}


void PendSV_Handler(void)
{
  

  
  

  
}


void SysTick_Handler(void)
{
  

  
  HAL_IncTick();
  

  
}









void DMA1_Stream0_IRQHandler(void)
{
  

  
  HAL_DMA_IRQHandler(&hdma_dcmi);
  

  
}


void DCMI_IRQHandler(void)
{
  

  
  HAL_DCMI_IRQHandler(&hdcmi);
  

  
}


void TIM16_IRQHandler(void)
{
  

  
  HAL_TIM_IRQHandler(&htim16);
  

  
}





