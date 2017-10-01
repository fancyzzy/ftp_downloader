#!/usr/bin/evn python


import Queue
import os
import time

LOG_FILE = os.path.join(os.getcwd(), 'my_ftp.log')
FTP_TIP_QUE = Queue.Queue()
print 'DEBUG FTP_TIP_QUE is created with id', id(FTP_TIP_QUE)

def printl(s):
	global LOG_FILE
	global FTP_TIP_QUE

	if 'unicode' in str(type(s)):
		s = s.encode('utf-8')

	FTP_TIP_QUE.put(s)
	print(s)
	#print ">>>after put s, mail size=",FTP_TIP_QUE.qsize()
	#time.sleep(0.4)

	try:
		with open(LOG_FILE, 'a') as fobj:
			fobj.write(s + '\n')
	except Exception as e:
		print "DEBUG wirte failed, e:",e
#########recode_log()#######################