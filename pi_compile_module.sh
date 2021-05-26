#!/bin/bash

FULL_KERNEL_VERSION=$(uname -r)
cd /home/pi/linux/
make clean
make -j4 M=drivers/usb/gadget/function modules
cp drivers/usb/gadget/function/usb_f_mass_storage.ko /lib/modules/$FULL_KERNEL_VERSION/kernel/drivers/usb/gadget/function/usb_f_mass_storage.ko
depmod
