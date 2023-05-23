#ifndef __VGA_H
#define __VGA_H

/**
 * VGA Pinout
 * 
 * TIM2
 * PA2  (D10)   -> VSYNC-BACK-PORCH
 * PA15 (D9)    -> VSYNC
 * 
 * TIM3
 * PB1  (D6)    -> HSYNC-BACK-PORCH
 * PB4  (D5)    -> HSYNC
 * 
 * PA5  (D13)   -> RED
 * PA4  (D7)    -> GREEN
 * PXXX (DX)    -> BLUE
 */

/**
 * Initialise the VGA driver
 */
void vga_init(void);

#endif // __VGA_H