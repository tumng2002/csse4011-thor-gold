#include <stdio.h>
#include "main.h"
#include "cmsis_os.h"

#include "vga.h"
#include "radar.h"

extern UART_HandleTypeDef huart1;

osThreadId_t radarTaskHandle;
const osThreadAttr_t radarTask_attributes = {
  .name = "radarTask",
  .stack_size = 128 * 4,
  .priority = (osPriority_t) osPriorityRealtime,
};

unsigned char uart_getc(void) {
    uint8_t rxChar = '\0';

    //Non Block receive - 0 delay (set to HAL_MAX_DELAY for blocking)
    if (HAL_UART_Receive(&huart1, &rxChar, 1, HAL_MAX_DELAY) == HAL_OK) {
        return rxChar;
    } else {
        return '\0';
    }
}

void radarTask(void *argument) {

    for (;;) {

        unsigned char c = uart_getc();

        char string[4];
        sprintf(string, "%c\n\r", c);

        HAL_UART_Transmit(&huart1, (uint8_t*) string, 20, 0);
    }
}

void radar_task_init() {
    radarTaskHandle = osThreadNew(radarTask, NULL, &radarTask_attributes);
}