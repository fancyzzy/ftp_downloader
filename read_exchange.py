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




'''
user_name = raw_input("input domain\\account:")
print("DEBUG username=",user_name)
pwd = raw_input("input password:")
#mail_addr = 'felix.zhang@alcatel-lucent.com'
mail_addr = raw_input("input mail address:")
'''
EXCHANGE_SERVER_ADD = 'CASArray.ad4.ad.alcatel.com'

tz = EWSTimeZone.timezone('UTC')
UTC_NOW = tz.localize(EWSDateTime.now()) - timedelta(hours=8)
print("DEBUG utc_now=",UTC_NOW)



user_name = 'ad4\\tarzonz'
pwd = 'CV_28763_10a'
mail_addr = 'felix.zhang@alcatel-lucent.com'

'''
credentials = Credentials(username=user_name, password=pwd)
config = Configuration(server= EXCHANGE_SERVER_ADD, credentials=credentials)
MY_ACC = Account(primary_smtp_address=mail_addr, config=config,
                     autodiscover=False, access_type=DELEGATE)
'''

#print(MY_ACC.root.tree())

class MY_OUTLOOK():
	def __init__(self, user_name, pwd, server_addr, mail_addr):
		global UTC_NOW

		credentials = Credentials(username=user_name, password=pwd)
		config = Configuration(server= EXCHANGE_SERVER_ADD, credentials=credentials)
		self.my_account = Account(primary_smtp_address=mail_addr, config=config, \
			autodiscover=False, access_type=DELEGATE)

		tz = EWSTimeZone.timezone('UTC')
		self.utc_time_point = UTC_NOW
	##########init()##############


	def find_mail(self, mail_subject_keyword):
		'''
		check the inbox and return
		a mail list that contains new mails subjects
		which received time is > the specific time
		'''
		print('Start find new mails...')
		print("DEBUG specific now_time =",self.utc_time_point)

		#mail_list = []
		my_inbox = self.my_account.inbox
		my_inbox.refresh()
		mail_number = my_inbox.total_count
		latest_mail =my_inbox.all().order_by('-datetime_received')[:1].next()

		if self.utc_time_point > latest_mail.datetime_received:
			print("No new mail..")
			yield None

		print("There are new mails received after this time point:",\
			self.utc_time_point)

		re_rule = re.compile(mail_subject_keyword, re.I)

		print("DEBUG start to find latest 10 mails")
		for item in my_inbox.all().order_by('-datetime_received')[:10]:
			d_rec = item.datetime_received
			subject = item.subject
			print("New mail Date:[%s], subject:[%s]" % (str(d_rec), subject))

			if re_rule.search(subject):
				print("keyword %s match!" % mail_subject_keyword)	
				yield item

			if self.utc_time_point > d_rec:
				break

		#update time to the checked latest mail's
		self.utc_time_point = latest_mail.datetime_received
	##############find_mail()################################

if __name__ == '__main__':

	'''
	print("total_count=",MY_ACC.inbox.total_count)
	mail_received_list = MY_ACC.inbox.all().order_by('-datetime_received')
	for item in MY_ACC.inbox.all().order_by('-datetime_received')[:1]:
		#print(item.subject, item.body, item.attachments)
		print("The latest mail subject:", item.subject)
		#print("The latest mail body:", item.body)
		#print("dir item=",dir(item))
		d_rec = item.datetime_received
		print("The latest mail received time:", d_rec)
		print("utc_now=",UTC_NOW)
		print(d_rec < UTC_NOW)

		html_str = item.body
		dr = re.compile(r'<[^>]+>',re.S)
		dd = dr.sub('',html_str)
		print
		print("After filter, dd=",dd)
	'''
	#timedelta = 8 means now, - 9 means 1 hour earlier
	UTC_NOW = tz.localize(EWSDateTime.now()) - timedelta(hours=9)
	print("DEBUG utc_now=",UTC_NOW)

	print("DEBUG start")
	my_o = MY_OUTLOOK(user_name, pwd, EXCHANGE_SERVER_ADD, mail_addr)
	print("initialized")
	mail_subject_keyword = '.*'
	for mail in my_o.find_mail(mail_subject_keyword):
		print("DEBUG new_mail subject = %s"%mail.subject)


	a  = raw_input('quit')
