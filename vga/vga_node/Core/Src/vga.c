#include "main.h"
#include "cmsis_os.h"

#include "vga.h"

extern TIM_HandleTypeDef htim16;
extern UART_HandleTypeDef huart1;

// extern DAC_HandleTypeDef hdac1;

#define VSIZE   480     /* Vertical resolution (in lines) */
#define HSIZE   80      /* Horizontal resolution (in bytes) (640 pixels, 1 byte per pixel) */

uint8_t fb[VSIZE][HSIZE];		/* Frame buffer for red pixels */
static uint16_t vline = 0;		/* The current line being drawn */
static uint32_t vflag = 0;		/* When 1, the DAC DMA request can draw on the screen */
static uint32_t vdraw = 0;		/* Used to increment vline every 3 drawn lines */

/**
 * Initialise the VGA driver
 */
void vga_init(void) {

    HAL_TIM_Base_Start_IT(&htim16);
}

// HAL timer callback
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim) {
	// Check which version of the timer triggered this callback
	if (htim == &htim16 ) {
		// do things here
	}
}

/**
 * Clears the VGA screen
 */
void vga_clear_screen(void) {
    uint16_t x, y;

	for (y = 0; y < VSIZE; y++) {
		for (x = 0; x < HSIZE; x++) {
			fb[y][x] = 0;
        }
    }	
}