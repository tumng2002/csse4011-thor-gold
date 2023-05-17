/*
 * CSSE4011 Project
 * csse4011-thor-gold
 * VGA Node main.c
 * 
 * Nicholas Bassett
 */

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(vga_node);

void main(void) {

    LOG_INF("Starting up VGA node");

	printk("Hello World! %s\n", CONFIG_BOARD);

    

    LOG_INF("VGA node initialised");
}