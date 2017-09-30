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
import read_olook
import time
import pythoncom 

HOST = '135.242.80.16'
PORT = '8080'
DOWNLOAD_DIR = '/01_Training/02_PMU/02_Documents'
ACC = 'QD-BSC'
PWD = 'qdBSC#1234'
SAVE_DIR = os.getcwd()
CONN = None
DATA_BAK = os.path.join(SAVE_DIR, "my_ftp.pkl")
MAIL_KEYWORD = r'\d-\d{8}'
#MAIL_KEYWORD = '1-6853088'
MY_FTP = collections.namedtuple("MY_FTP",\
 "host port user pwd target_dir mail_keyword")


MONITOR_THREADS = []
MONITOR_STOP = True


file_number = 0
dir_number = 0
downloaded_number = 0


def save_bak():
	data_bak = MY_FTP(HOST, PORT, ACC, PWD, DOWNLOAD_DIR, MAIL_KEYWORD)
	print "data_bak to be saved as:", data_bak
	pickle.dump(data_bak, open(DATA_BAK,"wb"), True)
############save_bak()#####################


def retrive_bak():
	try:
		data_bak = pickle.load(open(DATA_BAK, "rb"))

		print "DEBUG retrive_bak data_bak=",data_bak
		HOST = data_bak.host
		PORT = data_bak.port
		ACC = data_bak.user
		PWD = data_bak.pwd
		DOWNLOAD_DIR = data_bak.target_dir

	except Exception as e:
		print "ERROR occure, e=",e

	else:
		print "Retrive success!"
		print "data_bak = ",data_bak
		return data_bak	
	return None
############retrive_bak()###################



def ftp_conn(host, port, acc, pwd):
	global CONN
	try:
		CONN = ftplib.FTP()
		CONN.connect(host, port)
	except (socket.error, socket.gaierror), e:
		print 'ERROR: cannot reach "%s"' % HOST
		return False
	print '*** Connected to host "%s"'% HOST

	try:
		CONN.login(acc, pwd)
	except ftplib.error_perm:
		print 'ERROR: cannot login as "%s"' % ACC
		f.quit()
		return False
	print '*** Logged in as "%s"' % ACC

	return True
############ftp_conn()#####################


def ftp_download_dir(dirname):
	global downloaded_number

	try:
		CONN.cwd(dirname)
	except ftplib.error_perm:
		print 'ERROR: cannot cd to "%s"' % dirname
	else:
		print("change diretocry into %s..." %dirname)
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
				ftp_download_dir(filelines_bk[i])
				CONN.cwd('..')
				os.chdir('..')
				print("back to upper directory to downlaod....")
			else:
				try:
					CONN.retrbinary('RETR %s' % filelines_bk[i], \
						open(filelines_bk[i], 'wb').write)
				except ftplib.error_perm:
					print 'ERROR: cannot read file "%s"' % FILE
					os.unlink(FILE)
				else:
					downloaded_number += 1
					print("File %s has been downloaded!" % filelines_bk[i])
			i += 1
##################download_dir()###############

def get_file_number(dirname):
	global file_number
	global dir_number
	global CONN

	try:
		CONN.cwd(dirname)
	except ftplib.error_perm:
		print 'ERROR: cannot cd to "%s"' % dirname
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
	os.chdir(save_dir)

	res = ftp_conn(host, port, acc, pwd)


	if not res:
		print "Error to logged in the %s" % host
		print "DEBUG res=",res
		return None


	print "Waiting for calculate to total file number..."
	m,n = get_file_number(download_dir)
	print "Total %d files, %d folders to be downloaded" % (n, m)
	ftp_download_dir(download_dir)
	CONN.quit()

	if n == downloaded_number:
		print "#########################"
		print "DEBUG Downloaded Success!"	
		print "#########################"

	return os.path.join(save_dir,os.path.basename(download_dir))
#############my_download()########


class My_Ftp(object):
	def __init__(self, parent_top):
		global HOST
		global PORT
		global ACC
		global PWD
		global DOWNLOAD_DIR

		self.parent_top = parent_top
		self.ftp_top = Toplevel(parent_top)
		self.ftp_top.title("Ftp_Downloader")
		self.ftp_top.geometry('600x300+300+220')
		#self.ftp_top.iconbitmap(icon_path)
		self.ftp_top.attributes("-toolwindow", 1)
		#self.ftp_top.wm_attributes('-topmost',1)
		self.ftp_top.protocol("WM_DELETE_WINDOW",lambda :self.ask_quit(self.ftp_top))

		blank_label_1 = Label(self.ftp_top, text = '').pack()
		self.pwindow_qconn = ttk.Panedwindow(self.ftp_top, orient=VERTICAL)

		self.lframe_qconn = ttk.Labelframe(self.ftp_top, text='Direct Download',\
		 width= 620, height = 420)
		self.lframe_autoconn = ttk.Labelframe(self.ftp_top, text='Auto Download',\
		 width= 620, height = 420)
		self.pwindow_qconn.add(self.lframe_qconn)
		self.pwindow_qconn.add(self.lframe_autoconn)

		#Host label and entry
		self.label_host = Label(self.lframe_qconn, text = 'Host:').grid(row=0,column=0)
		self.v_host = StringVar()
		self.entry_host = Entry(self.lframe_qconn, textvariable=self.v_host,width=20)
		self.entry_host.grid(row=0,column=1)

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
		s1 = "Enable 'Inbox' mail monitor function to automatically"
		s2 = " "
		s3 ="ftp download files based on mail title"
		s = s1+s2+s3

		self.v_chk = BooleanVar() 
		self.chk_auto = Checkbutton(self.fm_up, text = s, variable = self.v_chk,\
			command = self.periodical_check).pack()
		self.label_mail = Label(self.fm_up, text = 'Mail Title Keyword:    ').pack(side=LEFT)
		##########mail_keyword###########
		self.v_mail = StringVar()
		self.entry_mail = Entry(self.fm_up, textvariable=self.v_mail,width=32)
		self.entry_mail.pack(side=LEFT)

		self.label_blank0 = Label(self.fm_up,text= ' '*20).pack(side = 'left')
		#button trigger monitor mails' titles
		self.button_monitor = Button(self.fm_up, text="Start monitor", command=self.start_thread_monitor, activeforeground\
			='white', activebackground='orange',bg = 'white', relief='raised', width=20)
		#self.button_monitor = Button(self.fm_up,text="Start monitor",\
			#width=20,command=self.start_thread_monitor).pack()	
		self.button_monitor.pack()
		self.fm_up.pack()


		self.fm_down = Frame(self.lframe_autoconn)

		self.label_new = Label(self.fm_down, \
			text = " Monitored Dirname: ",justify='left').pack(side=LEFT)

		self.v_new_dirname = StringVar()
		print "DEBUG self.v_ddirname.get()=",self.v_ddirname.get()
		self.label_new_dirname = Label(self.fm_down, \
			textvariable=self.v_new_dirname,justify='left')
		self.label_new_dirname.pack(side = 'left')

		self.label_blank = Label(self.fm_down,text= ' '*18).pack(side = 'left')
		self.label_new_dirname.pack(side = 'left')
	
		self.fm_down.pack(side='left')

		self.pwindow_qconn.pack()

		#######retrive data from disk#############:
		data_bak = retrive_bak()
		if data_bak:

			self.v_host.set(data_bak.host)
			self.v_port.set(data_bak.port)
			self.v_user.set(data_bak.user)
			self.v_pwd.set(data_bak.pwd)
			self.v_ddirname.set(data_bak.target_dir)
			self.v_mail.set(data_bak.mail_keyword)
		else:
			self.v_host.set(HOST)
			self.v_port.set(PORT)
			self.v_user.set(ACC)
			self.v_pwd.set(PWD)
			self.v_ddirname.set(DOWNLOAD_DIR)	
			self.v_mail.set(MAIL_KEYWORD)
			print "DEBUG data_bak is NONE!!!"
		#######retrive data from disk#############:
		print "DEBUG v_ddirname=",self.v_ddirname.get()
		self.v_new_dirname.set(self.v_ddirname.get() +'/' +'*'+ self.v_mail.get()+'*')

		##############init()###############


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
		global DOWNLOAD_DIR
		print "Direct_download starts"

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

		res = my_download(HOST, PORT, ACC, PWD, SAVE_DIR, DOWNLOAD_DIR)

		if not res:
			print "DEBUG cannot access"
			#crash
			#showerror(title='Ftp Connect Error', message="Cannot accesst to %s" % HOST)
		else:
			print "DEBUG downloaded success in file %s" % res


		self.button_qconn.config(text="Direct download",bg='white',relief='raised',state='normal')
	##############direct_download()##################


	def start_monitor(self, mail_keyword):

		pythoncom.CoInitialize() 



		try:
			my_ol = read_olook.My_Outlook()
			print "debug my_outlook.count =",my_ol.my_outlook.Count
		except Exception as e:
			print "debug outlook initialization failed, e:", e
			return

		print "DEBUG start_monitor"
		print "DEBUG my_ol=",my_ol
		my_subfolder = my_ol.find_subfolder("inbox")
		re_rule = re.compile(mail_keyword, re.I)

		if my_subfolder:
			print 'DEBUG start periodical monitor task'
			while 1:
				mail_title_list = []
				mail_title_list = my_ol.find_mail(my_subfolder, mail_keyword)
				print "Debug conaining keywords {0} mails found:{1}"\
				.format(mail_keyword,mail_title_list)

				#download start
				if mail_title_list:

					for mail_title in mail_title_list:
						new_dirname = os.path.join\
						(DOWNLOAD_DIR, re_rule.search(mail_title).group(0))

						save_dir = my_download(HOST, PORT, ACC, PWD, SAVE_DIR, new_dirname)
						if save_dir:
							if True:
								#send to auto search
								pass
						else:
							print "DEBUG download failed"
				time.sleep(10)
				print "DEBUG after 10 seconds,continue monitor"
				print "DEBUG MONITOR_STOP=",MONITOR_STOP

				if MONITOR_STOP:
					break
		print "Debug CoUninitialize()"
		pythoncom.CoUninitialize()
		print "Debug CoUninitialize()"
		self.button_monitor.config(text="Start monitor",bg='white',relief='raised',state='normal')

	#############start_monitor()#############


	def start_thread_monitor(self):

		global MAIL_KEYWORD
		global MONITOR_STOP

		if self.v_mail.get():
			MAIL_KEYWORD = self.v_mail.get()

		self.button_monitor.config(text="Click to stop",bg='orange', relief='sunken',state='normal')

		if MONITOR_STOP:
			MONITOR_STOP = False

			t = threading.Thread(target=self.start_monitor, args=(MAIL_KEYWORD,))
			#for terminating purpose
			MONITOR_THREADS.append(t)
			t.start()	
		else:
			MONITOR_STOP = True
			self.button_monitor.config(text="Stopping..",bg='orange', relief='sunken',state='disable')
	############start_thread_monitor()#############


	def periodical_check(self):
		if self.v_chk.get() == 1:
			print "periodical check started!"
		else:
			print "stopped"	
	########Periodical_check()#####################

	def ask_quit(self, top):
		global HOST
		global PORT
		global ACC
		global PWD
		global DOWNLOAD_DIR
		global MAIL_KEYWORD

		if askyesno("Tip","Save or not?"):
			#save
			HOST = self.v_host.get()
			PORT = self.v_port.get()
			ACC = self.v_user.get()
			PWD = self.v_pwd.get()
			DOWNLOAD_DIR = self.v_ddirname.get()
			MAIL_KEYWORD = self.v_mail.get()

			save_bak()

		else:
			pass

		top.quit()

	###########init()##############		


if __name__ == '__main__':
	HOST = '135.242.80.16'
	PORT = '8080'
	DOWNLOAD_DIR = '/01_Training/02_PMU/02_Documents'
	ACC = ''
	PWD = ''
	SAVE_DIR = os.getcwd()

	test_top = Tk()
	test_top.withdraw()

	ftp_top = My_Ftp(test_top)
	test_top.mainloop()

