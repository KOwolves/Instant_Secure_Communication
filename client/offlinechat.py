import socket
from tkinter import *
from tkinter import messagebox
import time
from PIL import Image, ImageTk
import time
import re

def send(myId,itsId):  #离线消息发送函数
    Server_ip = '10.21.170.91'
    tk = Tk()
    tk.geometry("444x225")
    tk.title("离线留言")
    background = Frame(tk, bg='#ADD8E6')
    background.grid()
    f = StringVar()

    def messagesend(Server_ip, en,myId,itsId):
        data = en.get()
        #print(222)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  #与服务器进行TCP连接
        s.connect((Server_ip, 55555))
        #print(333)
        msg1 = ('6' + '|' + myId+'/'+itsId).encode()  #即将发送离线消息的标志位,将 str 类型转换成 bytes 类型
        #print(destIp)
        # #发送的离线消息，包括发送方id，时间和内容
        data = (myId + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) + ':' + '\n' +data).encode()
        s.send(msg1)
        s.send(data)
        reply = s.recv(1024)  #收到的返回值
        if reply.decode() == '16':
            messagebox.showinfo(title="Attention", message="离线消息传输成功")
        else:
            messagebox.showinfo(title="Attention", message="离线消息传输失败")
        s.close()

    #界面
    p1 = Frame(background, width=300, height=25, bg='#ADD8E6')
    p2 = Frame(background, width=300, height=50, bg='#ADD8E6')
    p3 = Frame(background, width=300, height=50, bg='#ADD8E6')
    p1.grid(row=1, column=1, padx=72, pady=20)
    p2.grid(row=2, column=1, padx=72, pady=20)
    p3.grid(row=3, column=1, padx=72, pady=20)
    p1.grid_propagate(0)
    p2.grid_propagate(0)
    p3.grid_propagate(0)
    Label(p1, bg='#ADD8E6', fg='white', text="请留言", font=('等线', 15), anchor='center').grid(row=0, column=0,rowspan=2, sticky=NSEW)
    en=Entry(p2, bd=0, width=40)
    en.grid(row=0, column=0, columnspan=2, sticky=NSEW)
    Button(p3, bg='#87CEEB', bd=0, fg='white', text="发送", font=('等线', 15), width=16, command=lambda :messagesend(Server_ip,en,myId,itsId),anchor='center').pack()
    #print('sending {}'.format(photo))


    tk.mainloop() #mainloop方法最后执行，将标签显示在屏幕，进入等待状态（注：若组件未打包，则不会在窗口中显示），准备响应用户发起的GUI事件

if __name__  == '__main__':
    a = send('a','b')