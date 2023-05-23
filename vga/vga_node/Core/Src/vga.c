#include "main.h"
#include "cmsis_os.h"

#include "vga.h"

extern TIM_HandleTypeDef htim2;
extern TIM_HandleTypeDef htim3;

/**
 * Initialise the VGA driver
 */
void vga_init(void) {

    HAL_TIM_Base_Start_IT(&htim2);
    HAL_TIM_Base_Start_IT(&htim3);
}