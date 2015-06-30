#!/usr/bin/python

# jamorham 

# quick and dirty python script to emulate some of the function of 'dexterity'

# connect a wixel to usb and then set wifi-wixel feature in xdrip to point
# to the ip address of the host(s) running this script.

# intended for raspberry pi or other linux box

# wixel xdrip bridge needs to have output printf like this:

# printf("%lu %lu %lu %hhu %d %hhu %d \r\n", pPkt->src_addr,dex_num_decoder(pPkt->raw),dex_num_decoder(pPkt->filtered)*2, pPkt->battery, getPacketRSSI(pPkt),pPkt->txId,adcConvertToMillivolts(adcRead(0)));

# at time of writing the standard version uses a different printf which doesn't work with
# dexterity or this code. The full wixel sdk and sdcc work fine on the raspberry pi so the
# whole development of the wixel code can be done on the pi. 

# shell cmd to emulate client: 
# echo -e '{"numberOfRecords":1,"version":1}\n' | nc -w 3 127.0.0.1 50005

import json
import socket
import sys
import time
import os
from thread import *

import serial
 
HOST = ''   # All
PORT = 50005 # xdrip standard port


# output template

mydata = { "TransmitterId":"0","_id":1,"CaptureDateTime":0,"RelativeTime":0,"ReceivedSignalStrength":0,"RawValue":0,"TransmissionId":0,"BatteryLife":0,"UploadAttempts":0,"Uploaded":0,"UploaderBatteryLife":0,"FilteredValue":0 }


# threads

def serialthread(dummy):
	print "entering serial loop"
	global mydata
	while 1:
		try:

			# sometimes the wixel reboots and comes back as a different
			# device - this code seemed to catch that happening
			# more complex code might be needed if the pi has other
			# ACM type devices.

			if (os.path.exists("/dev/ttyACM0")):
				ser = serial.Serial('/dev/ttyACM0', 9600)
			if (os.path.exists("/dev/ttyACM1")):
				ser = serial.Serial('/dev/ttyACM1', 9600)

			serial_line = ser.readline()
		
				# debug print what we received
			print serial_line 
		
			# simple space delimited data records
			datax = serial_line.split(" ")
		
			# update dictionary - no sanity checking here

			mydata['CaptureDateTime']=str(int(time.time()))+"000"
			mydata['RelativeTime']="0"
			mydata['TransmitterId']=datax[0]
			mydata['RawValue']=datax[1]
			mydata['FilteredValue']=datax[2]
			mydata['BatteryLife']=datax[3]
			mydata['ReceivedSignalStrength']=datax[4]
			mydata['TransmissionId']=datax[5]

		except serial.serialutil.SerialException,e:
			print "Serial exception ",e
			time.sleep(1)
			
		ser.close() 
		time.sleep(6) 



# Create socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

print 'Socket created'
 
# Bind socket to local host and port

try:
    s.bind((HOST, PORT))
except socket.error as msg:
    print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
    sys.exit()
     
 
s.listen(10)

start_new_thread(serialthread,("",))


# socket thread
 
def clientthread(conn):

    while True:
		data = conn.recv(1024)
		reply = ''
		if not data: 
			break
		decoded = json.loads(data)     
		print json.dumps(decoded,sort_keys=True,indent=4)
		
		mydata['RelativeTime']=str((int(time.time())*1000)-int(mydata['CaptureDateTime']))

		if (mydata['RawValue']!=0):
			reply = reply + json.dumps(mydata) + "\n\n"
		else:
			print "we do not have any data to send yet"
		
		print reply

		conn.sendall(reply)
    conn.close()

# thread end
 
# main busy loop 
# wait for connections and start a thread

while 1:
    conn, addr = s.accept()
    print 'Connected with ' + addr[0] + ':' + str(addr[1])
     
    start_new_thread(clientthread ,(conn,))
 
s.close()
