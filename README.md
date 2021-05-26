# Evil_Update

## Theory behind 

### What it is?

This repository provides you with a script that will setup a [Raspberry Pi Zero](https://www.raspberrypi.org/products/raspberry-pi-zero-w/) or [USBArmory](https://inversepath.com/usbarmory.html) device to act as a malicious USB mass-storage device which will allow you to attack insecure update processes of your potential target devices. The flaw that this tool aims to exploit is a variant of Time-of-Check-Time-of-Use (TOC-TOU) attack when files are accessed on a USB stick (controlled by attacker). This attack is described in great detail [here](https://www.usenix.org/system/files/conference/woot12/woot12-final28.pdf).

### Why it works?

In general embedded systems are usually not known for an excessive amounts of storage and memory so the processes that are performed on these devices are usually taking this lack of resources into account. In case of possible USB updates this may result in developers deciding to first validate the signature of the data file on the USB stick and then process it (copy, unzip, etc.). Such approach may be susceptible to a TOC-TOU attacks as the lower amounts of memory will usually prevent the operating system from caching the contents of the data file into the memory and therefore, after validating the authenticity of the update package a window of opportunity exists for an attacker to swap the original file with a malicious version of it. This can result in a complete takeover of the compromised device as it may allow attacker to install arbitrary software components to the targeted device. 

### When it will not work?

There may be situations where this attack will not work or will have extremely limited impact. Those cases include but are not limited to:
* The device has enough memory to cache the whole data file and there is no way to trick the OS to flush the cache (see Attack Possibilities below)
* The data file is copied to internal storage and all operations (signature validation and applying the update) are performed from the locally stored copy of the file
* The order of loading separate manifest files and the data file does not allow you to perform tricks with clearing the page cache
* There is other "runtime" protection that will severely limit the impact of exploited issue (secure boot, runtime validation of signed applications, etc.)

### Attack Possibilities

#### Multiple Files (XML manifest)

When the signature is delivered in the separate file (XML in this case) there are various possibilities on how to force clearing of the page cache and thus make sure that the file is read from the beginning when it is accessed for the second time. First of all, signed XML files very often ignore comments when performing the signature validation (read more [here](https://www.w3.org/TR/xml-c14n.html)). Another point important for this exploitation is that XML parsing tends to be quite memory intensive task, so inserting sufficient amount of comments in the XML file allows you to exhaust most of the memory available on the device (use carefully though as the update process may crash due to lack of available memory). In cases where the canonicalization method is set to include comments, it will for sure ignore whitespace characters between element tags. Therefore, while not as effective as using comments which are by default parsed as XML elements, you can place sufficient amount of whitespace characters between various XML elements without the need to worry about braking the signature (in such case you may need to increase the size of the file to an extent which will be refused by the XML parser, this needs to be tried out as each device and parser combination will behave differently). Last but not least, signed XML document has to contain a section that holds teh signature. This section cannot be signed and thus is ideal candidate fo inserting dummy XML elements to consume the parser memory which is very helpful in clearing the OS page cache.

#### Multiple Files (S/MIME manifest)

The S/MIME styled manifest files work by including the data in a portion of the file which is signed while the rest of the file is not. You can use whitespace characters in the start of the file to fill the page cache and cause a second read of the file. Unfortunately, unlike with the XML example the parsing itself does not take that much RAM so you will have to pad a lot.

#### Single file

In a lot of cases the signature is either prepended or appended to the file, this is a little problematic as you cannot really manipulate with the file size without invalidating the signature. However, if the file is larger than the available RAM at the time of update, it will work too.

## Setup

## USBArmory

First make sure that you do initial setup of the USBArmory device. The USBArmory Mk.II has 16GB internal eMMC storage. After installing the OS this will result in approximately `14GB` of usable space. This means that you can use this storage for monitoring accesses to files with size of approximately `14GB` and in attack mode for disk images with up to `7GB` size. If you need to work with larger files use the SD card with sufficient capacity, it is important to keep in mind that using eMMC storage is about 50% faster on read speeds vs Samsung EVO cards (I have not tested the extremely expensive cards).

When setting up the eMMC storage you first need to follow [these instructions](https://github.com/f-secure-foundry/usbarmory-debian-base_image/blob/master/README.md#accessing-the-usb-armory-mk-ii-internal-emmc-as-usb-storage-device) to expose the eMMC to your laptop as a mass-storage device. When done you just `dd` the downloaded image to the corresponding device as mentioned [here](https://github.com/f-secure-foundry/usbarmory-debian-base_image/blob/master/README.md#installation) (and as you would when setting up a bootable SD card). After that you should be able to login to the device as described [here](https://github.com/f-secure-foundry/usbarmory-debian-base_image/blob/master/README.md#connecting).

After you complete the initial installation step it is necessary to expand the default partition to the whole available space. This is very easy process that is demonstrated [here](https://elinux.org/Beagleboard:Expanding_File_System_Partition_On_A_microSD)

The only custom thing you need to do is to install necessary packages to allow building of the custom kernel modules. First, it is required that you provide internet connectivity to the USBArmory. Exact steps on how to do this for all major OSes are shown in [this guide](https://github.com/f-secure-foundry/usbarmory/wiki/Host-communication#cdc-ethernet). When done install any pending OS updates (reboot in case of kernel update) and then run this command to install necessary packages: `sudo apt install build-essential bc kmod cpio flex libncurses5-dev libelf-dev libssl-dev xz-utils bison`

From this point on, the USBArmory no longer needs to have access to the internet and is ready for the configuration.

## Raspberry Pi Zero

You will need a Raspberry Pi Zero and a fast micro SD card. First do the initial setup of the Raspberry Pi OS (Lite version is strongly suggested) as per [standard process](https://www.raspberrypi.org/documentation/installation/installing-images/). Setup [SSH](https://www.raspberrypi.org/documentation/remote-access/ssh/README.md) and `hostapd` ([here](https://www.raspberrypi.org/documentation/configuration/wireless/access-point-routed.md)) or `wpa_supplicant` ([here](https://www.raspberrypi.org/documentation/configuration/wireless/headless.md)) as per your requirements and make sure that you have a working base installation of Raspberry Pi OS with internet connectivity and a user with `sudo` access without password. That is all that is required as the remainder of the setup will be automatically performed by the script itself (note that the Pi needs to have Internet connectivity).


## Monitor mode

The `monitor` mode of this tool sets the device which was pre-configured using the previous steps with ability to log all events where the file was accessed to the `/var/log/syslog` or `dmesg` output. To use this mode prepare the contents of the USB that you would like to use in a ZIP file (`content.zip` for example) and simply run the `evil_update.py` script with `sudo`, device type as first argument and `monitor` as the second argument (`sudo ./evil_update.py <pizero|usbarmory> monitor`) the script will guide you through the setup process.
For the ease of access on USBArmory, it is recommended to flash both eMMC and SD Card with bootable images. You can always access the booted system from the other OS which is just a simple flip of a switch away. That way you can easily read data from the script by grepping the `/var/log/syslog` file for `EVIL_UPDATE` keyword.

## Attack mode

The `attack` mode is in essence very similar to the `monitor` mode. You can run the device preparation with `sudo ./evil_update.py <pizero|usbarmory> attack` and the script will ask you three more questions as compared to the `monitor` option. The first question related to `attack` mode will be related to the file that is about to be replaced where you should put the path to the file within the unpacked content (`./contents/<your_input>`). The second question will prompt you to supply the path to the *evil* file which will be used as a malicious replacement (and has to be exactly the same size as original!). By answering the last question you can specify on which read the file should be replaced. In the simplified sample scenarios provided in this repository that will always be `2` as the file is read for the first time for signature validation and for second time for the copy operation. The actual number may vary depending on the conditions you will be facing and it is strongly suggested to use the `monitor` mode to figure out correct number.