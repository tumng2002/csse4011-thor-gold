#include <zephyr/shell/shell.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/usb/usb_device.h>
#include <zephyr/logging/log.h>

#include "vga_shell.h"

#define VGA_SHELL_THREAD_PRIORITY 1
#define VGA_SHELL_THREAD_STACK 500

LOG_MODULE_REGISTER(vga_node_shell);

/** 
 * Hello world command handler. Prints "Hello World!" to the shell
 */
static void cmd_hello_world(const struct shell *shell, size_t argc, char **argv) {
    ARG_UNUSED(argc);
    ARG_UNUSED(argv);

    shell_print(shell, "Hello World!\r\n");
}

/* ---- Register Commands ---- */

// register the hello_world command
SHELL_CMD_REGISTER(hello_world, NULL, "Print 'Hello World!'", cmd_hello_world);

/* ---- ---- */

/**
 * Init the VGA node shell system
 */
void init_vga_shell(void) {

    LOG_INF("Initialised the VGA shell");
}

/**
 * @brief Main thread for VGA node command line interface implementation.
 */
void vga_shell_thread(void) {
    const struct device *dev;
    uint32_t dtr = 0;

    dev = DEVICE_DT_GET(DT_CHOSEN(zephyr_shell_uart));
    if (!device_is_ready(dev)) {
        return;
    }

    while (!dtr) {
        uart_line_ctrl_get(dev, UART_LINE_CTRL_DTR, &dtr);
        k_sleep(K_MSEC(100));
    }

    while (1) {
        k_msleep(100);
    }
}

// create the base node shell thread
K_THREAD_DEFINE(vga_shell_thread_tid, VGA_SHELL_THREAD_STACK, vga_shell_thread, NULL, NULL, NULL, VGA_SHELL_THREAD_PRIORITY, 0, 0);