#!/bin/bash

KERNEL_VERSION=$(uname -r | cut -d"-" -f1)
FULL_KERNEL_VERSION=$(uname -r)
cd /home/usbarmory/linux-$KERNEL_VERSION/
make clean
make -j4 M=drivers/usb/gadget/function modules
cp drivers/usb/gadget/function/usb_f_mass_storage.ko /lib/modules/$FULL_KERNEL_VERSION/kernel/drivers/usb/gadget/function/usb_f_mass_storage.ko
depmod