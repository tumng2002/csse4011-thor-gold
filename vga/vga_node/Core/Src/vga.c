#include "main.h"
#include "cmsis_os.h"

#include "vga.h"

extern TIM_HandleTypeDef htim16;
extern UART_HandleTypeDef huart1;

uint8_t fb[BUFFER_VSIZE][BUFFER_HSIZE];	/* Frame buffer for pixels */

static uint16_t hpos = 0;	/* The current position in the horizontal line */
static uint16_t vline = 0;	/* The current line being drawn */

/**
 * Initialise the VGA driver
 */
void vga_init(void) {

	// set the red, green, and blue pins to low
	HAL_GPIO_WritePin(VGA_RED_GPIO_Port, VGA_RED_Pin, GPIO_PIN_RESET);
	HAL_GPIO_WritePin(VGA_GREEN_GPIO_Port, VGA_GREEN_Pin, GPIO_PIN_RESET);
	HAL_GPIO_WritePin(VGA_BLUE_GPIO_Port, VGA_BLUE_Pin, GPIO_PIN_RESET);

	// set the HSYNC and VSYNC pins to high
	HAL_GPIO_WritePin(VGA_HSYNC_GPIO_Port, VGA_HSYNC_Pin, GPIO_PIN_SET);
	HAL_GPIO_WritePin(VGA_VSYNC_GPIO_Port, VGA_VSYNC_Pin, GPIO_PIN_SET);

	// clear the screen before writing
	vga_clear_screen();

	// start the timer with interrupts
    HAL_TIM_Base_Start_IT(&htim16);
}

/**
 * Clears the VGA screen
 */
void vga_clear_screen(void) {
    uint32_t x, y;

	for (y = 0; y < BUFFER_VSIZE; y++) {
		for (x = 0; x < BUFFER_HSIZE; x++) {
			fb[y][x] = 0;
        }
    }	
}

/**
 * Write a new frame to screen
 * 
 * @param frame a pointer to a new frame buffer of size BUFFER_VSIZE*BUFFER_HSIZE
 */
void vga_write_frame(uint8_t** frame) {
	uint16_t x, y;

	for (y = 0; y < BUFFER_VSIZE; y++) {
		for (x = 0; x < BUFFER_HSIZE; x++) {
			fb[y][x] = frame[x][y];
        }
    }
}

/**
 * Write a new value to a pixel on the screen
 * 
 * @param pixel the new value of the pixel
 * @param x horizontal position of the pixel
 * @param y vertical position of the pixel
 */
void vga_write_pixel(uint8_t pixel, uint16_t x, uint16_t y) {
	fb[y][x] = pixel;
}

/**
 * Get the state of a specific colour for a given pixel from the buffer.
 * 
 * @param pixel the pixel from the frame buffer
 * @param colour the desired colour: 0 for red, 1 for green, 2 for blue
 * @return the state to set the colour output for the pixel
 */
GPIO_PinState vga_pixel_colour_state(uint8_t pixel, uint8_t colour) {

	switch (colour) {
		case 0:
			// red
			if ((pixel & 0x01) == 1) {
				return GPIO_PIN_SET;
			}
			return GPIO_PIN_RESET;
		case 1:
			// green
			if ((pixel & 0x02) == 2) {
				return GPIO_PIN_SET;
			}
			return GPIO_PIN_RESET;
		case 2:
			// blue
			if ((pixel & 0x04) == 4) {
				return GPIO_PIN_SET;
			}
			return GPIO_PIN_RESET;
		default:
			// invalid colour
			return GPIO_PIN_RESET;
	}
}

/**
 * Get a pixel from the buffer
 */
uint8_t vga_get_pixel_from_buffer(uint16_t x, uint16_t y) {
	uint16_t bx = x/4;	// get the horizontal position of the pixel in the buffer
	uint16_t by = y/2;	// get the vertical position of the pixel in the buffer

	return fb[by-1][bx-1];
}

// HAL timer callback
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim) {
	// Check which version of the timer triggered this callback
	if (htim == &htim16 ) {
		if (hpos == 0) {
			// in the first clock cycle of the line, set the value for vsync
			if (vline == VSIZE + 10) {
				// drop the vsync pin low
				HAL_GPIO_WritePin(VGA_VSYNC_GPIO_Port, VGA_VSYNC_Pin, GPIO_PIN_RESET);
			} 
			
			if (vline == VSIZE + 10 + 2) {
				// bring vsync back up high
				HAL_GPIO_WritePin(VGA_VSYNC_GPIO_Port, VGA_VSYNC_Pin, GPIO_PIN_SET);
			}
		}

		if (hpos < HSIZE && vline < VSIZE) {
			// writing pixels
			//HAL_GPIO_WritePin(VGA_RED_GPIO_Port, VGA_RED_Pin, vga_pixel_colour_state(fb[vline][hpos], 0));
			//HAL_GPIO_WritePin(VGA_GREEN_GPIO_Port, VGA_GREEN_Pin, vga_pixel_colour_state(fb[vline][hpos], 1));
			//HAL_GPIO_WritePin(VGA_BLUE_GPIO_Port, VGA_BLUE_Pin, vga_pixel_colour_state(fb[vline][hpos], 2));

			HAL_GPIO_WritePin(VGA_RED_GPIO_Port, VGA_RED_Pin, vga_pixel_colour_state(vga_get_pixel_from_buffer(hpos, vline), 0));
			HAL_GPIO_WritePin(VGA_GREEN_GPIO_Port, VGA_GREEN_Pin, vga_pixel_colour_state(vga_get_pixel_from_buffer(hpos, vline), 1));
			HAL_GPIO_WritePin(VGA_BLUE_GPIO_Port, VGA_BLUE_Pin, vga_pixel_colour_state(vga_get_pixel_from_buffer(hpos, vline), 2));

		} 
		
		if (hpos == HSIZE + 16) {
			// drop the hsync pin low
			HAL_GPIO_WritePin(VGA_HSYNC_GPIO_Port, VGA_HSYNC_Pin, GPIO_PIN_RESET);

		} 
		
		if (hpos == HSIZE + 16 + 96) {
			// bring hsync back up high
			HAL_GPIO_WritePin(VGA_HSYNC_GPIO_Port, VGA_HSYNC_Pin, GPIO_PIN_SET);

		}

		// increment the horizontal position
		hpos++;
		
		if (hpos == HSIZE + 16 + 96 + 48) {
			// the next horizontal position is beyond the line
			// start a new line
			hpos = 0;
			vline++;

			if (vline == VSIZE + 10 + 2 + 33) {
				// the next line is beyond the end of the frame
				// start a new frame
				vline = 0;
			}
		}
	}
}