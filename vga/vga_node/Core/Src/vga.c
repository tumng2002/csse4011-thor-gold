#include "main.h"
#include "cmsis_os.h"

#include "vga.h"

extern TIM_HandleTypeDef htim2;
extern TIM_HandleTypeDef htim3;

extern DAC_HandleTypeDef hdac1;

#define VSIZE   200     /* Vertical resolution (in lines) */
#define HSIZE   50      /* Horizontal resolution (in bytes) */
#define VTOTAL	52      /* Total bytes to send through DMA */

uint32_t red_fb[VSIZE][HSIZE+2];    /* Frame buffer for red pixels */
uint32_t green_fb[VSIZE][HSIZE+2];  /* Frame buffer for green pixels */
uint32_t blue_fb[VSIZE][HSIZE+2];   /* Frame buffer for blue pixels */
static uint16_t vline = 0;		    /* The current line being drawn */
static uint32_t vflag = 0;			/* When 1, the DAC DMA request can draw on the screen */
static uint32_t vdraw = 0;			/* Used to increment vline every 3 drawn lines */

/**
 * Initialise the VGA driver
 */
void vga_init(void) {

    HAL_TIM_Base_Start_IT(&htim2);
    HAL_TIM_Base_Start_IT(&htim3);

    HAL_DAC_Start_DMA(&hdac1, DAC_CHANNEL_1, &(red_fb[0][0]), HSIZE+2, DAC_ALIGN_8B_R);
    HAL_DAC_Start_DMA(&hdac1, DAC_CHANNEL_2, &(green_fb[0][0]), HSIZE+2, DAC_ALIGN_8B_R);
}

/**
 * Call inside the VSYNC IRQ to handle the interrupt
 */
void vga_vsync_irq(void) {
    vflag = 1;
	// TIM2->SR = 0xFFF7; //~TIM_IT_CC3;
}

/**
 * Call inside the HSYNC IRQ to handle the interrupt
 */
void vga_hsync_irq(void) {
    if (vflag) {
		DMA1_Channel3->CCR = 0x93;
	}
	// TIM1->SR = 0xFFFB; //~TIM_IT_CC2;
}

/**
 * Clears the VGA screen
 */
void vga_clear_screen(void) {
    uint16_t x, y;

	for (y = 0; y < VSIZE; y++) {
		for (x = 0; x < VTOTAL; x++) {
			red_fb[y][x] = 0;
            green_fb[y][x] = 0;
            blue_fb[y][x] = 0;
        }
    }	
}