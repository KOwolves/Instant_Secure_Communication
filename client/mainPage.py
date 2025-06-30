from tkinter import *
from tkinter import messagebox
from threading import *
import time
import friend
import sendmessage
import main_interface
import socket
import getData
import chatting
from getData import *
import RSA
import file_recv
from offlinemsg import *
from time import sleep
import group_option
import sys
import creategroup
'''7777是聊天端口，6666是监听端口，2222是发起聊天的端口（即2222给6666发起聊天申请，6666监听到聊天申请后，双方使用7777与彼此通信）'''

c = ['#ADD8E6', '#062F4F', 'white', '#EEAA7B', '#E37222']

def mainP(root,name):
    def frdView():  #好友列表显示函数
        homeFrm.grid_forget()
        frdFrm.grid()
        msgFrm.grid_forget()
        friend.frdList(frdFrm, name)

    def logoff(sock):  #账号注销函数
        ok = messagebox.askyesno(title="提示", message="是否注销账号")
        if ok == True:
            sock.close()
            homeFrm.destroy()
            frdFrm.destroy()
            msgFrm.destroy()
            root.geometry('360x300')
            main_interface.enterSystem(root)

            tag = '14' #用户申请下线时发给服务器的信息标识
            msg = tag + '|' + name

            #response = sendmessage.sendMsg(msg)



    def homeP(page,sock):  #主页显示函数
        p1 = Frame(page, width=216, height=130, bg=c[0])
        p2 = Frame(page, width=300, height=70, bg=c[0])
        p3 = Frame(page, width=300, height=60, bg=c[0])
        p4 = Frame(page, width=300, height=60, bg=c[0])
        p5 = Frame(page, width=300, height=60, bg=c[0])
        p6 = Frame(page,width = 300,height =60,bg=c[0])
        p1.grid(row=0, column=0, padx=96, pady=60, columnspan=2)
        p2.grid(row=2, column=0)
        p3.grid(row=3, column=0)
        p4.grid(row=4, column=0)
        p5.grid(row=5, column=0)
        p6.grid(row=6, column=0)
        p1.grid_propagate(0)
        p2.grid_propagate(0)
        p3.grid_propagate(0)
        p4.grid_propagate(0)
        p5.grid_propagate(0)
        p6.grid_propagate(0)
        #点击Button控件后跳转到相应的command函数
        Label(p1, bg=c[0], fg=c[1], text='Hello', font=("等线", 40, 'bold'), anchor='center', width=5).grid(row=0,
                                                                                                          column=0,
                                                                                                          rowspan=4,
                                                                                                          sticky=NSEW)
        Label(p1, bg=c[0], fg=c[1], text='User:' + name, font=("等线", 15, 'bold'), anchor='center', width=15).grid(row=4,
                                                                                                                  column=0,
                                                                                                                  pady=10,
                                                                                                                  )
        Button(p2, bg='#87CEEB', bd=0, fg='white', text='好 友 列 表', width=25, command=frdView, font=('等线', 15, 'bold'),
               anchor='center').grid(column=1, pady=10, padx=10, sticky=NSEW)
        Button(p3, bg='#87CEEB', bd=0, fg='white', text='离 线 消 息', width=25, command=lambda :get_offline_msg(name),font=('等线', 15, 'bold'),
               anchor='center').grid(column=1, pady=10, padx=10, sticky=NSEW)
        #Button(p4, bg='#87CEEB', bd=0, fg='white', text='注    销', width=25, command=lambda:logoff(sock), font=('等线', 15, 'bold'),
               #anchor='center').grid(column=1, pady=10, padx=10, sticky=NSEW)
        Button(p4, bg='#87CEEB', bd=0, fg='white', text='群 聊', width=25, command=lambda: group_option.Option_list(name),
               font=('等线', 15, 'bold'),
               anchor='center').grid(column=1, pady=10, padx=10, sticky=NSEW)
    def homeView(sock):
        homeP(homeFrm,sock)
        homeFrm.grid()
        frdFrm.grid_forget()
        msgFrm.grid_forget()
    def reactApp(listen,name):  #主页面生成后对监听到的消息进行相应的函数
        flag=-1
        while True:

            if listen._closed == True:
                break
            try:
                Info = listen.recvfrom(1024)
            except:
                break
            #print(Info)
            #print(flag,type(flag))
            flag = Info[0].decode()
            flag = flag.split('/')
            itsId = flag [1]
            #print(flag)
            if flag[0] == '1':#接收到新的消息
                ok = messagebox.askyesno(title='提示',message=itsId+'向您申请对话，是否同意？')
                if ok==True:
                    #itsT=Toplevel()
                    Ip = Info[1][0]
                    print(Ip)
                    Port = int(Info[1][1])
                    key = listen.recvfrom(1024)
                    key = key[0]
                    chatting.chatting(Ip,7777,flag[1],name,RSA.decrypt(name,key))
                flag=-1
            elif flag[0] == '2':  #接收到传输文件
                ok = messagebox.askyesno(title='提示',message=itsId + '向您传输文件，是否接收？')
                if ok ==True:
                    listen.sendto('ok'.encode(),(Info[1][0],2222))
                    file_recv.receive()

    def closeSyst():
        ok=messagebox.askyesno(title='提示',message='是否决意退出系统？')
        if ok == True:
            #print('关')
            msg = '14' + '|' + name
            sendmessage.sendMsg(msg)
            messagebox.showerror(title='Attention', message='下线成功！欢迎再来。')
            root.destroy()




    homeFrm=Frame(root,width=360,height=560,bg=c[0])
    frdFrm=Frame(root,width=360,height=560,bg=c[0])
    msgFrm=Frame(root,width=360,height=560,bg=c[0])
    #打开6666监听端口
    listen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen.bind(("", 6666))
    #开启一个线程专门处理监听到的信息
    t=Thread(target=reactApp,args=(listen,name))
    t.setDaemon(True)
    t.start()
    def heart_beat(name):  #向主机发送在线信息，便于主机中用户状态的更新
        beat = '50' + '|' + name
        beat = beat.encode()
        print('heartbeat')
        while True:
            sleep(1.5)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('10.21.170.91', 55555))
            s.send(beat)
            s.close()
    t2=Thread(target=heart_beat, args=(name,))
    t2.setDaemon(True)
    t2.start()
       #def msgView():
    #    homeFrm.grid_forget()
    #    frdFrm.grid_forget()
    #    msgFrm.grid()
        #msgPage.msgList(msgFrm,name)
    homeFrm.grid()
    homeP(homeFrm,listen)
    menubar=Menu(root)
    menubar.add_command(label='主页',command=lambda :homeView(listen))
    menubar.add_command(label='好友',command=frdView)
    #menubar.add_command(label='消息列表',command=msgView)
    root['menu']=menubar
    root.protocol('WM_DELETE_WINDOW',closeSyst)
    #root.mainloop()


def mainpage(root,name):
    mainP(root,name)
