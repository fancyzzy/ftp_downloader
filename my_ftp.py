#!/usr/bin/env python
#!--*--coding:utf-8--*-

from Tkinter import *
import ttk
from tkMessageBox import *

import ftplib
import os
import socket
import threading
import cPickle as pickle
import collections
import threading
import Queue
#change method of getting mails from win32com to exchangelib
#import read_olook
#import pythoncom 
import read_exchange
from log_reserve import *
import time
import datetime
import tooltip
import ctypes
import inspect


HOST = '135.242.80.16'
PORT = '8080'
DOWNLOAD_DIR = '/01_Training/02_PMU/02_Documents'
ACC = 'QD-BSC2'
PWD = 'qdBSC#1234'
SAVE_DIR = os.path.join(os.getcwd(),'ftp_download')
if not os.path.exists(SAVE_DIR):
	os.mkdir(SAVE_DIR)
CONN = None
DATA_BAK_FILE = os.path.join(SAVE_DIR, "my_ftp.pkl")
MAIL_KEYWORD = r'\d-\d{7}\d*'
#MAIL_KEYWORD = '1-6853088'
MONITOR_INTERVAL = '6'
MY_FTP = collections.namedtuple("MY_FTP",\
 "host port user pwd target_dir mail_keyword interval")

#outlook config
EXSERVER = 'CASArray.ad4.ad.alcatel.com'
MAIL_ADD = 'xxx.yy@nokia-sbell.com'
AD4_ACC = 'ad4\\xxx'
AD4_PWD = ''
MY_OLOOK = collections.namedtuple("MY_OLOOK", "server mail user pwd")


#all the data to be backup
DATA_BAK = collections.namedtuple("DATA_BAK", "ftp_bak ol_bak")

AUTOANA_ENABLE = False
MONITOR_THREADS = []
MONITOR_STOP = True
MONITOR_REC = collections.namedtuple("M_REC", "index time subject ftp download_file")
MONITOR_REC_FILE = os.path.join(SAVE_DIR, "monitor_history.txt")
MONITOR_REC_LIST = []
MONITOR_REC_LIST.append(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
IS_FIND = False

DOWNLOADER_ICON = os.path.join(os.path.join(os.getcwd(), "resource"),'mail.ico')

file_number = 0
dir_number = 0
downloaded_number = 0

ASK_QUIT = False

FTP_FILE_QUE = Queue.Queue()


def save_bak():
	ftp_bak = MY_FTP(HOST, PORT, ACC, PWD, DOWNLOAD_DIR, MAIL_KEYWORD, MONITOR_INTERVAL)
	ol_bak = MY_OLOOK(EXSERVER, MAIL_ADD, AD4_ACC, AD4_PWD)
	data_bak = DATA_BAK(ftp_bak, ol_bak)
	printl("Save data_bak: {}".format(data_bak))
	pickle.dump(data_bak, open(DATA_BAK_FILE,"wb"), True)
############save_bak()#####################


def retrive_bak():
	#change method of getting mails from win32com to exchangelib
	#printl('\n'+read_olook.TIME_POINT)
	printl('Welcome to Ftp Monitor------------------------')
	try:
		data_bak = pickle.load(open(DATA_BAK_FILE, "rb"))
		printl("Retrive data_bak:{}".format(data_bak))

		HOST = data_bak.ftp_bak.host
		PORT = data_bak.ftp_bak.port
		ACC = data_bak.ftp_bak.user
		PWD = data_bak.ftp_bak.pwd
		DOWNLOAD_DIR = data_bak.ftp_bak.target_dir
		MONITOR_INTERVAL = data_bak.ftp_bak.interval

		EXSERVER = data_bak.ol_bak.server
		MAIL_ADD = data_bak.ol_bak.mail
		AD4_ACC = data_bak.ol_bak.user
		AD4_PWD = data_bak.ol_bak.pwd

	except Exception as e:
		printl("ERROR occure, e= %s" %e)

	else:
		printl("Retrive success!\n")
		return data_bak	
	return None
############retrive_bak()###################


#terminate threads
def _async_raise(tid, exctype):
		"""raises the exception, performs cleanup if needed"""
		tid = ctypes.c_long(tid)
		if not inspect.isclass(exctype):
			exctype = type(exctype)
		res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
		if res == 0:
			raise ValueError("invalid thread id")
		elif res != 1:
			# """if it returns a number greater than one, you're in trouble,
			# and you should call it again with exc=NULL to revert the effect"""
			ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
			raise SystemError("PyThreadState_SetAsyncExc failed")

def terminate_threads(l_threads):
	'''
	强制终止线程
	'''
	print "DEBUG start terminate threads: {}".format(l_threads)
	if l_threads:
		for t in l_threads:
			if t.is_alive():
				_async_raise(t.ident, SystemExit)
	#clear the thread list
	l_threads[:] = []
	print "terminate threads done"
################terminate_threads()##########################


FTP_INFO = collections.namedtuple("FTP_INFO", "HOST PORT ACC PWD DIRNAME")

def extract_ftp_info(s):
	'''
	from the string s to find the first ftp format string
	return 'ftp://QD-BSC2:qdBSC#1234@135.242.80.16:8080/01_Training/02_PMU/02_Documents'
	'''
	print("Debug start extract_ftp_info")
	ftp_re = r'ftp://(\w.*):(\w.*)@(\d{2,3}\.\d{2,3}\.\d{2,3}\.\d{2,3})(:\d*)?(/.*)'
	res = re.search(ftp_re,s)

	if res:
		acc = res.group(1)
		pwd = res.group(2)
		host = res.group(3)
		port = res.group(4)
		# '.'will match any character except '\n' so the last 
		#character is '\r' and use [:-1] to slice off it
		dirname = res.group(5).strip(r'\r')

		if not port:
			port = '21'
		else:
			port = port[1:]

		if acc and pwd and host and port and dirname:
			ftp_info = FTP_INFO(host, port, acc, pwd, dirname)
			print("DEBUG ftp info found: %s" % ''.join(ftp_info))
			return ftp_info
		else:
			print("DEBUG error, some ftp info is none")
			return None
	else:
		return None
###########extract_ftp_info()################


def ftp_conn(host, port, acc, pwd):
	global CONN

	printl('Ftp connecting start, host:{0}, port:{1}, acc:{2}, pwd:{3}'\
		.format(host,port,acc,pwd))

	try:
		CONN = ftplib.FTP()
		CONN.connect(host, port)
	except (socket.error, socket.gaierror), e:
		printl('ERROR: cannot reach host "%s", exited.' % host)
		return False
	printl('*** Successfully connected to host "%s"'% host)

	try:
		CONN.login(acc, pwd)
	except ftplib.error_perm:
		printl('ERROR: cannot login as "%s", exited.' % acc)
		CONN.quit()
		return False
	printl('*** Successfully logged in as "%s"' % acc)

	return True
############ftp_conn()#####################


def ftp_download_dir(dirname):
	global downloaded_number

	printl('Download start, dirname = %s' % dirname)
	try:
		CONN.cwd(dirname)
	except ftplib.error_perm:
		printl('ERROR: cannot cd to "%s"' % dirname)
	else:
		#printl("change diretocry into %s..." %dirname)
		new_dir = os.path.basename(dirname)
		if not os.path.exists(new_dir):
			os.mkdir(new_dir)

		os.chdir(new_dir)

		filelines = []
		CONN.dir(filelines.append)
		filelines_bk = CONN.nlst()
		i = 0
		for file in filelines:
			#<DIR> display in widows and dxxx in linux
			if '<DIR>' in file or file.startswith('d'):
				ftp_download_dir(filelines_bk[i])
				CONN.cwd('..')
				os.chdir('..')
				#print("back to upper directory to download....")
			else:
				try:
					CONN.retrbinary('RETR %s' % filelines_bk[i], \
						open(filelines_bk[i], 'wb').write)
				except ftplib.error_perm:
					printl('ERROR: cannot read file "%s"' % file)
					os.unlink(file)
				else:
					downloaded_number += 1
					printl("File %s has been downloaded!" % filelines_bk[i])
			i += 1
##################download_dir()###############

def get_file_number(dirname):
	global file_number
	global dir_number
	global CONN

	try:
		CONN.cwd(dirname)
	except ftplib.error_perm:
		printl('ERROR: cannot cd to "%s"' % dirname)
		return None
	else:
		new_dir = os.path.basename(dirname)
		if not os.path.exists(new_dir):
			os.mkdir(new_dir)
		os.chdir(new_dir)
		filelines = []
		CONN.dir(filelines.append)
		filelines_bk = CONN.nlst()
		i = 0
	
		for file in filelines:
			if '<DIR>' in file:
				dir_number += 1
				get_file_number(filelines_bk[i])
				CONN.cwd('..')
			else:
				file_number += 1
			i += 1

	return dir_number, file_number
#############get_file_number()###############


def my_download(host, port, acc, pwd, save_dir, download_dir):
	global downloaded_number
	global CONN

	#if this file had been downloaded, quit
	down_name = os.path.basename(download_dir)

	printl("my_download starts")
	if os.path.exists(os.path.join(save_dir,down_name)):
		printl("file already exsit:%s"% os.path.join(save_dir,down_name))
		return None

	os.chdir(save_dir)

	if not ftp_conn(host, port, acc, pwd):
		return None

	printl("Calculating the download files number...")
	m,n = get_file_number(download_dir)
	if m == None:
		return None
	printl("Total %d files, %d folders to be downloaded" % (n, m))
	ftp_download_dir(download_dir)
	CONN.quit()

	if n == downloaded_number:
		printl("All files in {} have been downloaded successfully!".\
			format(download_dir))

	return os.path.join(save_dir,os.path.basename(download_dir))
#############my_download()########


def ftp_upload_file(file_path, remote_path):
	global CONN	

	printl('Ftp upload start, file_name:{0}, destination:{1}'\
		.format(file_path,remote_path))

	bufsize = 1024
	fp = open(file_path, 'rb')

	try:
		CONN.storbinary('STOR ' + remote_path, fp, bufsize)
	except Exception as e:
		printl("error when uploading, e={}".format(e))
		return False

	fp.close()
	return True
##################ftp_upload_file()###############


def my_upload(host, port, acc, pwd, file_path, remote_path):
	global CONN

	if not ftp_conn(host, port, acc, pwd):
		return False

	if not ftp_upload_file(file_path, remote_path):
		printl('Upload error, exited')
		return False
	else:
		printl("Upload file {} successfully!".format(remote_path))
		return True
#####################my_upload()###################


class My_Ftp(object):
	def __init__(self, parent_top):
		global HOST
		global PORT
		global ACC
		global PWD
		global DOWNLOAD_DIR

		global EXSERVER
		global MAIL_ADD
		global AD4_ACC
		global AD4_PWD
		
		self.parent_top = parent_top
		self.ftp_top = Toplevel(parent_top)
		self.ftp_top.title("Outlook Monitor")
		self.ftp_top.geometry('600x330+300+220')
		self.ftp_top.iconbitmap(DOWNLOADER_ICON)
		#self.ftp_top.attributes("-toolwindow", 1)
		#self.ftp_top.wm_attributes('-topmost',1)
		self.ftp_top.protocol("WM_DELETE_WINDOW",lambda :self.ask_quit(self.ftp_top))
		self.running = True

		blank_label_1 = Label(self.ftp_top, text = '').pack()
		self.pwindow_qconn = ttk.Panedwindow(self.ftp_top, orient=VERTICAL)

		self.lframe_qconn = ttk.Labelframe(self.ftp_top, text='Direct Download',\
		 width= 620, height = 220)
		self.lframe_autoconn = ttk.Labelframe(self.ftp_top, text='Auto Download',\
		 width= 620, height = 220)
		#self.lframe_outacc = ttk.Labelframe(self.ftp_top, text='Outlook Account',\
		# width= 620, height = 420)
		self.pwindow_qconn.add(self.lframe_qconn)
		self.pwindow_qconn.add(self.lframe_autoconn)
		#self.pwindow_qconn.add(self.lframe_outacc)

		#Host label and entry
		self.label_host = Label(self.lframe_qconn, text = 'Host:').grid(row=0,column=0)
		self.v_host = StringVar()
		self.entry_host = Entry(self.lframe_qconn, textvariable=self.v_host,width=20)
		self.entry_host.grid(row=0,column=1)
		ts ="Input a ftp format, for example:\n ftp://QD-BSC2:qdBSC#1234@135.242.80.16:8080/01_Training/02_PMU/02_Documents\n then click 'Direct download' to download files in this directory"
		tooltip.ToolTip(self.entry_host, msg=None, msgFunc=lambda : ts, follow=True, delay=0.2)

		#Port label and entry
		self.label_port = Label(self.lframe_qconn, text = '   Port:').grid(row=0,column=2)
		self.v_port = StringVar()
		self.entry_port = Entry(self.lframe_qconn, textvariabl=self.v_port, width=20)
		self.entry_port.grid(row=0,column=3)

		#Usrnamer label and entry
		self.label_user = Label(self.lframe_qconn, text = '   Username:').grid(row=1,column=0)
		self.v_user = StringVar()
		self.entry_user = Entry(self.lframe_qconn, textvariabl=self.v_user, width=20)
		self.entry_user.grid(row=1,column=1)

		#Password label and entry
		self.label_pwd = Label(self.lframe_qconn, text = '   Password:').grid(row=1,column=2)
		self.v_pwd = StringVar()
		self.entry_pwd = Entry(self.lframe_qconn, textvariabl=self.v_pwd, width=20)
		self.entry_pwd.grid(row=1,column=3)

		#Download dirname
		self.label_ddirname = Label(self.lframe_qconn, text = 'Dirname:').grid(row=2,column=0)
		self.v_ddirname = StringVar()
		self.entry_ddirname = Entry(self.lframe_qconn, textvariabl=self.v_ddirname, width=40)
		self.entry_ddirname.grid(row=2,column=1)

		#Download button
		self.button_qconn = Button(self.lframe_qconn,text="Direct dowload",\
			width=20, command=self.thread_ftp, activeforeground='white', \
			activebackground='orange',bg = 'white', relief='raised')
		self.button_qconn.grid(row=2,column=3)

		#############Auto download###############

		self.fm_up = Frame(self.lframe_autoconn)
		s1 = "Monitor 'Inbox' to automatically download files"
		s2 = " "
		s3 ="based on ftp information in mail with specified title"
		s = s1+s2+s3
		self.v_chk = BooleanVar() 
		self.chk_auto = Checkbutton(self.fm_up, text = s, variable = self.v_chk,\
			command = self.periodical_check)
		self.chk_auto.pack()
		self.fm_up.pack()

		self.fm_config = Frame(self.lframe_autoconn,height=50)

		#exchange serveHost label and entry
		self.label_exserver = Label(self.fm_config, text = 'Exchange Server:')
		self.label_exserver.grid(row=0,column=0)
		self.v_exserver = StringVar()
		self.entry_exserver = Entry(self.fm_config, textvariable=self.v_exserver,width=27)
		self.entry_exserver.grid(row=0,column=1)

		#Mail Address label and entry
		self.label_mail_add = Label(self.fm_config, text = '  Mail Address:')
		self.label_mail_add.grid(row=0,column=2)	
		self.v_mail_k_add = StringVar()
		self.entry_mail_add = Entry(self.fm_config, textvariabl=self.v_mail_k_add, width=29)
		self.entry_mail_add.grid(row=0,column=3)

		#Domain//Usrnamer label and entry
		self.label_csl = Label(self.fm_config, text = 'Domain/CSL:',justify = LEFT)
		self.label_csl.grid(row=1,column=0)
		self.v_csl = StringVar()
		self.entry_csl = Entry(self.fm_config, textvariabl=self.v_csl, width=27)
		self.entry_csl.grid(row=1,column=1)

		#CIP Password label and entry
		self.label_cip = Label(self.fm_config, text = '  AD4 Password:')
		self.label_cip.grid(row=1,column=2)
		self.v_cip = StringVar()
		self.entry_cip = Entry(self.fm_config, show = "*",textvariabl=self.v_cip, width=29)
		self.entry_cip.grid(row=1,column=3)

		#mail title keyword
		self.label_mail_k = Label(self.fm_config, text = 'Mail Title Keyword:')
		self.label_mail_k.grid(row=2,column=0)
		self.v_mail_k = StringVar()
		self.entry_mail_k = Entry(self.fm_config, textvariable=self.v_mail_k,width=27)
		self.entry_mail_k.grid(row=2,column=1)
		ts ="Refer to the Python regular expression"
		tooltip.ToolTip(self.entry_mail_k, msg=None, msgFunc=lambda : ts, follow=True, delay=0.2)


		self.label_interval = Label(self.fm_config,text= 'Monitor Interval(sec):')
		self.label_interval.grid(row=2,column=2)
		self.v_interval = StringVar()
		self.interval_count = 0
		self.spin_interval = Spinbox(self.fm_config, textvariable=self.v_interval,\
			width = 8, from_=1, to=8640,increment=1)
		self.spin_interval.grid(row=2,column=3)	

		self.fm_config.pack()

		self.fm_mid = Frame(self.lframe_autoconn, height=50)
		#button trigger monitor mails' titles
		self.button_monitor = Button(self.fm_mid, text="Start monitor",\
		 command=self.start_thread_monitor, activeforeground\
		='white', activebackground='orange',bg = 'white', relief='raised', width=20)
		self.button_monitor.pack()#grid(row=1,column=3)
		self.fm_mid.pack()
		#for read exchanger configuration

		self.pwindow_qconn.pack()

		self.label_blank11 = Label(self.ftp_top,text= '  '*3).pack(side=LEFT)
		self.v_tip = StringVar()
		self.label_tip = Label(self.ftp_top,textvariable=self.v_tip).pack(side=LEFT)
		#GUI finish

		#######retrive data from disk#############:
		data_bak = retrive_bak()
		if data_bak:

			self.v_host.set(data_bak.ftp_bak.host)
			self.v_port.set(data_bak.ftp_bak.port)
			self.v_user.set(data_bak.ftp_bak.user)
			self.v_pwd.set(data_bak.ftp_bak.pwd)
			self.v_ddirname.set(data_bak.ftp_bak.target_dir)
			self.v_mail_k.set(data_bak.ftp_bak.mail_keyword)
			#print("DEBUG self.v_mail_k = ",self.v_mail_k.get())
			self.v_interval.set(data_bak.ftp_bak.interval)

			self.v_exserver.set(data_bak.ol_bak.server)
			self.v_mail_k_add.set(data_bak.ol_bak.mail)
			self.v_mail_k_add.set(data_bak.ol_bak.mail)
			self.v_csl.set(data_bak.ol_bak.user)
			self.v_cip.set(data_bak.ol_bak.pwd)
		else:
			self.v_host.set(HOST)
			self.v_port.set(PORT)
			self.v_user.set(ACC)
			self.v_pwd.set(PWD)
			self.v_ddirname.set(DOWNLOAD_DIR)	
			self.v_mail_k.set(MAIL_KEYWORD)
			self.v_interval.set(MONITOR_INTERVAL)

			self.v_exserver.set(EXSERVER)
			self.v_mail_k_add.set(MAIL_ADD)
			self.v_csl.set(AD4_ACC)
			self.v_cip.set(AD4_PWD)
		#######retrive data from disk#############:
		self.periodical_check()

		self.t_tip = threading.Thread(target=self.start_progress_tip)
		self.t_tip.start()

		
		##############init()###############

	def start_progress_tip(self):
		global FTP_TIP_QUE 
		global ASK_QUIT

		print "start_progress_tip begin!"
		while 1:
			try:
				s = FTP_TIP_QUE.get(False)
				self.v_tip.set(s)
			except Exception as e:
				#print("queue is empty, e %s" % e)
				pass

			time.sleep(0.4)

			if ASK_QUIT and FTP_TIP_QUE.empty():
				self.v_tip.set("Exited..")
				break
		print "start_progress_tip done!"

	########start_progess_tip###########


	def thread_ftp(self):

		self.button_qconn.config(text="Please wait",bg='orange',relief='sunken',state='disabled')
		
		t = threading.Thread(target=self.direct_download)
		#l_threads.append(t)
		t.start()
	##########thread_ftp()###################
	

	def direct_download(self):
		global HOST
		global PORT
		global ACC
		global PWD
		global SAVE_DIR
		global DOWNLOAD_DIR
		printl("Direct_download starts")

		#extract ftp info
		if self.v_host.get():
			ftp_info = extract_ftp_info(self.v_host.get())
			#FTP_INFO = collections.namedtuple("FTP_INFO", "HOST PORT ACC PWD DIRNAME")
			if ftp_info:
				self.v_host.set(ftp_info.HOST)
				self.v_port.set(ftp_info.PORT)
				self.v_user.set(ftp_info.ACC)
				self.v_pwd.set(ftp_info.PWD)
				self.v_ddirname.set(ftp_info.DIRNAME)

		if self.v_host.get():
			HOST = self.v_host.get()
		if self.v_port.get():
			PORT = self.v_port.get()
		if self.v_user.get():
			ACC = self.v_user.get()
		if self.v_pwd.get():
			PWD = self.v_pwd.get()
		if self.v_ddirname.get():
			DOWNLOAD_DIR = self.v_ddirname.get()

		file_saved = ''
		file_saved = my_download(HOST, PORT, ACC, PWD, SAVE_DIR, DOWNLOAD_DIR)

		if not file_saved:
			printl("Download Error: cannot access or file already exists or download dir not exsits.")
			#crash
			#showerror(title='Ftp Connect Error', message="Cannot accesst to %s" % HOST)
		else:
			printl("Downloaded success and saved in dir: %s" % \
				file_saved)

			#change method of getting mails from win32com to exchangelib
			if AUTOANA_ENABLE:
				#send to queue for other processing, e.g.,auto search in listdir.py
				print("DEBUG my_ftp.py send %s to auto analyse" % file_save)
				FTP_FILE_QUE.put(file_saved)

		self.button_qconn.config(text="Direct download",bg='white',relief='raised',state='normal')

		return file_saved
	##############direct_download()##################

	#revise with read_exchange
	def start_monitor(self, mail_keyword):
		global MONITOR_REC_LIST
		global MONITOR_REC_FILE
		global IS_FIND

		#change method of getting mails from win32com to exchangelib
		#pythoncom.CoInitialize() 
		self.interval_count = 0

		find_folder = "inbox"
		try:
			#change method of getting mails from win32com to exchangelib
			#my_ol = read_olook.My_Outlook()
			#def __init__(self, acc, pwd, ser, mail)
			acc = self.v_csl.get()
			pwd = self.v_cip.get()
			ser = self.v_exserver.get()
			mail = self.v_mail_k_add.get()
			my_ol = read_exchange.MY_OUTLOOK(acc, pwd, ser, mail)
		except Exception as e:
			printl("Error outlook initialization failed, e: %s"% e)
			return

		#change method of getting mails from win32com to exchangelib
		#my_subfolder = my_ol.find_subfolder(find_folder)
		re_rule = re.compile(mail_keyword, re.I)

		saved_item_path = ''
		n = 0
		IS_FIND = False
	
		if my_ol:
			printl('Start monitoring...')
			while 1:
				for mail_item in my_ol.find_mail(self.v_mail_k.get()):
					if not mail_item:
						break
					else:
						#Extract ftp info and then start to download 
						ftp_info = extract_ftp_info(mail_item.body)
						if ftp_info:
							printl("Detect ftp_info: %s"%''.join(ftp_info))
							#FTP_INFO = collections.namedtuple("FTP_INFO", "HOST PORT ACC PWD DIRNAME")
							self.v_host.set(''.join(ftp_info))
							file_saved = self.direct_download()
							#record mail, time, ftp, file_saved
							#MONITOR_REC = collections.namedtuple("M_REC", "index time subject ftp download_file")
							n += 1
							t = str(mail_item.datetime_received)
							s = mail_item.subject
							f = ''.join(ftp_info)
							if file_saved:
								d = file_saved
							else:
								d = r"N/A"
							monitor_record = MONITOR_REC(str(n), t, s, f, d)
							MONITOR_REC_LIST.append(''.join(monitor_record))
							IS_FIND = True

				time.sleep(int(self.v_interval.get()))
				self.interval_count += 1
				printl("%d seconds interval..count %d"\
				 % (int(self.v_interval.get()), self.interval_count))


				if IS_FIND and self.interval_count % 10 == 0:
					try:
						with open(MONITOR_REC_FILE, 'a') as fobj:
							for item in MONITOR_REC_LIST:
	  							fobj.write(item + '\n')
	  				except Exception as e:
	  					printl("Record monitor history file error:%s" % e)
	  				else:
	  					MONITOR_REC_LIST[:] = []

				if MONITOR_STOP:
					printl("Monitor stopped")
					break

		else:
			printl("ERROR, cannot access to the exhcange server")
		#change method of getting mails from win32com to exchangelib
		'''
		if my_subfolder:
			printl('Start monitor...')
			while 1:
				mail_title_list = []
				mail_title_list = my_ol.find_mail(my_subfolder, mail_keyword)

				if mail_title_list:
					#send mail to inform user
					#the expected mail list
					for mail_title in mail_title_list:
						new_dirname = os.path.join\
						(DOWNLOAD_DIR, re_rule.search(mail_title).group(0))

						saved_item_path = my_download(HOST, PORT, ACC, PWD, SAVE_DIR, new_dirname)
						if saved_item_path:
							if AUTOANA_ENABLE:
								#send to auto search
								FTP_FILE_QUE.put(saved_item_path)
								saved_item_path = ''
						else:
							printl("Download failed")
				time.sleep(int(self.v_interval.get()))
				interval_count += 1
				printl("%d seconds interval..count %d" % (int(self.v_interval.get()), interval_count))

				#test
				if interval_count == 2:
					print("Test start")
					saved_item_path = r"C:\Users\tarzonz\Desktop\sss\ftp_download\1-6889375"
					FTP_FILE_QUE.put(saved_item_path)
					print("DEBUG quit monitor")
				if MONITOR_STOP:
					printl("Monitor stopped")
					break
		else:
			printl("Error, no such folder: %s" % find_folder)
		pythoncom.CoUninitialize()
		'''
		#record
		if IS_FIND:
			try:
				with open(MONITOR_REC_FILE, 'a') as fobj:
					for item in MONITOR_REC_LIST:
	  					fobj.write(item + '\n')
	  		except Exception as e:
	  			printl("Record monitor history file error:%s" % e)


	  	MONITOR_REC_LIST[:] = []
	  	IS_FIND = False
		self.button_monitor.config(text="Start monitor",bg='white',relief='raised',state='normal')
	#############start_monitor()#############


	def start_thread_monitor(self):

		global MAIL_KEYWORD
		global MONITOR_STOP
		global MONITOR_REC_LIST
		global IS_FIND

		if self.v_mail_k.get():
			MAIL_KEYWORD = self.v_mail_k.get()

		self.button_monitor.config(text="Click to stop...",bg='orange', relief='sunken',state='normal')

		if MONITOR_STOP:
			MONITOR_STOP = False

			t = threading.Thread(target=self.start_monitor, args=(MAIL_KEYWORD,))
			#for terminating purpose
			MONITOR_THREADS.append(t)
			t.start()	
		else:
			MONITOR_STOP = True
			self.button_monitor.config(text="Stopping..",bg='orange', relief='sunken',state='disable')
			terminate_threads(MONITOR_THREADS)
			printl("Monitor is terminated")
			if IS_FIND and MONITOR_REC_LIST:
				try:
					with open(MONITOR_REC_FILE, 'a') as fobj:
						for item in MONITOR_REC_LIST:
	  						fobj.write(item + '\n')
	  					fobj.write('Monitor stop\n')
	  			except Exception as e:
	  				printl("Record monitor history file error:%s" % e)
	  			else:
	  				MONITOR_REC_LIST[:] = []
			self.button_monitor.config(text="Start monitor",bg='white',relief='raised',state='normal')
	############start_thread_monitor()#############


	def periodical_check(self):
		global AUTOANA_ENABLE
		if self.v_chk.get() == 1:
			printl("Enable periodical monitor")
			self.entry_mail_k.config(state='normal')
			self.button_monitor.config(state='normal')
			self.label_mail_k.config(state='normal')
			self.spin_interval.config(state='normal')
			self.label_interval.config(state='normal')
			AUTOANA_ENABLE = True

			self.label_exserver.config(state='normal')
			self.entry_exserver.config(state='normal')
			self.label_mail_add.config(state='normal')
			self.entry_mail_add.config(state='normal')
			self.label_csl.config(state='normal')
			self.entry_csl.config(state='normal')
			self.label_cip.config(state='normal')
			self.entry_cip.config(state='normal')

		else:
			#printl("Periodical monitor disabled")
			self.entry_mail_k.config(state='disable')
			self.button_monitor.config(state='disable')
			self.label_mail_k.config(state='disable')
			self.spin_interval.config(state='disable')
			self.label_interval.config(state='disable')
			AUTOANA_ENABLE = False

			self.label_exserver.config(state='disable')
			self.entry_exserver.config(state='disable')
			self.label_mail_add.config(state='disable')
			self.entry_mail_add.config(state='disable')
			self.label_csl.config(state='disable')
			self.entry_csl.config(state='disable')
			self.label_cip.config(state='disable')
			self.entry_cip.config(state='disable')
	########Periodical_check()#####################


	def ask_quit(self, ftp_top):
		global HOST
		global PORT
		global ACC
		global PWD
		global DOWNLOAD_DIR
		global MAIL_KEYWORD
		global MONITOR_INTERVAL

		global EXSERVER
		global MAIL_ADD
		global AD4_ACC
		global AD4_PWD

		global ASK_QUIT

		if askyesno("Tip","Save or not?"):
			#save
			HOST = self.v_host.get()
			PORT = self.v_port.get()
			ACC = self.v_user.get()
			PWD = self.v_pwd.get()
			DOWNLOAD_DIR = self.v_ddirname.get()
			MAIL_KEYWORD = self.v_mail_k.get()
			MONITOR_INTERVAL = self.v_interval.get()

			EXSERVER = self.v_exserver.get()
			MAIL_ADD = self.v_mail_k_add.get()
			AD4_ACC = self.v_csl.get()
			self.v_cip.set('')
			AD4_PWD = self.v_cip.get()

			save_bak()
		else:
			pass

		printl('Bye---------------------------------------'+'\n')
		ASK_QUIT = True
		self.running = False
		if __name__ == '__main__':
			#quit() all windows and parent window to be closed
			ftp_top.quit()
		else:
			#derstroy only this window
			ftp_top.destroy()

	###########init()##############		


if __name__ == '__main__':

	test_top = Tk()
	test_top.withdraw()

	ftp_top = My_Ftp(test_top)
	test_top.mainloop()


	#upload test
	'''
	host = '135.242.80.37'
	port = '21'
	acc = 'mxswing'
	pwd = 'mxswing'
	#file_path = r'C:\Users\tarzonz\Desktop\my_ftp.log'
	file_path = 'my_ftp.log'

	remote_path = '/sharing_folder_37/SLA_History/my_ftp.log'
	my_upload(host, port, acc, pwd, file_path, remote_path)
	'''

