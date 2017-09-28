#!/usr/bin/env python
#!--*--coding:utf-8--*-

from Tkinter import *
import ttk
from tkMessageBox import *

import ftplib
import os
import socket
import threading

HOST = '135.242.80.16'
PORT = '8080'
DOWNLOAD_DIR = '/01_Training/02_PMU/02_Documents'
ACC = ''
PWD = ''
SAVE_DIR = os.getcwd()
CONN = ftplib.FTP()


file_number = 0
dir_number = 0
downloaded_number = 0

def ftp_conn(host, port, acc, pwd):
	print "DEBUG host=",host
	print "DBUEG port = ",port
	try:
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
	print "DEBUG my_download host=",host
	print "DEBUG port = ",port
	os.chdir(save_dir)

	res = ftp_conn(host, port, acc, pwd)

	if not res:
		print "Error to logged in the %s" % host
		showerror(title='Ftp Connect Error', \
			message="Cannot accesst to %s" % host)
		return 


	print "DEBUG waiting for calculate to total file number..."
	m,n = get_file_number(download_dir)
	print "DEBUG total %d files, %d folders to be downloaded" % (n, m)
	ftp_download_dir(download_dir)
	CONN.quit()

	print "DEBUG n = %d, downloaded_number = %d" %(n, downloaded_number)
	if n == downloaded_number:
		print "#########################"
		print "DEBUG Downloaded Success!"	
		print "#########################"

	return os.path.join(save_dir,os.path.basename(download_dir))
#############my_download()########


class My_Ftp(object):
	def __init__(self, parent_top):
		self.parent_top = parent_top
		self.ftp_top = Toplevel(parent_top)
		self.ftp_top.title("Ftp_Downloader")
		self.ftp_top.geometry('700x300+300+220')
		#self.ftp_top.iconbitmap(icon_path)
		self.ftp_top.attributes("-toolwindow", 1)
		#self.ftp_top.wm_attributes('-topmost',1)

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

		self.button_qconn = Button(self.lframe_qconn,text="Direct dowload",\
			width=20,command=self.thread_ftp)	
		self.button_qconn.grid(row=2,column=3)

		#Auto download
		s1 = "Enable mail fiter function to automatically"
		s2 = ""
		s3 ="ftp download logs according to specific mail subject"
		s = s1+s2+s3

		self.v_chk = BooleanVar() 
		self.chk_auto = Checkbutton(self.lframe_autoconn, text = s, variable = self.v_chk,\
			command = self.periodical_check).pack()
		self.label_mail = Label(self.lframe_autoconn, text = 'Keyword in Mail subject:').pack(side=LEFT)
		self.v_mail = StringVar()
		self.entry_mail = Entry(self.lframe_autoconn, textvariable=self.v_mail,width=30)
		self.entry_mail.pack(side=LEFT)

		self.pwindow_qconn.pack()
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
		print "Debug direct_download starts"

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

		my_download(HOST, PORT, ACC, PWD, SAVE_DIR, DOWNLOAD_DIR)

		self.button_qconn.config(text="Direct download",bg='white',relief='raised',state='normal')
	##############direct_download()##################

	def periodical_check(self):
		if self.v_chk.get() == 1:
			print "periodical check started!"
		else:
			print "stopped"	
	########Periodical_check()#####################

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

