#!/usr/bin/env python
#!--*--coding:utf-8--*-

import mttkinter as Tkinter
from Tkinter import *
import ttk
from tkMessageBox import *

import ftplib
import os
import socket
import threading
import cPickle as pickle
import collections
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


'''
here totally 3 thread lists
l_threads.extend(my_ftp.MONITOR_THREADS)
l_threads.extend(my_ftp.DIRECT_DOWNLOAD_THREADS)
l_threads.extend(my_ftp.PROGRESS_THREADS)
'''

DOWNLOADER_ICON = os.path.join(os.path.join(os.getcwd(), "resource"),'mail.ico')

HOST = '135.242.80.16:8080'
PORT = '8080'
DOWNLOAD_DIR = '/01_Training/02_PMU/02_Documents'
ACC = 'QD-BSC2'
PWD = 'qdBSC#1234'
SAVE_DIR = FTP_SAVES

L_RESERVED_FTP = []

CONN = None
CONN2 = None
CWD_PATH = os.getcwd()
DATA_BAK_FILE = os.path.join(CWD_PATH, "my_ftp.pkl")
MAIL_KEYWORD = r'\d-\d{7}\d*'
#MAIL_KEYWORD = '1-6853088'
MONITOR_INTERVAL = '6'
MY_FTP = collections.namedtuple("MY_FTP",\
 "host port user pwd target_dir mail_keyword interval l_reserved")

#outlook config
EXSERVER = 'CASArray.ad4.ad.alcatel.com'
MAIL_ADD = 'xxx.yy@nokia-sbell.com'
AD4_ACC = 'ad4\\xxx'
AD4_PWD = ''
MY_OLOOK = collections.namedtuple("MY_OLOOK", "server mail user pwd")

FTP_INFO = collections.namedtuple("FTP_INFO", "HOST PORT ACC PWD DIRNAME")
FTP_INFO_HISTORY = []

#all the data to be backup
DATA_BAK = collections.namedtuple("DATA_BAK", "ftp_bak ol_bak")
try:
	PARTIAL_FTP_RE = open('download_flag.txt','r').readlines()[0]
except:
	PARTIAL_FTP_RE = ''

DIRECT_DOWNLOAD_STOP = True
DIRECT_DOWNLOAD_THREADS = []
DIRECT_DOWNLOAD_TOTAL = 0
DIRECT_DOWNLOAD_COUNT = 0
DIRECT_DOWNLOAD_BYTES = 0

AUTOANA_ENABLE = False
MONITOR_THREADS = []
MONITOR_STOP = True



PROGRESS_THREADS = []
FTP_FILE_QUE = Queue.Queue()
PROGRESS_LBL = None
PROGRESS_BAR = None
PROGRESS_STRVAR = None
PROGRESS_COST_SEC = 0
PROGRESS_TOTAL_BYTES = 0

#MUTEX = threading.Lock()

def save_bak():
	ftp_bak = MY_FTP(HOST, PORT, ACC, PWD, DOWNLOAD_DIR, MAIL_KEYWORD, MONITOR_INTERVAL,\
		L_RESERVED_FTP)
	ol_bak = MY_OLOOK(EXSERVER, MAIL_ADD, AD4_ACC, AD4_PWD)
	data_bak = DATA_BAK(ftp_bak, ol_bak)
	#printl("Save data_bak: {}".format(data_bak))
	pickle.dump(data_bak, open(DATA_BAK_FILE,"wb"), True)
############save_bak()#####################


def retrive_bak():
	global HOST
	global PORT
	global ACC
	global PWD
	global DOWNLOAD_DIR
	global MONITOR_INTERVAL
	global L_RESERVED_FTP

	global EXSERVER
	global MAIL_ADD
	global AD4_ACC
	global AD4_PWD

	printl("'Welcome to Mail Monitor v2.1'")
	try:
		data_bak = pickle.load(open(DATA_BAK_FILE, "rb"))
		#printl("Retrive data_bak:{}".format(data_bak))

		HOST = data_bak.ftp_bak.host
		PORT = data_bak.ftp_bak.port
		ACC = data_bak.ftp_bak.user
		PWD = data_bak.ftp_bak.pwd
		DOWNLOAD_DIR = data_bak.ftp_bak.target_dir
		MONITOR_INTERVAL = data_bak.ftp_bak.interval
		L_RESERVED_FTP = data_bak.ftp_bak.l_reserved

		EXSERVER = data_bak.ol_bak.server
		MAIL_ADD = data_bak.ol_bak.mail
		AD4_ACC = data_bak.ol_bak.user
		AD4_PWD = data_bak.ol_bak.pwd

	except Exception as e:
		#printl("ERROR occure, e= %s" %e)
		if not L_RESERVED_FTP:
			retrive_reserved_ftp()
		pass

	else:
		#printl("Retrive success!\n")
		return data_bak	
	return None

def retrive_reserved_ftp():
	global CWD_PATH
	global L_RESERVED_FTP
	try:
		with open(os.path.join(CWD_PATH,'reserved_ftp.ini'), 'rb') as fobj:
			while 1:
				buff = fobj.readline()
				if buff == '':
					break
				else:
					L_RESERVED_FTP.append(buff.strip())
	except Exception as e:
		#if no .ini file
		L_RESERVED_FTP = [r'ftp://ftpalcatel:ftp$alcatel1@172.23.102.135',r'ftp://QD-BSC2:qdBSC#1234@135.242.80.16:8080']
		pass
	else:
		print("DEBUG L_RESERVED_FTP=",L_RESERVED_FTP)

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
				#bug18 unresolved question
				#t._Thread__stop()
	#clear the thread list
	#l_threads[:] = []
	#print "terminate threads done"
################terminate_threads()##########################


def ftp_conn(host, port, acc, pwd, timeout = None):
	global CONN

	printl('ftp_conn start, host:{0}, port:{1}, acc:{2}, pwd:{3}'\
		.format(host,port,acc,pwd))

	try:
		CONN = ftplib.FTP()
		#set a 3 seconds timeout
		if not timeout:
			CONN.connect(host, port, timeout)
		else:
			CONN.connect(host, port)
	except (socket.error, socket.gaierror), e:
		printl('ERROR: cannot reach host "%s", exited.' % host)
		return False
	printl("Successfully connected to host '%s'"% host)

	try:
		CONN.login(acc, pwd)
	except ftplib.error_perm:
		printl('ERROR: cannot login as "%s", exited.' % acc)
		CONN.quit()
		return False
	printl("Successfully logged in as '%s'" % acc)

	return True
############ftp_conn()#####################


def ftp_write_handle(buff,total,func):
	global DIRECT_DOWNLOAD_BYTES
	global PROGRESS_BAR
	global PROGRESS_STRVAR
	global PROGRESS_COST_SEC
	global PROGRESS_TOTAL_BYTES

	start_t = time.clock()
	func(buff)
	block_len = len(buff)
	DIRECT_DOWNLOAD_BYTES += block_len
	PROGRESS_BAR["maximum"] = total
	PROGRESS_BAR["value"] = DIRECT_DOWNLOAD_BYTES

	interv_t = time.clock() - start_t

	PROGRESS_TOTAL_BYTES += block_len
	PROGRESS_COST_SEC += interv_t

	s = "{:.1%}({:.1f}KB/s)".format(DIRECT_DOWNLOAD_BYTES*1.0/total, \
		PROGRESS_TOTAL_BYTES/1024.0/PROGRESS_COST_SEC)
	PROGRESS_STRVAR.set(s)

def ftp_download_dir(dirname):
	global CONN
	global DIRECT_DOWNLOAD_COUNT
	global DIRECT_DOWNLOAD_TOTAL
	global DIRECT_DOWNLOAD_BYTES

	print("ftp_download_dir, dirname: '%s'" % dirname)
	try:
		CONN.cwd(dirname)
	except ftplib.error_perm:
		printl('ERROR: cannot cd to "%s"' % dirname)
		return False
	else:

		new_dir = os.path.basename(dirname)
		if not os.path.exists(new_dir):
			os.mkdir(new_dir)

		os.chdir(new_dir)

		filelines = []
		filelines_bk = []
		CONN.dir(filelines.append)
		filelines_bk = CONN.nlst()

		if len(filelines_bk) != len(filelines):
			print("Error, Number does not match!\n")

		i = 0
		for file in filelines:
			#unmatched file_name
			file_name = ''
			if filelines_bk[i] in file:
				file_name = filelines_bk[i]
			else:
				#the filelines_bk is not in the same order with filelines
				#filelines like:
				#'drwxr-xr-x   2 ftpalcatel users        1024 Oct 26 14:46 SQ2DSL02.02C_20171026095345.0'
				#There is a bug if the file name contains blanks
				file_name = file.split()[-1]

			#<DIR> display in widows and drwxr- in linux
			#here maybe a bug if only a file with name 'dxxxx'
			if '<DIR>' in file or file.startswith('d'):
					ftp_download_dir(file_name)
					CONN.cwd('..')
					os.chdir('..')
			else:
				try:
					#how to speed up?
					DIRECT_DOWNLOAD_BYTES = 0
					#change transfor mode from ASCII to Binary
					#then allowed to get file_size
					CONN.voidcmd('TYPE I')
					file_size = CONN.size(file_name)
					maxblocksize = 2097152
					printl("Downloading[%d/%d]: %s"%\
						(DIRECT_DOWNLOAD_COUNT+1, DIRECT_DOWNLOAD_TOTAL, file_name))

					file_to_write = open(file_name, 'wb').write
					CONN.retrbinary('RETR %s' % file_name, \
						#use lambda to pass multiple paremeters
						#open(filelines_bk[i], 'wb').write,maxblocksize)
						lambda block: ftp_write_handle(block,file_size,file_to_write), maxblocksize)
				#except ftplib.error_perm:
				except Exception as e:
					printl('ERROR: cannot download file "%s"' % file_name)
					print("error:",e)
					try:
						os.unlink(file_name)
					except Exception as e:
						#print("DEBUG os.unlink error:",e)
						continue
					else:
						print("DEBUG os.unlink successed")
						continue
				else:
					DIRECT_DOWNLOAD_COUNT += 1
			i += 1
		return True
##################download_dir()###############

def start_get_file_number(host, port, acc, pwd, download_dir):

	t = threading.Thread(target=new_conn_get_file_number,args=(host, port, acc, pwd, download_dir))
	DIRECT_DOWNLOAD_THREADS.append(t)
	t.start()

def new_conn_get_file_number(host, port, acc, pwd, download_dir):
	global CONN2

	print('start the conn2 for file number, host:{0}, port:{1}, acc:{2}, pwd:{3}'\
		.format(host,port,acc,pwd))

	try:
		CONN2 = ftplib.FTP()
		#set a 3 seconds timeout
		CONN2.connect(host, port, 30000)
	except (socket.error, socket.gaierror), e:
		printl('ERROR: cannot reach host "%s", exited.' % host)
		return False

	try:
		CONN2.login(acc, pwd)
	except ftplib.error_perm:
		printl('ERROR: cannot login as "%s", exited.' % acc)
		CONN2.quit()

	get_file_number(download_dir)
###############################################################3#


def get_file_number(dirname):
	global DIRECT_DOWNLOAD_TOTAL
	global CONN2

	#print("DEBUG get_file_number, dirname:'%s'"%dirname)
	try:
		CONN2.cwd(dirname)
		CONN2.voidcmd('TYPE I')
	except Exception as e:
		printl('ERROR: cannot cd to "%s" due to %s' % (dirname,e))
		return None
	else:

		#bug filelines not match with filelines_bk order
		filelines = []
		filelines_bk = []
		filelines_bk = CONN2.nlst()
		CONN2.dir(filelines.append)
		if len(filelines_bk) != len(filelines):
			printl("DEBUG ERROR number don't match\n")

		i = 0
		for file in filelines:
			if '<DIR>' in file or file.startswith('d'):
				if filelines_bk[i] in file:
					get_file_number(filelines_bk[i])
				else:
					#print("disorderrrrrrrrrrrrrrrrr!")
					#print ("DEBUG file=",file)
					get_file_number(file.split()[-1])
				CONN2.cwd('..')
			else:
				DIRECT_DOWNLOAD_TOTAL += 1
				#print("DEBUG counting: ",DIRECT_DOWNLOAD_TOTAL)
			i += 1
#############get_file_number()###############


def my_download(host, port, acc, pwd, save_dir, download_dir):
	global CONN
	global DIRECT_DOWNLOAD_TOTAL
	global DIRECT_DOWNLOAD_COUNT
	global PROGRESS_COST_SEC
	global PROGRESS_TOTAL_BYTES
	global PROGRESS_STRVAR
	global PROGRESS_BAR
	global PROGRESS_LBL

	down_name = os.path.basename(download_dir)

	printl("my_download starts,download_dir: '%s'"%(download_dir))
	#if this file had been downloaded, quit
	printl("Check exists of dir: %s"%(os.path.join(save_dir,down_name)))
	if os.path.exists(os.path.join(save_dir,down_name)):
		printl("Dir already exsit:%s, quit download."% os.path.join(save_dir,down_name))
		return None

	os.chdir(save_dir)

	if not ftp_conn(host, port, acc, pwd, 30000):
		return None

	printl("Begin to download, calculating files number...")
	DIRECT_DOWNLOAD_TOTAL = 0
	DIRECT_DOWNLOAD_COUNT = 0
	start_get_file_number(host, port, acc, pwd, download_dir)
	#CONN.set_debuglevel(1)
	#get_file_number(download_dir)
	if DIRECT_DOWNLOAD_TOTAL == 0:
		pass
		#return None
	#printl("Total %d files" % (DIRECT_DOWNLOAD_TOTAL))
	PROGRESS_COST_SEC = 0
	PROGRESS_TOTAL_BYTES = 0
	PROGRESS_BAR.pack(side=LEFT)
	PROGRESS_LBL.pack(side=LEFT)

	download_success = ftp_download_dir(download_dir)
	CONN.quit()

	PROGRESS_BAR.pack_forget()
	PROGRESS_LBL.pack_forget()

	if not download_success:
		return None
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

	if not ftp_conn(host, port, acc, pwd, 3):
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
		Label(fm0, text = '').pack()

		fm0.pack()

		
		self.dir_fm = Frame(self.ftp_top)
		self.v_saved_number =  0
		self.l_savein = Label(self.dir_fm, text="Save in: ")
		self.v_savein = StringVar()
		self.entry_savein = Entry(self.dir_fm, width=66, textvariable=self.v_savein)
		self.v_savein.set(SAVE_DIR)
		#self.entry_savein.config(state='disabled')

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
		self.label_csl = Label(self.fm_config, text = 'Domain\CSL:',justify = LEFT)
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
		tts ="Refer to the Python regular expression\n '.*' means no filter or just leave it a blank"
		tooltip.ToolTip(self.entry_mail_k, msg=None, msgFunc=lambda : tts, follow=True, delay=0.2)


		self.label_interval = Label(self.fm_config,text= 'Monitor Interval(sec):')
		self.label_interval.grid(row=2,column=2)
		self.v_interval = StringVar()
		self.spin_interval = Spinbox(self.fm_config, textvariable=self.v_interval,\
			width = 8, from_=1, to=8640,increment=1)
		self.spin_interval.grid(row=2,column=3)	

		self.fm_config.pack()

		self.fm_mid = Frame(self.lframe_monitor, height=50)
		#button trigger monitor mails' titles
		self.ftp_queue = []
		#like self.ftp_queue = [['ftp_info1','ftp_info2'],['ftp_info3'],['ftp_info4,ftp_info5']]
		self.v_ftp_number = StringVar()
		self.v_ftp_number.set(str(len(self.ftp_queue)))
		self.label_ftp_q = Label(self.fm_mid, textvariable = self.v_ftp_number)
		self.label_ftp_q.pack(side=RIGHT)
		Label(self.fm_mid, text="FTP Queued: ").pack(side=RIGHT)
		self.button_monitor = Button(self.fm_mid, text="Start monitor",\
		 command=self.start_monitor_download, activeforeground\
		='white', activebackground='orange',bg = 'white', relief='raised', width=20)
		self.button_monitor.pack()#grid(row=1,column=3)
		self.fm_mid.pack()
		#for read exchanger configuration

		self.pwindow_qconn.pack()

		Label(self.ftp_top,text='  ').pack()
		self.fm_tip = Frame(self.ftp_top)
		fm_label = Frame(self.fm_tip)
		#self.label_blank11 = Label(self.fm_tip,text= '  '*3).pack(side=LEFT)
		self.v_tip = StringVar()
		self.label_tip = Label(fm_label,textvariable=self.v_tip,justify=LEFT)
		self.label_tip.grid(row=0,column=0)
		fm_label.pack()

		fm_b = Frame(self.fm_tip)
		self.p = ttk.Progressbar(fm_b, orient=HORIZONTAL, mode='determinate',length = 100, maximum=100)
		self.p.pack(side=LEFT)
		global PROGRESS_BAR
		global PROGRESS_STRVAR
		global PROGRESS_LBL
		self.v_p = StringVar()
		self.v_p.set("")
		PROGRESS_STRVAR = self.v_p
		self.p_label = Label(fm_b, textvariable=self.v_p)
		self.p_label.pack(side=LEFT)
		PROGRESS_LBL = self.p_label
		PROGRESS_BAR = self.p
		fm_b.pack(side=LEFT)
		self.fm_tip.pack(side=LEFT)
		PROGRESS_BAR.pack_forget()
		PROGRESS_LBL.pack_forget()
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

		#start a ever running progress tip thread
		t_progress_tip = threading.Thread(target=self.start_progress_tip)
		t_progress_tip.start()
		PROGRESS_THREADS.append(t_progress_tip)
		print("DEBUG my_ftp.py progress thread start",t_progress_tip)
		
		##############init()###############


	def extract_ftp_info(self,s, from_mail = False):
		'''
		from the string s to find the first ftp format string
		return 'ftp://QD-BSC2:qdBSC#1234@135.242.80.16:8080/01_Training/02_PMU/02_Documents'
		'''
		global PARTIAL_FTP_RE
		print("extract_ftp_info start")
		#full_ftp_re = r'ftp://(\w.*):(\w.*)@(\d{2,3}\.\d{2,3}\.\d{2,3}\.\d{2,3})(:\d*)?(/.*?\r)'
		#due to the mail content got from exchangelib is html fomat
		#the matched result ended with a '\r' being the ending flag
		#so use r'[^\\r]'to explicitly tell the characters lasts until meeting a r'\\r'
		#sometimes people write the url and finished with the period '.' so stop here.
		#full_ftp_re = r'ftp://(\w.*):(\w.*)@(\d{2,3}\.\d{2,3}\.\d{2,3}\.\d{2,3})(:\d*)?(/.*[^\.,\r])'
		full_ftp_re = r'ftp://(\w.*):(\w.*)@(\d{2,3}\.\d{2,3}\.\d{1,3}\.\d{1,3})(:\d*)?(/.[^\r,\n,\.,\,]*)'
		res = re.search(full_ftp_re,s)

		if not res:
			#host is a non-numeric domain name then we use r'(.[^/:]*) to get the name string
			#no / and no : contained in the domain name then any character
			full_ftp_re = r'ftp://(\w.*):(\w.*)@(.[^/:]*)(:\d*)?(/.*[^\r,\n,\.])'
			res = re.search(full_ftp_re,s)

		#res.group(0) the whole ftp url
		#res.group(1) the account
		#res.group(2) the password
		#res.group(3) the IP address
		#res.group(4) the port number
		#res.group(5) the download directory
		if res:
			print("Get regular expression host res.group(0)=",res.group(0))
			acc = res.group(1)
			pwd = res.group(2)
			host = res.group(3)
			port = res.group(4)
			dirname = res.group(5).strip('\r').strip(' ')
	
			if not port:
				port = '21'
			else:
				port = port[1:]
	
			if acc and pwd and host and port and dirname:
				ftp_info = FTP_INFO(host, port, acc, pwd, dirname)
				print("Get full ftp info: %s" % ''.join(ftp_info))
				return ftp_info
			else:
				print("DEBUG error, some ftp info is none")
				return None

		else:
			#only partial ftp information
			if not from_mail:
				#direct input host:port like "135.252.80.40:21"
				host_port_re = r'(\d{2,3}\.\d{2,3}\.\d{2,3}\.\d{2,3})(:\d*)?'
				host_port_res = re.search(host_port_re,s)
				#for host is a domain string
				if not host_port_res:
					host_port_re = r'(.[^/]*)(:\d*)?'
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
					#here just return None to only update host and port
					return None
				else:		
					print("DEBUG ftp info not found return None")
					return None
			else:
				#try to find the partila ftp info: directory name:

				#check if there is only a directory name
				#then get it and combined with the reserved servers
				#try every reserved servers

				partial_ftp_re = ''
				if not PARTIAL_FTP_RE:
					partial_ftp_re = \
					r'(TEC server.*(\n)?.*)|(traces are.*(\n)?.*)'+\
					r'|(available traces.*(\n)?.*)|(download traces.*(\n)?.*)'+\
					r'|(you can get.*(\n)?.*)|(traces upload.*(\n).*)|(ftp server.*(\n).*)'+\
					r'|(upload to.*(\n).*)'
				else:
					partial_ftp_re = PARTIAL_FTP_RE

				res = re.search(partial_ftp_re, s, re.IGNORECASE)

				dirname = ''
				if res:
					print("DEBUG found the flag of trace download request: ",res.group(0))
					#there is trace upload flag
					s_ftp = res.group(0)
					#dir_re = r'(/.*)+[^\.,\r,\n,\,]'
					dir_re = r'(/.[^\,\r\n\.]*)+'
					res_dir = re.search(dir_re, s_ftp)	
					if res_dir:
						dirname = res_dir.group(0)
						#debug why group(1) inacurate
						print("DEBUG get the dirname: ",dirname)
						if dirname != None:
							ftp_info = FTP_INFO('', '', '', '', dirname)
							print("DEBUG partial ftp_info get: %s" % ''.join(ftp_info))
							return ftp_info
						else:
							print("DEBUG no available dirname!")
							return None
					else:
						return None
				else:
					return None
###########extract_ftp_info()################


	def choose_dir(self,ev=None):
		global SAVE_DIR 
		p = askdirectory(parent=self.ftp_top,mustexist=1)  # 返回目录路径
		print("choose to save in directory:",p)
		if 'unicode' in str(type(p)):
			p = p.encode('utf-8')#.decode('gb2312')
		elif 'str' in str(type(p)):
			p = p.decode('utf-8')
		print(p)

		if p:
			SAVE_DIR = p
			printl("Updated save dir: %s"%SAVE_DIR)
			self.v_savein.set(p)
	######open_dir()##############


	def start_progress_tip(self):
		global FTQ  

		print "ftp start_progress_tip begin"
		while 1:
			#print("DEBUG progress is undergoing")
			#time.sleep(1)
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
		global PROGRESS_BAR
		global PROGRESS_LBL

		if DIRECT_DOWNLOAD_STOP:
			DIRECT_DOWNLOAD_STOP = False
			self.button_direct.config(text="Downloading...",bg='orange',relief='sunken',state='normal')

			t = threading.Thread(target=self.direct_download)
			DIRECT_DOWNLOAD_THREADS.append(t)
			t.start()

		else:
			DIRECT_DOWNLOAD_STOP = True
			self.button_direct.config(text="Stopping..",bg='orange', relief='sunken',state='disable')
			terminate_threads(DIRECT_DOWNLOAD_THREADS)
			printl("Direct Download is terminated")
			self.button_direct.config(text="Direct download",bg='white',relief='raised',state='normal')
			PROGRESS_BAR.pack_forget()
			PROGRESS_LBL.pack_forget()

	##########start_direct_download()###################
	

	def direct_download(self):
		global HOST
		global PORT
		global ACC
		global PWD
		global SAVE_DIR
		global DOWNLOAD_DIR
		global DIRECT_DOWNLOAD_STOP
		global L_RESERVED_FTP
		global PROGRESS_TOTAL_BYTES
		global PROGRESS_COST_SEC
		printl("Direct_download starts")


		#extract ftp info
		if self.v_host.get():

			ftp_info = self.extract_ftp_info(self.v_host.get(), from_mail = False)
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
			#get rid of the last '/' if had
			self.v_ddirname.set(self.v_ddirname.get().strip())
			if self.v_ddirname.get()[-1] == '/':
				self.v_ddirname.set(self.v_ddirname.get()[:-1])
			DOWNLOAD_DIR = self.v_ddirname.get()


		#set host to display as ip:port format
		self.v_host.set(HOST + ':' + PORT)
		file_saved = ''
		start_t = time.clock()
		try:
			file_saved = my_download(HOST, PORT, ACC, PWD, SAVE_DIR, DOWNLOAD_DIR)
		except Exception as e:
			print("my_download error",e)
			file_saved = None
		end_t = time.clock()
		interval_t = time.clock() - start_t

		print("DEBUG file_saved=",file_saved)
		if not file_saved:
			print("DEBUG Download failed, time used: %.1f seconds"%interval_t)
			#crash
			#showerror(title='Ftp Connect Error', message="Cannot accesst to %s" % HOST)
		else:
			self.l_savein.bell()
			printl("Download completed in: %s, total time: %.1f seconds" % (file_saved, interval_t))
			print("DEBUG total bytes:{} total sec:{}".format(PROGRESS_TOTAL_BYTES, PROGRESS_COST_SEC))
			#update MM's knowledge about ftp info 
			s = r"ftp://"+ACC+":"+PWD+"@"+HOST+":"+PORT
			if s not in L_RESERVED_FTP:
				L_RESERVED_FTP.append(s)
				printl("New ftp address learned:",s)

			if AUTOANA_ENABLE:
				#send to queue for other processing, e.g.,auto search in listdir.py
				print("DEBUG my_ftp.py send %s to auto analyse" % file_saved)
				FTP_FILE_QUE.put(file_saved)

		DIRECT_DOWNLOAD_STOP = True
		self.button_direct.config(text="Direct download",bg='white',relief='raised',state='normal')

		return file_saved
	##############direct_download()##################


	def download_ftpinfo(self):
		global DIRECT_DOWNLOAD_STOP
		print("DEBUG start download_ftpinfo circle")
		interval_count = 0
		while 1:

			if MONITOR_STOP or (not self.running):
				printl("download_ftpinfo thread stopped")
				break

			if self.ftp_queue:
				#pop out the first ftp_info_list
				ftp_info_list = self.ftp_queue[0][:]
				#ftp_info_list len >1 only when the case from partial ftp info
				#that guessed from many reserved ftp address
				#so once one ftp_info was successfully download
				#quit the for circle
				print("DEBUG start to download ftp_info_list",ftp_info_list)
				file_saved=''
				for ftp_info in ftp_info_list:
					self.v_host.set(ftp_info)
					if DIRECT_DOWNLOAD_STOP:
						DIRECT_DOWNLOAD_STOP = False
						self.button_direct.config\
						(text="Downloading...",bg='orange',relief='sunken',state='normal')
						file_saved = self.direct_download()
						if file_saved:
							self.v_saved_number += 1
							self.l_savein.config(text='%s'%(str(self.v_saved_number) + ' Saved in: '), bg='orange')
							#quit after downloading successuflly
							break
						else:
							printl("try another reserved ftp address...")
							continue

					else:
						printl("Error, another direct download is under processing, you can't start to download this!")
						self.ftp_queue.insert(0,ftp_info_list)
						break

				#record all the download info into ftp_log.txt
				if not file_saved:
					file_saved = "Failed"
				printl("ftp_info: '%s' download result: '%s'"%(str(ftp_info),file_saved))

				self.ftp_queue.pop(0)
				self.v_ftp_number.set(str(len(self.ftp_queue)))

			else:
				pass

			time.sleep(int(self.v_interval.get()))
			interval_count += 1
			print(">>>>Download ftp, count %d" % (interval_count))
		#while
		print("DEBUG download_ftpinfo stopped.")
	############################download_ftpinfo()####################################


	def monitor_ftpinfo(self):
		'''
		get ftp info extracted from mail body
		and the mail comes from read exchange server by read_exchange.py
		'''
		global MONITOR_STOP
		global DIRECT_DOWNLOAD_STOP
		global L_RESERVED_FTP
		global FTP_INFO_HISTORY
		global MUTEXT

		interval_count = 0
		find_folder = "inbox"

		try:
			acc = self.v_csl.get()
			pwd = self.v_cip.get()
			ser = self.v_exserver.get()
			mail = self.v_mail_k_add.get()
			my_ol = read_exchange.MY_OUTLOOK(acc, pwd, ser, mail)
		except Exception as e:
			printl("Error exchanger account: {} connecting failed: {}".format(mail,e))
		else:

			printl("Start monitoring exchange account %s"% mail)
			del_html = re.compile(r'<[^>]+>',re.S)
			while 1:
				if MONITOR_STOP or (not self.running):
					break

				for mail_item in my_ol.find_mail(self.v_mail_k.get()):
					if not mail_item:
						break
					else:
						#sound a bell
						self.l_savein.bell()
						#Extract ftp info and then start to download 
						plain_body = del_html.sub('',mail_item.body)
						#print("DEBUG plain_body:",plain_body)
						ftp_info = self.extract_ftp_info(plain_body, from_mail=True)

						if (ftp_info != None) and (ftp_info not in FTP_INFO_HISTORY):
							FTP_INFO_HISTORY.append(ftp_info)
						else:
							print("DBUEG already handled ftp_info")
							continue

						#only dirname case:
						try_ftp_list = []
						if ftp_info != None and ftp_info.HOST == '' and ftp_info.ACC == '' and ftp_info.DIRNAME != '':
							#use reserved ftp info to combine this dirname to try:

							for ftp_addr in L_RESERVED_FTP:
								#here is it necessary to add the '\r' ending?
								s = ftp_addr + ftp_info.DIRNAME + '\r'
								if 'unicode' in str(type(s)):
									s = s.encode('utf-8')
								try_ftp_list.append(s)
							#is here necessary to do the mutex?yes
							self.ftp_queue.append(try_ftp_list[:])


						#for the full ftp case
						elif ftp_info != None and ftp_info.HOST != '' and ftp_info.ACC != '':
							printl("Detected ftp_info:{}".format(ftp_info))
							#FTP_INFO = collections.namedtuple("FTP_INFO", "HOST PORT ACC PWD DIRNAME")
							#must add '\\r' because extract_ftp_info use this as an end
							s = r"ftp://"+ftp_info.ACC+":"+ftp_info.PWD+"@"+ftp_info.HOST+":"+\
							ftp_info.PORT+ftp_info.DIRNAME + '\r'
							if 'unicode' in str(type(s)):
								s = s.encode('utf-8')
							self.ftp_queue.append([s])
						else:
							print("DEBUG error, should no such case")
							pass

					self.v_ftp_number.set(str(len(self.ftp_queue)))
					sub = mail_item.subject
					printl("Detect a ftp_info: %s from mail: %s"%(str(ftp_info),sub))
				#end for
				time.sleep(int(self.v_interval.get()))
				interval_count += 1
				print("Monitor ftp>>>>, count %d"\
				 % (interval_count))
			#end while

		MONITOR_STOP = True
		self.button_monitor.config(text="Start monitor",bg='white',relief='raised',state='normal')
	#############monitor_ftpinfo()#############


	def start_monitor_download(self):
		global MONITOR_STOP

		if MONITOR_STOP:
			MONITOR_STOP = False
			self.button_monitor.config(text="Monitoring...",bg='orange', relief='sunken',state='normal')
			t_monitor = threading.Thread(target=self.monitor_ftpinfo)
			t_download = threading.Thread(target=self.download_ftpinfo)
			#for terminating purpose
			MONITOR_THREADS.append(t_monitor)
			MONITOR_THREADS.append(t_download)
			t_monitor.start()	
			t_download.start()	
			print("DEBUG threads monitor {} and download {} start".format(t_monitor,t_download))

			#Here to start another consumer thread to trigger those ftp
		else:
			MONITOR_STOP = True
			self.button_monitor.config(text="Stopping..",bg='orange', relief='sunken',state='disable')
			terminate_threads(MONITOR_THREADS)
			printl("Monitor is terminated")
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

		res = askyesnocancel("Mail Monitor","(Recommended)Save current configurations?", parent=ftp_top)
		if res:
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
			#do not save password
			#self.v_cip.set('')
			AD4_PWD = self.v_cip.get()

			save_bak()
		elif res == False:
			pass
		else:
			#'cancel' nothing to do
			return

		printl("'Mail Monitor exited'\n")
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

		l_thr = []
		l_thr.extend(MONITOR_THREADS)
		l_thr.extend(DIRECT_DOWNLOAD_THREADS)
		l_thr.extend(PROGRESS_THREADS)
		terminate_threads(l_thr)
		for l in l_thr:
			if l.is_alive():
				l._Thread__stop()


		'''
		print("DEBUG my_ftp threads status:")
		print("Direct threads:",DIRECT_DOWNLOAD_THREADS)
		print("monitor threads:",MONITOR_THREADS)
		print("Progress threads:",PROGRESS_THREADS)
		print("self.running:",self.running)
		print("DEBUG askquit finished")
		'''
	###########init()##############		


def main():
	cstart = time.clock()

	test_top = Tk()
	test_top.withdraw()
	ftp_top = My_Ftp(test_top)

	cend = time.clock()
	print("'Startup time costs: %.2f seconds.'"%(cend-cstart))
	test_top.mainloop()

if __name__ == '__main__':

	main()

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

