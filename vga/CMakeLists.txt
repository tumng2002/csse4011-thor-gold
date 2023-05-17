# Project VGA display node CMakeLists configuration
cmake_minimum_required(VERSION 3.20.0)

# always compile for the disco_l475_iot1 board
set(BOARD disco_l475_iot1)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(csse4011-thor-gold-vga)

# get the path to OSLIB
set(OSLIB_DIR ../oslib)

# get the required sources and includes from OSLIB
set(OSLIB_SRCS )
#include_directories(${OSLIB_DIR}/bsu_hci ${OSLIB_DIR}/bsu_shell ${OSLIB_DIR}/bsu_bt)

# sources and includes for the app
include_directories(inc)
target_sources(app PRIVATE src/main.c src/vga_driver.c ${OSLIB_SRCS})