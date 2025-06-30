import groupchoose
from tkinter import messagebox
import socket, select, threading
from tkinter import *
from tkinter import scrolledtext
import time
import creategroup
import groupchoose
host = ''
Server_ip = '10.21.170.91'
addr = (Server_ip, 55555)
c = ['#9370DB', '#062F4F', 'white', '#EEAA7B', '#E37222']
'''群聊的程序从这个开始，首先进入选择界面，有两个按钮，创建聊天和进入聊天'''
def Option_list(myId):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(s)
    try:
        s.connect(addr)
    except:
        print('con error')
    root = Tk()
    root.geometry("360x250")
    root.title("安全即时通信系统")
    f = Frame(root, bg=c[0])
    f.grid()
    '''创建框架'''
    p1 = Frame(root, width=250, height=30, bg=c[0])
    p2 = Frame(root, width=250, height=80, bg=c[0])
    '''安置框架'''
    p1.grid(row=0, column=0, padx=70, pady=70)
    p2.grid(row=1, column=0,padx=70,pady=0)
    '''固定框架位置'''
    p1.grid_propagate(0)
    p2.grid_propagate(0)
    '''设置两个按钮，创建群聊和进入群聊'''
    Button(p1, bd=0, bg='#87CEEB', fg=c[2], text="创建群聊", font=('等线', 15), width=20, command=lambda: creategroup.creategroup(myId,s),
           anchor='center').grid()#创建聊天跳转到creategroup
    Button(p2, bd=0, bg='#87CEEB', fg=c[2], text="进入群聊", font=('等线', 15), width=20, command=lambda: groupchoose.groupchoose(s,myId),
           anchor='center').grid()#选择群聊跳转到groupchoose
    root.mainloop()