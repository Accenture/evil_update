#!/bin/bash

if [[ ! -f "/home/pi/kernel.check" ]]
then
    # There is no kernel source
    git clone --depth=1 https://github.com/raspberrypi/linux
    cd /home/pi/linux/
    KERNEL=kernel
    make bcmrpi_defconfig
    make modules_prepare
    touch /home/pi/kernel.check
fi
