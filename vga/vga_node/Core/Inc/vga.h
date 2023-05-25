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
 * Call inside the DMA1 Channel 3 IRQ to handle the interrupt
 */
void vga_dma_ch3_irq(void);

/**
 * Call inside the DMA1 Channel 4 IRQ to handle the interrupt
 */
void vga_dma_ch4_irq(void);

/**
 * Clears the VGA screen
 */
void vga_clear_screen(void);

#endif // __VGA_H