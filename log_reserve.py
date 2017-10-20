#!/usr/bin/evn python


import Queue
import os
import time
from datetime import datetime


FTP_SAVES = os.path.join(os.getcwd(),'my_ftp_saves')
if not os.path.exists(FTP_SAVES):
	os.mkdir(FTP_SAVES)

LOG_FILE = os.path.join(FTP_SAVES, 'my_ftp.log')
FTP_TIP_QUE = Queue.Queue()

def printl(s):
	global LOG_FILE
	global FTP_TIP_QUE

	if 'unicode' in str(type(s)):
		s = s.encode('utf-8')

	FTP_TIP_QUE.put(s)
	print(s)

	time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

	try:
		with open(LOG_FILE, 'a') as fobj:
			fobj.write(time_now +  ': ' + s + '\n')
	except Exception as e:
		print "DEBUG wirte failed, e:",e
#########recode_log()#######################