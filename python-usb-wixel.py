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

# If you have more than one device you can use the remoteHosts list below to consolidate all of
# them to a single ip address

import json
import logging
import socket
import sys
import time
import os
from ConfigParser import SafeConfigParser
import platform
from urlparse import urlparse
import threading
import signal
import serial
import pycurl
from StringIO import StringIO
import re

if platform.system() != "Windows":
	import grp

	DEFAULT_LOG_FILE = "/tmp/python-usb-wixel.log"
else:
	DEFAULT_LOG_FILE = "python-usb-wixel.log"

HOST = ''  # All interfaces
PORT = 50005  # xdrip standard port

# Set a list of remote hosts in the format 192.168.1.50:50005, ... to consolidate
# multiple remote usb wixels or parakeet webservices to a single instance
# the script will poll the others for the latest data every 10 seconds.

remoteHosts = ""

# Set the parakeet url to your receiver.cgi url, eg https://your-parakeet-receiver.appspot.com/receiver.cgi
# and then all received data will be relayed to a parakeet app engine instance which is good for bypassing
# network address translation etc. App engine software is at: https://github.com/jamorham/Parakeet-App-Engine

parakeet_url = ""
parakeet_passcode = "12345"

# If you wired your wixel directly to the serial pins of the raspberry Pi set this to True
# for usb connected wixels leave it set as False

use_raspberry_pi_internal_serial_port = False

# Or you can store the configuration in a file which overrides whatever is set in this script

config = SafeConfigParser({'HOST': HOST,
						   'PORT': PORT,
						   'remoteHosts': remoteHosts,
						   'parakeet_url': parakeet_url,
						   'parakeet_passcode': parakeet_passcode,
						   'use_raspberry_pi_internal_serial_port': False,
						   'DEFAULT_LOG_FILE': DEFAULT_LOG_FILE})

# script should be python-usb-wixel.py and then config file will be python-usb-wixel.cfg
config_path = re.sub(r".py$", ".cfg", os.path.realpath(__file__))

if (os.path.isfile(config_path)):
	config.read(config_path)
	print "Loading configuration from: " + config_path
	HOST = config.get('main', 'HOST').strip()
	PORT = config.getint('main', 'PORT')
	remoteHosts = config.get('main', 'remoteHosts').strip()
	parakeet_url = config.get('main', 'parakeet_url').strip()
	parakeet_passcode = config.get('main', 'parakeet_passcode').strip()
	try:
		use_raspberry_pi_internal_serial_port = config.getboolean('main', 'use_raspberry_pi_internal_serial_port')
	except:
		use_raspberry_pi_internal_serial_port = False
	DEFAULT_LOG_FILE = config.get('main', 'DEFAULT_LOG_FILE').strip()
else:
	print "No custom config file: " + config_path

# remoteHosts is now specified as , separated string then converted to old style list
if (len(remoteHosts) > 0):
	remoteHosts = remoteHosts.split(',')
else:
	remoteHosts = []

# output template


mydata = {"TransmitterId": "0", "_id": 1, "CaptureDateTime": 0, "RelativeTime": 0, "ReceivedSignalStrength": 0,
		  "RawValue": 0, "TransmissionId": 0, "BatteryLife": 0, "UploadAttempts": 0, "Uploaded": 0,
		  "UploaderBatteryLife": 0, "FilteredValue": 0}


# threads

def serialThread(dummy):
	print "entering serial loop - waiting for data from wixel"
	global mydata
	while 1:
		try:

			# sometimes the wixel reboots and comes back as a different
			# device - this code seemed to catch that happening
			# more complex code might be needed if the pi has other
			# ACM type devices.

			if os.path.exists("/dev/ttyACM0"):
				ser = serial.Serial('/dev/ttyACM0', 9600)
			else:
				if os.path.exists("/dev/ttyACM1"):
					ser = serial.Serial('/dev/ttyACM1', 9600)
				else:
					if use_raspberry_pi_internal_serial_port and os.path.exists("/dev/ttyAMA0"):
						ser = serial.Serial('/dev/ttyAMA0', 9600)
					else:
						logger.error("Could not find any serial device")
						time.sleep(30)

			try:
				serial_line = ser.readline()

				# debug print what we received
				print serial_line
				serial_line = re.sub("[^0-9 \n-]", "", serial_line)
				logger.info("Serial line: " + serial_line.strip())

				# simple space delimited data records
				datax = serial_line.split(" ")

				if datax[0] == "\n":
					print "Detected loss of serial sync - restarting"
					logger.warning("Serial line error: " + serial_line)
					break

				# update dictionary - no sanity checking here

				mydata['CaptureDateTime'] = str(int(time.time())) + "000"
				mydata['RelativeTime'] = "0"
				mydata['TransmitterId'] = datax[0]
				mydata['RawValue'] = datax[1]
				mydata['FilteredValue'] = datax[2]
				mydata['BatteryLife'] = datax[3]
				mydata['ReceivedSignalStrength'] = datax[4]
				mydata['TransmissionId'] = datax[5]

				parakeet_upload()

			except Exception, e:
				print "Exception: ", e

		except serial.serialutil.SerialException, e:
			print "Serial exception ", e
			time.sleep(1)

		try:
			ser.close()
		except Exception, e:
			print "Serial close exception", e

		time.sleep(6)


# socket thread

def clientThread(connlocal):
	try:
		connlocal.settimeout(10)
		while True:
			data = connlocal.recv(1024)
			reply = ''
			if not data:
				break
			decoded = json.loads(data)
			print json.dumps(decoded, sort_keys=True, indent=4)

			mydata['RelativeTime'] = str((int(time.time()) * 1000) - int(mydata['CaptureDateTime']))

			if mydata['RawValue'] != 0:
				reply = reply + json.dumps(mydata) + "\n\n"
			else:
				print "we do not have any data to send yet"

			print reply

			connlocal.sendall(reply)
		connlocal.close()

	except Exception, e:
		print "Exception in clientThread: ", e


def consolidationThread():
	global mydata
	global remoteHosts
	print "Starting consolidationThread"
	while True:
		for host in remoteHosts:
			try:

				host = "//" + host  # must be cleaner way to do this
				remote_address = (urlparse(host).hostname, urlparse(host).port)
				# print "Trying: ",remote_address
				sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				sock.settimeout(5)  # could be longer if not on local network

				sock.connect(remote_address)

				sock.sendall("{\"numberOfRecords\":1,\"version\":1}\n")

				data = sock.recv(1024)

				decoded_data = json.loads(data)
				if (int(decoded_data['RelativeTime'])+100) < ((int(time.time()) * 1000) - int(mydata['CaptureDateTime'])):
					# print "Received NEWER: ",data
					print "NEWEST FROM: ", remote_address
					mydata = decoded_data
					parakeet_upload(ts=((int(time.time()) * 1000) - int(mydata['CaptureDateTime'])))

				sock.close()

			except Exception, e:
				print e, remote_address

		time.sleep(10)


def parakeet_upload(ts=1):
	global parakeet_url
	global mydata
	if parakeet_url != "":
		tries = 0
		max_tries = 2
		success = False
		while (success == False) and (tries < max_tries):
			tries = tries + 1
			buffer = StringIO()
			c = pycurl.Curl()
			c.setopt(pycurl.URL, parakeet_url
					 + "?"
					 + "&lv=" + mydata['RawValue']
					 + "&lf=" + mydata['FilteredValue']
					 + "&zi=" + mydata['TransmitterId']
					 + "&db=" + mydata['BatteryLife']
					 + "&gl=" + "-15,-15"
					 + "&pc=" + parakeet_passcode
					 + "&ts=" + str(ts)
					 )
			c.setopt(c.TIMEOUT, 20)
			c.setopt(c.USERAGENT, "usb-wixel")
			c.setopt(c.WRITEDATA, buffer)
			c.perform()
			rcode = c.getinfo(c.RESPONSE_CODE)
			rtime = c.getinfo(c.TOTAL_TIME)
			c.close()
			if (rcode == 200) and buffer.getvalue().startswith("!ACK"):
				print "Successfully Uploaded parakeet data in " + str(rtime) + "s"
				success = True
			else:
				logger.error(
					"Error uploading Parakeet data: Response code: " + str(rcode) + " time: " + str(rtime) + "s")
				logger.error("received reply: " + buffer.getvalue())
				time.sleep(10)


# threads end

# MAIN

# some init
if (platform.system() != "Windows"):
	if os.getuid() == 0:
		print "Dropping root"
		os.setgid(1000)  # make sure this user is in the dialout group or setgid to dialout
		try:
			os.setgid(grp.getgrnam("dialout").gr_gid)
		except:
			print "Couldn't find the dialout group to use"

		os.setuid(1000)
		print "Dropped to user: ", os.getuid()
		if os.getuid() == 0:
			print "Cannot drop root - exit!"
			sys.exit()

logger = logging.getLogger('python-usb-wixel')
hdlr = logging.FileHandler(DEFAULT_LOG_FILE)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.addHandler(logging.StreamHandler())

# choose your logging level as required

logger.setLevel(logging.INFO)
# logger.setLevel(logging.WARNING)

logger.info("Startup")

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

threading.Thread(target=serialThread, args=("",)).start()

if len(remoteHosts) > 0:
	t = threading.Thread(target=consolidationThread, args=()).start()

# main busy loop
# wait for connections and start a thread
try:
	print "Waiting for connections"

	while 1:
		conn, addr = s.accept()
		print 'Connected with ' + addr[0] + ':' + str(addr[1])

		threading.Thread(target=clientThread, args=(conn,)).start()
	s.close()

except KeyboardInterrupt:
	print "Shutting down"
	os.kill(os.getpid(), signal.SIGKILL)
