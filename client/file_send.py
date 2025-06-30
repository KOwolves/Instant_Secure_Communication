import socket
from tkinter import *
from tkinter import messagebox
from PIL import Image, ImageTk
import time
import re

def send(destIp,myId):
    tk = Tk()
    tk.geometry("444x190")
    tk.title("文件传输")
    background = Frame(tk,bg = '#ADD8E6')
    background.grid()
    f = StringVar()

    def filesend(destIp,en):

        def file_deal(file_path):  # 读取文件
            msg = b''
            try:
                file = open(file_path, 'rb') #rb:读取非文本文件
                msg = file.read()
            except:
                print('error{}'.format(file_path))
            else:
                file.close()
                return msg

        file=en.get()  #获得传输文件的路径
        #print(file)
        data = file_deal(file)   #获取传输文件中的数据
        #print(222)
        file_name = file.split('\\')[-1]
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  #创建向好友发送文件传输请求的套接字
        s.bind(("", 2222))
        #print(333)
        msg1 = ('2' + '/' + myId).encode()
        #print(destIp)
        s.sendto(msg1, (destIp, 6666))
        reply = s.recv(1024)
        #print(444)
        s.close()
        #print(555)
        if 'ok' == reply.decode():  # 确认一下另一用户得到文件长度和文件名数据
            #print('文件信息已确认')
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  #创建新的用于文件传输的套接字
            time.sleep(1)
            sock.connect((destIp, 8888))
            go = 0
            total = len(data)
            #print(total)
            info = (str(total) + '|' + file_name).encode()
            sock.sendall(info)
            configration = sock.recv(1024)
            if 'ok' == configration.decode():
                while go < total:  # 发送文件
                    data_to_send = data[go:go + 1024]  #将数据分段发送
                    sock.send(data_to_send)
                    go += len(data_to_send)
                reply = sock.recv(1024)
                if 'copy' == reply.decode():  #数据发送完成后关闭用于传输的套接字
                    print('{} send successfully'.format(file))
                    sock.close()
                    messagebox.showinfo(title="Attention", message="文件传输成功")
                else:
                    print('send failed')
                    sock.close()
                    messagebox.showerror(title="Attention",message="文件传输失败")

    p1 = Frame(background, width=300, height=25, bg='#ADD8E6')
    p2 = Frame(background, width=300, height=25, bg='#ADD8E6')
    p3 = Frame(background, width=300, height=25, bg='#ADD8E6')
    p1.grid(row=1, column=1, padx=72, pady=20)
    p2.grid(row=2, column=1, padx=72, pady=20)
    p3.grid(row=3, column=1, padx=72, pady=20)
    p1.grid_propagate(0)
    p2.grid_propagate(0)
    p3.grid_propagate(0)
    Label(p1, bg='#ADD8E6', fg='white', text="文件路径：", font=('等线', 15), anchor='center').grid(row=0, column=0,rowspan=2, sticky=NSEW)
    en=Entry(p2, bd=0, width=40)
    en.grid(row=0, column=0, columnspan=2, sticky=NSEW)
    Button(p3, bg='#87CEEB', bd=0, fg='white', text="发送", font=('等线', 15), width=16, command=lambda :filesend(destIp,en),anchor='center').pack()
    #print('sending {}'.format(photo))


    tk.mainloop()

#if __name__  == '__main__':
    #a = send('1.1.1.1')