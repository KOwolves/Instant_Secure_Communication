import socket, select, threading
from tkinter import *
from tkinter import messagebox
import groupchatting
from tkinter import scrolledtext
import time
#host = socket.gethostname()
host = ''
Server_ip = '10.21.170.91'
addr = (Server_ip, 55555)
ports = []
c = ['#9370DB', '#062F4F', 'white', '#EEAA7B', '#E37222']



def groupchoose(s,name):
    print('here')
    tk =Tk()

    def enter_group(s,en):
        group_number = en.get()
        msg = '99' + '|' +  name +'@@@'+group_number
        s.send(msg.encode())
        return_message = s.recv(1024).decode()
        messagebox.showwarning(title='Attention', message='%s' % return_message)
        print(return_message)
        print(type(return_message))
        #if(return_message == 'welcome into the chatting room'):
        #    print('success')
        groupchatting.start_group_chat(group_number,s,name)
        print(msg)

        '''输入群聊号码界面'''
    tk.geometry("444x225")
    tk.title("请输入群号")
    background = Frame(tk, bg='#ADD8E6')
    background.grid()
    p1 = Frame(tk, width=300, height=25, bg='#ADD8E6')
    p2 = Frame(tk, width=300, height=50, bg='#ADD8E6')
    p3 = Frame(tk, width=300, height=50, bg='#ADD8E6')
    p1.grid(row=1, column=1, padx=72, pady=20)
    p2.grid(row=2, column=1, padx=72, pady=20)
    p3.grid(row=3, column=1, padx=72, pady=20)
    p1.grid_propagate(0)
    p2.grid_propagate(0)
    p3.grid_propagate(0)
    Label(p1, bg='#ADD8E6', fg='white', text="请输入群聊号码", font=('等线', 15), anchor='center').grid(row=0, column=0,
                                                                                               rowspan=2,
                                                                                               sticky=NSEW)
    en = Entry(p2, bd=0, width=40)
    en.grid(row=0, column=0, columnspan=2, sticky=NSEW)
    Button(p3, bg='#87CEEB', bd=0, fg='white', text="发送", font=('等线', 15), width=16,
           command=lambda: enter_group(s, en), anchor='center').pack()
    tk.mainloop()
    enter_group(s, en)


