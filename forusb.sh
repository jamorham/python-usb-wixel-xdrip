#!/bin/sh -e
echo

if [ ! -f forusb.sh ]
then
echo "Not in the right folder, be in same folder as script and run: sh forusb.sh"
exit
fi

echo 
echo "This script will attempt to download and install the parakeet wixel firmware"
echo "in USB mode to a wixel attached to the USB port of this Raspberry Pi"
echo 
echo "There is an option to set the python script to auto-start and it will try to launch"
echo "the script after installation"
echo
echo "You will need internet access and know your dexcom G4 transmitter number"
echo
read -p "Do you want to proceed? y/n : " z
if [ "$z" = "Y" ] || [ "$z" = "y" ]
then
echo 
else
echo "Not proceeding.."
echo
exit
fi

if [ ! -f /usr/bin/sdcc ]
then
echo
echo "Installing recommended packages"
echo
sudo apt-get update && sudo apt-get -y install git screen python python-pycurl wget sdcc
echo
echo

fi

pw=`pwd`
if [ ! -s python-usb-wixel.py ]
then
echo "We do not appear to be in a folder containing python-usb-wixel.py"
echo
echo "Do you need to do: git clone https://github.com/jamorham/python-usb-wixel-xdrip.git "
echo
exit
fi

if [ ! -d wixel-xDrip ]
then
echo "Downloading wixel firmware"
git clone https://github.com/jamorham/wixel-xDrip
echo
fi

if [ ! -d wixel_linux ]
then
echo "Downloading wixel linux tools"
rm -f wixel-arm-linux-gnueabihf-150527.tar.gz
wget https://www.pololu.com/file/0J872/wixel-arm-linux-gnueabihf-150527.tar.gz
tar -xzvf wixel-arm-linux-gnueabihf-150527.tar.gz
fi

cd wixel-xDrip


echo "Configuring source code for USB use"
echo

read -p "Please enter your dexcom transmitter number, eg: ABCDE: " x

if [ ${#x} != 5 ]
then
echo "Transmitter ID wasn't 5 characters long, this looks wrong - exiting"
exit
fi

echo
echo "Reconfiguring..."

echo

if [ ! -f apps/dexdrip/dexdrip.orig ]
then
echo "Making backup to dexdrip.orig"
cat apps/dexdrip/dexdrip.c >apps/dexdrip/dexdrip.orig
else
echo "Restoring original from dexdrip.orig"
cat apps/dexdrip/dexdrip.orig >apps/dexdrip/dexdrip.c
fi

cat apps/dexdrip/dexdrip.c >apps/dexdrip/dexdrip.tmp
sed <apps/dexdrip/dexdrip.tmp >apps/dexdrip/dexdrip.c -e "s/ = \"ABCDE\";/ = \"${x}\";/g" -e "s/BIT use_gsm = 1;/BIT use_gsm = 0;/g"

echo
echo "Compiling wixel firmware: PLEASE WAIT"
echo
make

if [ -s apps/dexdrip/dexdrip.wxl ]
then
echo
echo "Firmware ready"
read -p "Install to USB attached wixel now? y/n : " y
if [ "$y" = "Y" ] || [ "$y" = "y" ]
then

sudo ../wixel_linux/wixelcmd list
sudo ../wixel_linux/wixelcmd write apps/dexdrip/dexdrip.wxl

echo

read -p "Make python script auto-start on Pi bootup? y/n : " y
if [ "$y" = "Y" ] || [ "$y" = "y" ]
then

if [ "`grep 'wixel python' /etc/rc.local`" = "" ]
then
echo
echo "Setting autostart in rc.local"
if [ ! -f rc.local.backup ]
then
sudo cat /etc/rc.local >rc.local.backup
echo "backup made rc.local.backup in local folder"
echo
fi
sudo grep -v '^exit 0' /etc/rc.local >/tmp/rc.local 
sudo echo -e "\n/usr/bin/screen -dmS wixel python \"$pw/python-usb-wixel.py\"\nexit 0" >>/tmp/rc.local
sudo cp /tmp/rc.local /etc/rc.local
sudo chmod a+rx /etc/rc.local
else
echo "Appears to already be enabled in rc.local"
fi
fi

echo
sleep 3

echo "Trying to start process.."
/usr/bin/screen -dmS wixel python "$pw/python-usb-wixel.py"
echo
screen -r wixel

else
echo "Not installing.."
exit
fi
else
echo "Firmware failed to build :("
exit
fi

