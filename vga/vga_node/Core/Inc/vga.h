#ifndef __VGA_H
#define __VGA_H

/**
 * VGA Pinout
 * 
 * PA2  (D10)   -> VSYNC-BACK-PORCH
 * PA15 (D9)    -> VSYNC
 * 
 * PB1  (D6)    -> HSYNC-BACK-PORCH
 * PB4  (D5)    -> HSYNC
 * 
 * PXXX (DX)    -> RED
 * PXXX (DX)    -> GREEN
 * PXXX (DX)    -> BLUE
 */

/**
 * Initialise the VGA driver
 */
void vga_init(void);

#endif // __VGA_H