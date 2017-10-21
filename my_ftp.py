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
import read_exchange
from log_reserve import FTP_TIP_QUE as FTQ
from log_reserve import printl
from log_reserve import FTP_SAVES
import time
import datetime
import tooltip
import ctypes
import inspect
from tkFileDialog import askdirectory


HOST = '135.242.80.16:8080'
PORT = '8080'
DOWNLOAD_DIR = '/01_Training/02_PMU/02_Documents'
ACC = 'QD-BSC2'
PWD = 'qdBSC#1234'
SAVE_DIR = FTP_SAVES

CONN = None
DATA_BAK_FILE = os.path.join(FTP_SAVES, "my_ftp.pkl")
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

FTP_INFO = collections.namedtuple("FTP_INFO", "HOST PORT ACC PWD DIRNAME")

#all the data to be backup
DATA_BAK = collections.namedtuple("DATA_BAK", "ftp_bak ol_bak")

DIRECT_DOWNLOAD_STOP = True
DIRECT_DOWNLOAD_THREADS = []
DIRECT_DOWNLOAD_TOTAL = 0
DIRECT_DOWNLOAD_COUNT = 0

AUTOANA_ENABLE = False
MONITOR_THREADS = []
MONITOR_STOP = True
MONITOR_REC = collections.namedtuple("M_REC", "index time subject ftp download_file")
MONITOR_REC_FILE = os.path.join(SAVE_DIR, "monitor_history.txt")
MONITOR_REC_LIST = []
IS_FIND = False

DOWNLOADER_ICON = os.path.join(os.path.join(os.getcwd(), "resource"),'mail.ico')

file_number = 0
dir_number = 0

PROGRESS_THREADS = []
FTP_FILE_QUE = Queue.Queue()


def save_bak():
	ftp_bak = MY_FTP(HOST, PORT, ACC, PWD, DOWNLOAD_DIR, MAIL_KEYWORD, MONITOR_INTERVAL)
	ol_bak = MY_OLOOK(EXSERVER, MAIL_ADD, AD4_ACC, AD4_PWD)
	data_bak = DATA_BAK(ftp_bak, ol_bak)
	#printl("Save data_bak: {}".format(data_bak))
	pickle.dump(data_bak, open(DATA_BAK_FILE,"wb"), True)
############save_bak()#####################


def retrive_bak():
	printl('Welcome to Mail Monitor v2.0')
	try:
		data_bak = pickle.load(open(DATA_BAK_FILE, "rb"))
		#printl("Retrive data_bak:{}".format(data_bak))

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
		#printl("ERROR occure, e= %s" %e)
		pass

	else:
		#printl("Retrive success!\n")
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
	#print "DEBUG start terminate threads: {}".format(l_threads)
	if l_threads:
		for t in l_threads:
			if t.is_alive():
				_async_raise(t.ident, SystemExit)
	#clear the thread list
	l_threads[:] = []
	#print "terminate threads done"
################terminate_threads()##########################


def record_monitor():
	global IS_FIND
	global MONITOR_REC_LIST

	if IS_FIND and MONITOR_REC_LIST:
		try:
			with open(MONITOR_REC_FILE, 'a') as fobj:
				for item in MONITOR_REC_LIST:
					if 'unicode' in str(type(item)):
						item = item.encode('utf-8')
					fobj.write(item + '\n')
  					fobj.write('Monitor stop\n')
		except Exception as e:
			printl("Record monitor history file error:%s" % e)
		else:
			MONITOR_REC_LIST[:] = []
			IS_FIND = False
############record_monitor()######################


def ftp_conn(host, port, acc, pwd):
	global CONN

	printl('ftp_conn start, host:{0}, port:{1}, acc:{2}, pwd:{3}'\
		.format(host,port,acc,pwd))

	print("DEBUG type(host)",type(host))
	print("DEBUG type(prot)",type(port))
	print("DEBUG type(acc)",type(acc))
	print("DEBUG type(pwd)",type(pwd))
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
	global CONN
	global DIRECT_DOWNLOAD_COUNT
	global DIRECT_DOWNLOAD_TOTAL

	print('ftp_download_dir start, dirname = %s' % dirname)
	try:
		CONN.cwd(dirname)
	except ftplib.error_perm:
		printl('ERROR: cannot cd to "%s"' % dirname)
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
			#<DIR> display in widows and dxxx in linux
			#here maybe a bug if only a file with name 'dxxxx'
			if '<DIR>' in file or file.startswith('d'):
				ftp_download_dir(filelines_bk[i])
				CONN.cwd('..')
				os.chdir('..')
			else:
				try:
					CONN.retrbinary('RETR %s' % filelines_bk[i], \
						open(filelines_bk[i], 'wb').write)
				except ftplib.error_perm:
					printl('ERROR: cannot read file "%s"' % file)
					os.unlink(file)
				else:
					DIRECT_DOWNLOAD_COUNT += 1
					printl("[%d/%d]downloaded: %s" % \
						(DIRECT_DOWNLOAD_COUNT, DIRECT_DOWNLOAD_TOTAL, filelines_bk[i]))
			i += 1
##################download_dir()###############

def get_file_number(dirname):
	global DIRECT_DOWNLOAD_TOTAL
	global CONN

	try:
		CONN.cwd(dirname)
	except ftplib.error_perm:
		printl('ERROR: cannot cd to "%s"' % dirname)
		return None
	else:

		'''
		new_dir = os.path.basename(dirname)
		if not os.path.exists(new_dir):
			os.mkdir(new_dir)
		os.chdir(new_dir)
		'''

		filelines = []
		CONN.dir(filelines.append)
		filelines_bk = CONN.nlst()
		i = 0
	
		for file in filelines:
			if '<DIR>' in file:
				get_file_number(filelines_bk[i])
				CONN.cwd('..')
			else:
				DIRECT_DOWNLOAD_TOTAL += 1
			i += 1
#############get_file_number()###############


def my_download(host, port, acc, pwd, save_dir, download_dir):
	global CONN
	global DIRECT_DOWNLOAD_TOTAL
	global DIRECT_DOWNLOAD_COUNT
	global file_number
	global dir_number

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
	DIRECT_DOWNLOAD_TOTAL = 0
	DIRECT_DOWNLOAD_COUNT = 0
	get_file_number(download_dir)
	if DIRECT_DOWNLOAD_TOTAL == 0:
		return None
	printl("Total %d files to be downloaded" % (DIRECT_DOWNLOAD_TOTAL))
	ftp_download_dir(download_dir)
	CONN.quit()

	if DIRECT_DOWNLOAD_TOTAL == DIRECT_DOWNLOAD_COUNT:
		printl("All {} files downloaded successfully!".\
			format(DIRECT_DOWNLOAD_COUNT))
	else:
		printl("DEBUG error, download number mismatch")

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
		global PROGRESS_THREADS
		
		self.parent_top = parent_top
		self.ftp_top = Toplevel(parent_top)
		self.ftp_top.title("Mail Monitor")
		self.ftp_top.geometry('600x330+300+220')
		self.ftp_top.iconbitmap(DOWNLOADER_ICON)
		#self.ftp_top.attributes("-toolwindow", 1)
		#self.ftp_top.wm_attributes('-topmost',1)
		self.ftp_top.protocol("WM_DELETE_WINDOW",lambda :self.ask_quit(self.ftp_top))
		self.running = True

		#Label(self.ftp_top, text='').pack()
		#Label(self.ftp_top, text='').pack()
		fm0 = Frame(self.ftp_top)
		#Label(fm0, text='Mail Monitor v2.0',\
		#	font = ('Helvetica', 12, 'bold')).pack()#, fg= my_color_blue_office)
		blank_label_1 = Label(fm0, text = '').pack()

		fm0.pack()

		
		self.dir_fm = Frame(self.ftp_top)
		self.l_savein = Label(self.dir_fm, text="Save in: ")
		self.v_savein = StringVar()
		self.entry_savein = Entry(self.dir_fm, width=67, textvariable=self.v_savein)
		self.v_savein.set(SAVE_DIR)
		self.entry_savein.config(state='disabled')

		self.b_savein = Button(self.dir_fm, text='Choose directory', command=self.choose_dir, activeforeground\
			='white', activebackground='orange')
		self.b_savein.pack(side=RIGHT)
		self.l_savein.pack(side=LEFT)
		self.entry_savein.pack(side=LEFT)
		self.dir_fm.pack()	


		self.pwindow_qconn = ttk.Panedwindow(self.ftp_top, orient=VERTICAL)

		self.lframe_direct = ttk.Labelframe(self.ftp_top, text='Direct Download',\
		 width= 620, height = 220)
		self.lframe_monitor = ttk.Labelframe(self.ftp_top, text='Auto Download',\
		 width= 620, height = 220)

		self.pwindow_qconn.add(self.lframe_direct)
		self.pwindow_qconn.add(self.lframe_monitor)

		#Host label and entry
		self.label_host = Label(self.lframe_direct, text = 'Ftp Host:').grid(row=0,column=0)
		self.v_host = StringVar()
		self.entry_host = Entry(self.lframe_direct, textvariable=self.v_host,width=50)
		self.entry_host.grid(row=0,column=1)
		ts1 ="Either input an ip:port address or a full ftp url:\n ftp://QD-BSC2:qdBSC#1234@135.242.80.16:8080/"
		ts2 ="01_Training/02_PMU/02_Documents\n then click 'Direct download' to download files in this directory"
		ts=ts1+ts2
		tooltip.ToolTip(self.entry_host, msg=None, msgFunc=lambda : ts, follow=True, delay=0.2)

		#Port label and entry
		self.label_port = Label(self.lframe_direct, text = 'Port:')
		#self.label_port.grid(row=0,column=2)
		self.v_port = StringVar()
		self.entry_port = Entry(self.lframe_direct, textvariabl=self.v_port, width=20)
		#self.entry_port.grid(row=0,column=3)

		#Usrnamer label and entry
		self.label_user = Label(self.lframe_direct, text = 'Username:').grid(row=0,column=2)
		self.v_user = StringVar()
		self.entry_user = Entry(self.lframe_direct, textvariabl=self.v_user, width=20)
		self.entry_user.grid(row=0,column=3)

		#Password label and entry
		self.label_pwd = Label(self.lframe_direct, text = 'Password:').grid(row=1,column=2)
		self.v_pwd = StringVar()
		self.entry_pwd = Entry(self.lframe_direct, textvariabl=self.v_pwd, width=20)
		self.entry_pwd.grid(row=1,column=3)

		#Download dirname
		self.label_ddirname = Label(self.lframe_direct, text = 'Dirname:').grid(row=1,column=0)
		self.v_ddirname = StringVar()
		self.entry_ddirname = Entry(self.lframe_direct, textvariabl=self.v_ddirname, width=50)
		self.entry_ddirname.grid(row=1,column=1)

		#Download button
		self.button_direct = Button(self.lframe_direct,text="Direct dowload",\
			width=20, command=self.start_direct_download, activeforeground='white', \
			activebackground='orange',bg = 'white', relief='raised')
		self.button_direct.grid(row=2,column=3)

		#############Auto download###############

		self.fm_up = Frame(self.lframe_monitor)
		s1 = "Monitor 'Inbox' to automatically download files"
		s2 = " "
		s3 ="based on ftp information in mail with specified title"
		s = s1+s2+s3
		self.v_chk = BooleanVar() 
		self.chk_auto = Checkbutton(self.fm_up, text = s, variable = self.v_chk,\
			command = self.periodical_check)
		self.chk_auto.pack()
		self.fm_up.pack()

		self.fm_config = Frame(self.lframe_monitor,height=50)

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
		tts ="Refer to the Python regular expression\n '.*' means no filter"
		tooltip.ToolTip(self.entry_mail_k, msg=None, msgFunc=lambda : tts, follow=True, delay=0.2)


		self.label_interval = Label(self.fm_config,text= 'Monitor Interval(sec):')
		self.label_interval.grid(row=2,column=2)
		self.v_interval = StringVar()
		self.interval_count = 0
		self.spin_interval = Spinbox(self.fm_config, textvariable=self.v_interval,\
			width = 8, from_=1, to=8640,increment=1)
		self.spin_interval.grid(row=2,column=3)	

		self.fm_config.pack()

		self.fm_mid = Frame(self.lframe_monitor, height=50)
		#button trigger monitor mails' titles
		self.button_monitor = Button(self.fm_mid, text="Start monitor",\
		 command=self.start_monitor_download, activeforeground\
		='white', activebackground='orange',bg = 'white', relief='raised', width=20)
		self.button_monitor.pack()#grid(row=1,column=3)
		self.fm_mid.pack()
		#for read exchanger configuration

		self.pwindow_qconn.pack()

		Label(self.ftp_top,text='  ').pack(side=LEFT)
		self.fm_tip = Frame(self.ftp_top)
		#self.label_blank11 = Label(self.fm_tip,text= '  '*3).pack(side=LEFT)
		self.v_tip = StringVar()
		self.label_tip = Label(self.fm_tip,textvariable=self.v_tip)
		self.label_tip.grid(row=0,column=0)
		self.fm_tip.pack(side=LEFT)
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

		t_progress_tip = threading.Thread(target=self.start_progress_tip)
		t_progress_tip.start()
		PROGRESS_THREADS.append(t_progress_tip)


		
		##############init()###############


	def extract_ftp_info(self,s):
		'''
		from the string s to find the first ftp format string
		return 'ftp://QD-BSC2:qdBSC#1234@135.242.80.16:8080/01_Training/02_PMU/02_Documents'
		'''
		print("Debug start extract_ftp_info")
		full_ftp_re = r'ftp://(\w.*):(\w.*)@(\d{2,3}\.\d{2,3}\.\d{2,3}\.\d{2,3})(:\d*)?(/.*?\r)'
		res = re.search(full_ftp_re,s)
	
		if res:
			acc = res.group(1)
			pwd = res.group(2)
			host = res.group(3)
			port = res.group(4)
			# '.'will match any character except '\n' so the last 
			#character is '\r' and use [:-1] to slice off it
			dirname = res.group(5).strip('\r')
	
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
			host_port_re = r'(\d{2,3}\.\d{2,3}\.\d{2,3}\.\d{2,3})(:\d*)?'
			host_port_res = re.search(host_port_re,s)
			if host_port_res:
				host = host_port_res.group(1)
				port = host_port_res.group(2)
				if not port:
					port = '21'
				else:
					port = port[1:]
				if host and port:
					self.v_host.set(host)
					self.v_port.set(port)
				print("DEBUG host:{},port:{} got!".format(self.v_host.get(),self.v_port.get()))
				return None
			else:		
				print("DEBUG ftp info not found return None")
				return None
###########extract_ftp_info()################


	def choose_dir(self,ev=None):
		global SAVE_DIR 
		p = askdirectory(mustexist=1)  # 返回目录路径
		print("choose to save in directory:",p)
		if 'unicode' in str(type(p)):
			p = p.encode('utf-8')#.decode('gb2312')
		elif 'str' in str(type(p)):
			p = p.decode('utf-8')

		print(p)
		print("DEBUG type(SAVE_DIR)",type(SAVE_DIR))

		if p:
			SAVE_DIR = p
			print("DEBUG type(SAVE_DIR)",type(SAVE_DIR))
			self.v_savein.set(p)
	######open_dir()##############


	def start_progress_tip(self):
		global FTQ  

		print "ftp start_progress_tip begin"
		while 1:
			#print("DEBUG progress is undergoing")
			#time.sleep(2)
			try:
				#block = False means if queue is empty
				#then get an exception
				s = FTQ.get(False)
				self.v_tip.set(s)
			except Exception as e:
				#print("queue is empty, e %s" % e)
				pass

			time.sleep(0.4)

			# BUG16 here can't use global to determine
			if not self.running:
				self.v_tip.set("Exited..")
				print("not running")
				break
		print "ftp start_progress_tip end!"

	########start_progess_tip###########


	def start_direct_download(self):
		global DIRECT_DOWNLOAD_STOP
		global DIRECT_DOWNLOAD_THREADS

		if DIRECT_DOWNLOAD_STOP:
			DIRECT_DOWNLOAD_STOP = False
			self.button_direct.config(text="Click to stop...",bg='orange',relief='sunken',state='normal')

			t = threading.Thread(target=self.direct_download)
			DIRECT_DOWNLOAD_THREADS.append(t)
			t.start()

		else:
			DIRECT_DOWNLOAD_STOP = True
			self.button_direct.config(text="Stopping..",bg='orange', relief='sunken',state='disable')
			terminate_threads(DIRECT_DOWNLOAD_THREADS)
			printl("Direct Download is terminated")
			self.button_direct.config(text="Direct download",bg='white',relief='raised',state='normal')

	##########start_direct_download()###################
	

	def direct_download(self):
		global HOST
		global PORT
		global ACC
		global PWD
		global SAVE_DIR
		global DOWNLOAD_DIR
		global DIRECT_DOWNLOAD_STOP
		printl("Direct_download starts")

		#extract ftp info
		if self.v_host.get():

			ftp_info = self.extract_ftp_info(self.v_host.get())
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

		#set host to display as ip:port format
		self.v_host.set(HOST + ':' + PORT)
		file_saved = ''
		file_saved = my_download(HOST, PORT, ACC, PWD, SAVE_DIR, DOWNLOAD_DIR)

		if not file_saved:
			printl("Download Error: cannot access or file already exists or download dir not exsits.")
			#crash
			#showerror(title='Ftp Connect Error', message="Cannot accesst to %s" % HOST)
		else:
			printl("Download completed in: %s" % \
				file_saved)

			if AUTOANA_ENABLE:
				#send to queue for other processing, e.g.,auto search in listdir.py
				print("DEBUG my_ftp.py send %s to auto analyse" % file_saved)
				FTP_FILE_QUE.put(file_saved)

		DIRECT_DOWNLOAD_STOP = True
		self.button_direct.config(text="Direct download",bg='white',relief='raised',state='normal')

		return file_saved
	##############direct_download()##################

	#revise with read_exchange
	def monitor_download(self, mail_keyword):
		global MONITOR_REC_LIST
		global MONITOR_REC_FILE
		global IS_FIND
		global MONITOR_STOP
		global DIRECT_DOWNLOAD_STOP

		self.interval_count = 0
		MONITOR_REC_LIST.append('')
		MONITOR_REC_LIST.append(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
		MONITOR_REC_LIST.append("index time subject ftp download_file")

		find_folder = "inbox"
		try:
			acc = self.v_csl.get()
			pwd = self.v_cip.get()
			ser = self.v_exserver.get()
			mail = self.v_mail_k_add.get()
			my_ol = read_exchange.MY_OUTLOOK(acc, pwd, ser, mail)
		except Exception as e:
			printl("Error outlook initialization failed, e: %s"% e)
			printl("DEBUG acc:{},pwd:{},ser:{},mail:{}".format(acc,pwd,ser,mail))
			return

		re_rule = re.compile(mail_keyword, re.I)
		del_html = re.compile(r'<[^>]+>',re.S)

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
						plain_body = del_html.sub('',mail_item.body)
						ftp_info = self.extract_ftp_info(plain_body)
						if ftp_info:
							print("\a")
							printl("Detected ftp_info:{}".format(ftp_info))
							#FTP_INFO = collections.namedtuple("FTP_INFO", "HOST PORT ACC PWD DIRNAME")
							#must add '\\r' because extract_ftp_info use this as an end
							s = r"ftp://"+ftp_info.ACC+":"+ftp_info.PWD+"@"+ftp_info.HOST+":"+\
							ftp_info.PORT+ftp_info.DIRNAME + '\r'
							if 'unicode' in str(type(s)):
								s = s.encode('utf-8')
							self.v_host.set(s)
							if DIRECT_DOWNLOAD_STOP:
								DIRECT_DOWNLOAD_STOP = False
								self.button_direct.config\
								(text="Click to stop...",bg='orange',relief='sunken',state='normal')
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
								monitor_record = MONITOR_REC(str(n)+'.', t, s, f, d)
								MONITOR_REC_LIST.append(',  '.join(monitor_record))
								IS_FIND = True
							else:
								printl("Error, another direct download is under processing, you can't start download this!")

				time.sleep(int(self.v_interval.get()))
				self.interval_count += 1
				printl("%d seconds interval..count %d"\
				 % (int(self.v_interval.get()), self.interval_count))


				if self.interval_count % 10 == 0:
					record_monitor()

				if MONITOR_STOP:
					printl("Monitor stopped")
					break

		else:
			printl("ERROR, cannot access to the exhcange server")
		#record
		record_monitor()
		MONITOR_STOP = True
		self.button_monitor.config(text="Start monitor",bg='white',relief='raised',state='normal')
	#############monitor_download()#############


	def start_monitor_download(self):

		global MAIL_KEYWORD
		global MONITOR_STOP
		global MONITOR_REC_LIST
		global IS_FIND

		if self.v_mail_k.get():
			MAIL_KEYWORD = self.v_mail_k.get()

		self.button_monitor.config(text="Click to stop...",bg='orange', relief='sunken',state='normal')

		if MONITOR_STOP:
			MONITOR_STOP = False

			t = threading.Thread(target=self.monitor_download, args=(MAIL_KEYWORD,))
			#for terminating purpose
			MONITOR_THREADS.append(t)
			t.start()	
		else:
			MONITOR_STOP = True
			self.button_monitor.config(text="Stopping..",bg='orange', relief='sunken',state='disable')
			terminate_threads(MONITOR_THREADS)
			printl("Monitor is terminated")

			record_monitor()

			self.button_monitor.config(text="Start monitor",bg='white',relief='raised',state='normal')
	############start_monitor_download()#############


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

		global FTQ

		if askyesno("Tip","Save current configurations?"):
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

		printl('Mail Monitor: Bye~'+'\n')
		self.running = False
		FTP_FILE_QUE.put('ftp quit')

		#terminate progress threads
		#crash don't know why
		#terminate_threads(PROGRESS_THREADS)

		if __name__ == '__main__':
			#quit() all windows and parent window to be closed
			ftp_top.quit()
		else:
			#important remember to do these stuffs before destruction!
			#Even though the window is destoyed, thease globals still in ram
			FTQ.queue.clear()
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

