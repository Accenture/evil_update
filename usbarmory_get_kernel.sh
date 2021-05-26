#!/bin/bash

KERNEL_VERSION=$(uname -r | cut -d"-" -f1)

if [[ ! -f "/home/usbarmory/kernel.check" ]]
then
    # There is no kernel source
    #wget https://www.kernel.org/pub/linux/kernel/v5.x/linux-$KERNEL_VERSION.tar.xz -O /home/usbarmory/linux.tar.xz
    tar -xf /home/usbarmory/linux.tar.xz
    cp /boot/config-$(uname -r)-usbarmory /home/usbarmory/linux-$KERNEL_VERSION/.config
    cd /home/usbarmory/linux-$KERNEL_VERSION/
    make oldconfig
    make modules_prepare
    touch /home/usbarmory/kernel.check
fi