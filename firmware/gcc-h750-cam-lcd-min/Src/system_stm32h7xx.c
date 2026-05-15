







#include "stm32h7xx.h"
#include <math.h>
#if !defined  (HSE_VALUE)
#define HSE_VALUE    ((uint32_t)25000000) 
#endif 

#if !defined  (CSI_VALUE)
  #define CSI_VALUE    ((uint32_t)4000000) 
#endif 

#if !defined  (HSI_VALUE)
  #define HSI_VALUE    ((uint32_t)64000000) 
#endif 
















#define VECT_TAB_OFFSET  0x00000000UL 









  
  uint32_t SystemCoreClock = 64000000;
  uint32_t SystemD2Clock = 64000000;
  const  uint8_t D1CorePrescTable[16] = {0, 0, 0, 0, 1, 2, 3, 4, 1, 2, 3, 4, 6, 7, 8, 9};










void SystemInit (void)
{
#if defined (DATA_IN_D2_SRAM)
 __IO uint32_t tmpreg;
#endif 

  
  #if (__FPU_PRESENT == 1) && (__FPU_USED == 1)
    SCB->CPACR |= ((3UL << (10*2))|(3UL << (11*2)));  
  #endif
  
  
  RCC->CR |= RCC_CR_HSION;

  
  RCC->CFGR = 0x00000000;

  
  RCC->CR &= 0xEAF6ED7FU;

#if defined(D3_SRAM_BASE)
  
  RCC->D1CFGR = 0x00000000;

  
  RCC->D2CFGR = 0x00000000;

  
  RCC->D3CFGR = 0x00000000;
#else
  
  RCC->CDCFGR1 = 0x00000000;

  
  RCC->CDCFGR2 = 0x00000000;

  
  RCC->SRDCFGR = 0x00000000;
#endif
  
  RCC->PLLCKSELR = 0x00000000;

  
  RCC->PLLCFGR = 0x00000000;
  
  RCC->PLL1DIVR = 0x00000000;
  
  RCC->PLL1FRACR = 0x00000000;

  
  RCC->PLL2DIVR = 0x00000000;

  

  RCC->PLL2FRACR = 0x00000000;
  
  RCC->PLL3DIVR = 0x00000000;

  
  RCC->PLL3FRACR = 0x00000000;

  
  RCC->CR &= 0xFFFBFFFFU;

  
  RCC->CIER = 0x00000000;

#if (STM32H7_DEV_ID == 0x450UL)
  
  if((DBGMCU->IDCODE & 0xFFFF0000U) < 0x20000000U)
  {
    
    
    *((__IO uint32_t*)0x51008108) = 0x000000001U;
  }
#endif

#if defined (DATA_IN_D2_SRAM)
  
#if defined(RCC_AHB2ENR_D2SRAM3EN)
  RCC->AHB2ENR |= (RCC_AHB2ENR_D2SRAM1EN | RCC_AHB2ENR_D2SRAM2EN | RCC_AHB2ENR_D2SRAM3EN);
#elif defined(RCC_AHB2ENR_D2SRAM2EN)
  RCC->AHB2ENR |= (RCC_AHB2ENR_D2SRAM1EN | RCC_AHB2ENR_D2SRAM2EN);
#else
  RCC->AHB2ENR |= (RCC_AHB2ENR_AHBSRAM1EN | RCC_AHB2ENR_AHBSRAM2EN);
#endif 

  tmpreg = RCC->AHB2ENR;
  (void) tmpreg;
#endif 

#if defined(DUAL_CORE) && defined(CORE_CM4)
  
#ifdef VECT_TAB_SRAM
  SCB->VTOR = D2_AHBSRAM_BASE | VECT_TAB_OFFSET; 
#else
  SCB->VTOR = FLASH_BANK2_BASE | VECT_TAB_OFFSET; 
#endif 

#else

  
#ifdef VECT_TAB_SRAM
  SCB->VTOR = D1_AXISRAM_BASE  | VECT_TAB_OFFSET; 
#else
  SCB->VTOR = FLASH_BANK1_BASE | VECT_TAB_OFFSET; 
#endif

#endif 

}


void SystemCoreClockUpdate (void)
{
  uint32_t pllp, pllsource, pllm, pllfracen, hsivalue, tmp;
  uint32_t common_system_clock;
  float_t fracn1, pllvco;


  

  switch (RCC->CFGR & RCC_CFGR_SWS)
  {
  case RCC_CFGR_SWS_HSI:  
    common_system_clock = (uint32_t) (HSI_VALUE >> ((RCC->CR & RCC_CR_HSIDIV)>> 3));
    break;

  case RCC_CFGR_SWS_CSI:  
    common_system_clock = CSI_VALUE;
    break;

  case RCC_CFGR_SWS_HSE:  
    common_system_clock = HSE_VALUE;
    break;

  case RCC_CFGR_SWS_PLL1:  

    
    pllsource = (RCC->PLLCKSELR & RCC_PLLCKSELR_PLLSRC);
    pllm = ((RCC->PLLCKSELR & RCC_PLLCKSELR_DIVM1)>> 4)  ;
    pllfracen = ((RCC->PLLCFGR & RCC_PLLCFGR_PLL1FRACEN)>>RCC_PLLCFGR_PLL1FRACEN_Pos);
    fracn1 = (float_t)(uint32_t)(pllfracen* ((RCC->PLL1FRACR & RCC_PLL1FRACR_FRACN1)>> 3));

    if (pllm != 0U)
    {
      switch (pllsource)
      {
        case RCC_PLLCKSELR_PLLSRC_HSI:  

        hsivalue = (HSI_VALUE >> ((RCC->CR & RCC_CR_HSIDIV)>> 3)) ;
        pllvco = ( (float_t)hsivalue / (float_t)pllm) * ((float_t)(uint32_t)(RCC->PLL1DIVR & RCC_PLL1DIVR_N1) + (fracn1/(float_t)0x2000) +(float_t)1 );

        break;

        case RCC_PLLCKSELR_PLLSRC_CSI:  
          pllvco = ((float_t)CSI_VALUE / (float_t)pllm) * ((float_t)(uint32_t)(RCC->PLL1DIVR & RCC_PLL1DIVR_N1) + (fracn1/(float_t)0x2000) +(float_t)1 );
        break;

        case RCC_PLLCKSELR_PLLSRC_HSE:  
          pllvco = ((float_t)HSE_VALUE / (float_t)pllm) * ((float_t)(uint32_t)(RCC->PLL1DIVR & RCC_PLL1DIVR_N1) + (fracn1/(float_t)0x2000) +(float_t)1 );
        break;

      default:
          pllvco = ((float_t)CSI_VALUE / (float_t)pllm) * ((float_t)(uint32_t)(RCC->PLL1DIVR & RCC_PLL1DIVR_N1) + (fracn1/(float_t)0x2000) +(float_t)1 );
        break;
      }
      pllp = (((RCC->PLL1DIVR & RCC_PLL1DIVR_P1) >>9) + 1U ) ;
      common_system_clock =  (uint32_t)(float_t)(pllvco/(float_t)pllp);
    }
    else
    {
      common_system_clock = 0U;
    }
    break;

  default:
    common_system_clock = CSI_VALUE;
    break;
  }

  
#if defined (RCC_D1CFGR_D1CPRE)
  tmp = D1CorePrescTable[(RCC->D1CFGR & RCC_D1CFGR_D1CPRE)>> RCC_D1CFGR_D1CPRE_Pos];

  
  common_system_clock >>= tmp;

  
  SystemD2Clock = (common_system_clock >> ((D1CorePrescTable[(RCC->D1CFGR & RCC_D1CFGR_HPRE)>> RCC_D1CFGR_HPRE_Pos]) & 0x1FU));

#else
  tmp = D1CorePrescTable[(RCC->CDCFGR1 & RCC_CDCFGR1_CDCPRE)>> RCC_CDCFGR1_CDCPRE_Pos];

  
  common_system_clock >>= tmp;

  
  SystemD2Clock = (common_system_clock >> ((D1CorePrescTable[(RCC->CDCFGR1 & RCC_CDCFGR1_HPRE)>> RCC_CDCFGR1_HPRE_Pos]) & 0x1FU));

#endif

#if defined(DUAL_CORE) && defined(CORE_CM4)
  SystemCoreClock = SystemD2Clock;
#else
  SystemCoreClock = common_system_clock;
#endif 
}








