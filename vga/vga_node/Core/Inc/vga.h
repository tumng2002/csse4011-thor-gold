#ifndef __VGA_H
#define __VGA_H

/**
 * VGA Pinout
 * 
 * TIM16 (80MHz counting to 3-1)
 * 
 * PB0  (D3)    -> VSYNC    (GPIO out)
 * PA3  (D4)    -> HSYNC    (GPIO out)
 * 
 * PB4  (D5)    -> RED      (GPIO out)
 * PB1  (D6)    -> GREEN    (GPIO out)
 * PA4  (D7)    -> BLUE     (GPIO out)
 */

#define VSIZE   480     /* Vertical resolution (in lines) */
#define HSIZE   640     /* Horizontal resolution (in pixels) */

#define BUFFER_VSIZE    240     /* Vertical resolution of the buffer (in lines) (VSIZE / 2) */
#define BUFFER_HSIZE    160     /* Horizontal resolution of the buffer (in pixels) (HSIZE / 4) */

/**
 * Initialise the VGA driver
 */
void vga_init(void);

/**
 * Clears the VGA screen
 */
void vga_clear_screen(void);

/**
 * Write a new frame to screen
 * 
 * @param frame a pointer to a new frame buffer of size BUFFER_VSIZE*BUFFER_HSIZE
 */
void vga_write_frame(uint8_t** frame);

/**
 * Write a new value to a pixel on the screen
 * 
 * @param pixel the new value of the pixel
 * @param x horizontal position of the pixel
 * @param y vertical position of the pixel
 */
void vga_write_pixel(uint8_t pixel, uint16_t x, uint16_t y);

/**
 * Display the colour test frame on the vga display
 */
void vga_display_test_frame(void);

#endif // __VGA_H