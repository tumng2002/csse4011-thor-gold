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
 * PA5  (D13)   -> RED      (DAC OUT1)
 * PA4  (D7)    -> GREEN    (DAC OUT2)
 * PXXX (DX)    -> BLUE
 */

/**
 * Initialise the VGA driver
 */
void vga_init(void);

/**
 * Call inside the VSYNC IRQ to handle the interrupt
 */
void vga_vsync_irq(void);

/**
 * Call inside the HSYNC IRQ to handle the interrupt
 */
void vga_hsync_irq(void);

/**
 * Clears the VGA screen
 */
vga_clear_screen(void);

#endif // __VGA_H