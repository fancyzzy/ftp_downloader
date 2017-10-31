#!/ust/bin/env python
#!-*-coding:utf-8-*-
from datetime import timedelta
from exchangelib import DELEGATE, IMPERSONATION, Account, Credentials, ServiceAccount, \
    EWSDateTime, EWSTimeZone, Configuration, NTLM, CalendarItem, Message, \
    Mailbox, Attendee, Q, ExtendedProperty, FileAttachment, ItemAttachment, \
    HTMLBody, Build, Version
#SSL certification
from exchangelib.protocol import BaseProtocol, NoVerifyHTTPAdapter
BaseProtocol.HTTP_ADAPTER_CLS = NoVerifyHTTPAdapter
#no warnings display warnings
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import re
import threading
from time import sleep
from log_reserve import printl


EXCHANGE_SERVER_ADD = 'CASArray.ad4.ad.alcatel.com'
tz = EWSTimeZone.timezone('UTC')
UTC_NOW = tz.localize(EWSDateTime.now())# - timedelta(hours=8)

user_name = 'ad4\\tarzonz'
pwd = 'CV_28763_10a'
mail_addr = 'felix.zhang@alcatel-lucent.com'


class MY_OUTLOOK():
	def __init__(self, acc, pwd, ser, mail):
		global UTC_NOW

		credentials = Credentials(username = acc, password = pwd)
		config = Configuration(server= ser, credentials = credentials)
		self.my_account = Account(primary_smtp_address = mail, config=config,\
			autodiscover = False, access_type = DELEGATE)

		tz = EWSTimeZone.timezone('UTC')
		self.utc_time_point = UTC_NOW
		print("Successfully accessed to exchange server. time:%s"%str(UTC_NOW))
		print("Server:{0}, Mail:{1}, Username{2}".format(ser,mail,acc))
	##########init()##############


	def find_mail(self, mail_subject_keyword):
		'''
		check the inbox and return
		a mail list that contains new mails subjects
		which received time is > the specific time
		'''
		print("Start to check new mail received after time: %s"%str(self.utc_time_point))

		#mail_list = []
		my_inbox = self.my_account.inbox
		my_inbox.refresh()
		mail_number = my_inbox.total_count
		latest_mail =my_inbox.all().order_by('-datetime_received')[:1].next()
		latest_mail_time = latest_mail.datetime_received + timedelta(hours=8)

		if self.utc_time_point >= latest_mail_time:
			print("No new mail..")
			yield None

		re_rule = re.compile(mail_subject_keyword, re.I)
		latest_ten = my_inbox.all().order_by('-datetime_received')[:10]
		for item in latest_ten:

			d_rec = item.datetime_received + timedelta(hours=8)
			if self.utc_time_point >= d_rec:
				break
			subject = item.subject

			if subject == None:
				subject = ''

			if re_rule.search(subject):
				printl("\nDetect a new mail, Date:[%s], subject:[%s]" % (str(d_rec), subject))
				yield item

		#update time to the checked latest mail's
		self.utc_time_point = latest_mail_time
	##############find_mail()################################


def test_start_monitor():
	global UTC_NOW
	global user_name
	global pwd
	global EXCHANGE_SERVER_ADD
	global mail_addr

	#pythoncom.CoInitialize()

	print("DEBUG test monitor start")
	my_ol = MY_OUTLOOK(user_name, pwd, EXCHANGE_SERVER_ADD, mail_addr)

	if my_ol:
		mail_subject_keyword = '.*'
		n = 0
		while 1:
			n += 1
			print(n)
			if n == 25:
				break

			for mail in my_ol.find_mail(mail_subject_keyword):
				#find ftp info
				if not mail:
					break
				else:
					print("mail(subject):",mail.subject)
					del_html = re.compile(r'<[^>]+>',re.S)
					plain_body = del_html.sub('',mail.body)
					#print("mail(body):",plain_body)
					full_ftp_re = r'ftp://(\w.*):(\w.*)@(\d{2,3}\.\d{2,3}\.\d{2,3}\.\d{2,3})(:\d*)?(/.*?\r)'
					res = re.search(full_ftp_re,plain_body)
					if res:
						print("\nftp info:",res.group(0))
					return
					pass

			print("debug 6 seconds interval... %d/20\n" % n)
			sleep(6)

	else:
		print("DEBUG my_ol is none")

	print("DEBUG quit")
	a = raw_input('input anything to quit this test>')

#########test_start_monitor()#######################


if __name__ == '__main__':

	print("DEBUG start main")
	#timedelta = 8 means now, - 9 means 1 hour earlier
	UTC_NOW = tz.localize(EWSDateTime.now()) - timedelta(hours=1)

	t = threading.Thread(target=test_start_monitor)
	t.start()		

	'''
	print("DEBUG start")
	my_o = MY_OUTLOOK(user_name, pwd, EXCHANGE_SERVER_ADD, mail_addr)
	print("initialized")
	mail_subject_keyword = '.*'

	for mail in my_o.find_mail(mail_subject_keyword):
		if mail:
			print("DEBUG get the new_mail with subject = %s" % mail.subject)
			print("debug type(mail) =",type(mail))
			print("debug dir(mail) =",dir(mail))
			break

	print("done")
	#a  = raw_input('quit')

	'''