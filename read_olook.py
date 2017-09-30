#!/usr/bin/env python

from win32com.client import constants
from win32com.client.gencache import EnsureDispatch as Dispatch
import re
import time
import threading
MAPI = Dispatch("Outlook.Application").GetNamespace("MAPI")
print "DEBUG 6= ",MAPI.GetDefaultFolder(6)
import pythoncom
#New mails are to be checked after this time point
TIME_POINT = time.strftime('%m/%d/%y %H:%M:%S',time.localtime(time.time()))
#print "type TIME_POINT=",type(TIME_POINT)
#format as str '09/29/17 14:35:50'


def st_comp(s1, s2):
	'''
		>>> s1 = '09/29/17 14:35:50'
		>>> s2 = '09/29/17 14:42:23'
		>>> ts1 = time.strptime(s1,'%m/%d/%y %H:%M:%S')
		>>> ts2 = time.strptime(s2,'%m/%d/%y %H:%M:%S')
		>>> ts1 > ts2
		False
	'''
	ts1 = time.strptime(s1,'%m/%d/%y %H:%M:%S')
	ts2 = time.strptime(s2,'%m/%d/%y %H:%M:%S')
	return ts1 > ts2

class My_Outlook():
	def __init__(self):
		outlook = Dispatch("Outlook.Application")
		MAPI = outlook.GetNamespace("MAPI")
		self.my_outlook = MAPI.Folders
	##########init()##############


	def items(self):
		array_size = self.my_outlook.Count
		for item_index in xrange(1,array_size+1):
			yield (item_index, self.my_outlook[item_index])
	###########items()############


	def find_subfolder(self, subfolder_name):
		print "DEBUG find_folder starts"

		print "DEBUG self.my_outlook=",self.my_outlook
		array_size = self.my_outlook.Count
		re_rule = re.compile(subfolder_name, re.I)

		for idx, folder in self.items():
			print "folder name is ", folder.Name
			for subfolder in folder.Folders:
				if re_rule.search(subfolder.Name):
					print "find this folder!!!!:", subfolder.Name
					return subfolder
				else:
					continue
		return None
	#############find_subfolder()######


	def find_mail(self, subfolder, mail_subject_keyword):
		global TIME_POINT

		print 'DEBUG start find_mail'

		mail_number = subfolder.Items.Count
		strtime_latest_mail = str(subfolder.Items.Item(mail_number).SentOn)
		mail_list = []

		if not st_comp(strtime_latest_mail, TIME_POINT):
			print "DEBUT return out!"
			return mail_list


		print "type of latest mail =",type(strtime_latest_mail)

		re_rule = re.compile(mail_subject_keyword, re.I)

		print "Check new mails received after time point",TIME_POINT
		print "Filter with keyword:",mail_subject_keyword
		print "type(keyword)=",type(mail_subject_keyword)
		for i in range(mail_number, 0, -1):
			strtime_rcv = str(subfolder.Items.Item(i).SentOn)
			subject = subfolder.Items.Item(i).Subject
			print "DEBUG type(subject)",type(subject)
			print "DEBUG subject = ",subject
			print "strtime_rcv:{0}, TIME_POINT:{1}".format(strtime_rcv,TIME_POINT)
			if st_comp(strtime_rcv, TIME_POINT):
				print "New mail received, Date:%s, subject:[%s] = "\
				% (strtime_rcv, subject)
				if re_rule.search(subject):
					print "Find this mail!"
					mail_list.append(subject)
				else:
					print "not this one...."
			else:
				print "the first mail is not fresh, so quit"
				break

		#update time to the checked latest mail's
		if st_comp(strtime_latest_mail, TIME_POINT):
			TIME_POINT  = strtime_latest_mail

		print "DEBUG find_mail, mail_list=",mail_list

		return mail_list
	############find_mail()##############

#######Class My_Outlook###########################


def start_monitor():

	print "DEBUG2 thread name= ", threading.currentThread().getName()

	pythoncom.CoInitialize() 

	print "DEBUG thread start_monitor start"
	my_ol = My_Outlook()
	my_subfolder = my_ol.find_subfolder("inbox")
	print 'DEBUG my_subfolder=',my_subfolder

	TIME_POINT = '09/28/17 14:35:50'

	mail_list = []
	if my_subfolder:
		mail_list = my_ol.find_mail(my_subfolder, r"ftp")

	print "DEBUG mail_list = ",mail_list
##########start_monitor()############

if __name__ == '__main__':

	'''
	my_ol = My_Outlook()
	my_subfolder = my_ol.find_subfolder("inbox")
	print 'DEBUG my_subfolder=',my_subfolder

	TIME_POINT = '09/28/17 14:35:50'

	mail_list = []
	if my_subfolder:
		mail_list = my_ol.find_mail(my_subfolder, r"ftp")

	print "DEBUG mail_list = ",mail_list
	'''

	print "DEBUG1 thread name=", threading.currentThread().getName()
	t = threading.Thread(target=start_monitor)
	t.start()		
	#t.join()
	print "\nMain process continue.."
	