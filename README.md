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

The sdcc compiler and wixel development tools + sdk can run fine on the Raspberry Pi. So it
is possible to develop everything directly on the Pi without needing to unplug the wixel 
which aids prototyping speed.
