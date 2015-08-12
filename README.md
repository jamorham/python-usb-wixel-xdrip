# python-usb-wixel-xdrip
xDrip wixel connected via USB for "wifi" wixel mode

Python script intended for the Raspberry Pi allowing connection of an xdrip-wixel via USB

Emulates portions of the 'dexterity' android app so that the xDrip Android app can connect
to (multiple) raspberry pi receivers and pull in received data using the "wifi wixel" input
mode.

Using multiple wixel + pi receivers allows you to have full receiver coverage, for example, 
throughout a house without needing to be in-range of a portable wireless bridge or the 
classic receiver.

To be compatible, the wixel code needs to have a printf like this:

printf("%lu %lu %lu %hhu %d %hhu %d \r\n", pPkt->src_addr,dex_num_decoder(pPkt->raw),dex_num_decoder(pPkt->filtered)*2, pPkt->battery, getPacketRSSI(pPkt),pPkt->txId,adcConvertToMillivolts(adcRead(0)));

This printf is already present in https://github.com/jamorham/wixel-xDrip and you should
check that the config option allow_alternate_usb_protocol = 1 is set in the dexdrip.c file.

To connect to this script within the xDrip Android app, select Menu -> Settings -> Data
Collection Method -> Wifi Wixel

Then in the "List Of Receivers" setting, enter for example: 192.168.1.15:50005
(if you had a single pi receiver on your local network at address 192.168.1.15)

For multiple receivers you would enter comma delimited with no spaces, eg:

192.168.1.15:50005,192.168.1.16:50005

The sdcc compiler and wixel development tools + sdk can run fine on the Raspberry Pi. So it
is possible to develop everything directly on the Pi without needing to unplug the wixel 
which aids prototyping speed.

Script is provided "AS IS" without warranty of any kind, either expressed or implied,
including, but not limited to, the implied warranties of merchantability and fitness for a
particular purpose. The entire risk as to quality and performance is with the user.
