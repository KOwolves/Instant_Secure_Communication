from tkinter import *
import time
import socket
from threading import Thread
from tkinter import scrolledtext
from tkinter import messagebox
import AES
import hashlib
#----------------------------------------------------------
#udpSocket = None
#destIp = ""
#destPort = 0

def chatting(destIp,destPort,itsId,myId,chatkey):
    # ----------------------------------------------------------------------

    #def connect():
    #    udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #    udpSocket.bind(("", 7777))
    #    return udpSocket


    def msgshow(ID,sendInfo):  #显示对话信息
        msg = ID + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) + '\n'
        txt_msglist.insert(END, msg, 'green')  # 添加时间
        txt_msglist.insert(END, sendInfo)  # 获取发送消息，添加文本到消息列表
        #txt_msgsend.delete('0.0', END)  # 清空发送消息


    def sendData(udpSocket,destIp,destPort):  #消息发送函数
        sendInfo = txt_msgsend.get('0.0', END)
        # sendInfo = AES.encrypt(kkey, sendInfo)
        sendc = AES.encrypt(chatkey, sendInfo)  #将消息进行加密之后传输
        h = hashlib.md5()
        h.update(sendc.encode("utf-8"))
        md = h.hexdigest()
        md = "############" + md
        all_msg = (sendc + md).encode("utf-8")
        udpSocket.sendto(all_msg, (destIp, destPort))
        msgshow(myId, sendInfo)
        txt_msgsend.delete('0.0', END)  # 清空发送消息


    def recvData():  #接收好友的对话消息
        #print(s._closed())

            while True:
                if not s._closed:
                    try:
                        recvInfo = s.recvfrom(1024)
                    except:
                        break
                    print(recvInfo)
                    if recvInfo:  #对收到的消息进行验证
                        #print(recvInfo)
                        cnt = 0
                        for i in range(1024):
                            #print(cnt)

                            if cnt == 12:
                                break
                            if chr(recvInfo[0][i]) == '#':
                                #print("here1")
                                cnt = cnt + 1
                            if chr(recvInfo[0][i]) != '#':
                                #print("here")
                                cnt = 0
                        #print(cnt)
                        temp = i
                        if (cnt != 12):
                            # print("here")
                            print("MD5验证失败")
                        else:
                            hh = hashlib.md5()
                            hh.update((recvInfo[0][0:temp - 12]))
                            recv_md5 = hh.hexdigest()

                            for i in range(len(recv_md5)):
                                if (recv_md5[i] != chr(recvInfo[0][i + temp])):
                                    print("MD5验证失败！")
                                    break
                            if (i == len(recv_md5) - 1):  #将收到的消息解密后进行显示
                                print("MD5验证成功！")
                                #print(chatkey)
                                #print(type(recvInfo[0].decode("utf-8")))
                                recvm = AES.decrypt(chatkey, recvInfo[0].decode("utf-8"))
                                #print("here!")
                                msgshow(itsId, recvm)

    '''定义取消发送消息函数'''

    def cancel():
        txt_msgsend.delete('0.0', END)  # 取消发送消息，即清空发送消息

    '''绑定up键'''


    def msgsendEvent(event):
        if event.keysym == 'Up':
            #msgshow()
            sendData(s,destIp,destPort)

    def closechatwindow(s):
        ok = messagebox.askyesno(title='提示', message='是否关闭聊天界面？')
        if ok == True:
            print('连接断开')
            s.close()
            tk.destroy()

    # ------------------------------------------------------------------------------
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # s套接字绑定7777端口，作为双方通信的端口
    print('链接')
    s.bind(("", 7777))

    tk = Tk()
    tk.title(itsId)
    tk.geometry('900x800')

    '''创建画布'''
    canvas = Canvas(tk, bg='#FFFAF0', height=660, width=250)

    '''好友信息文本框'''
    canvas.create_text(10, 126, text='\n好友ID:%s\n\n好友IP:%s\n'%(itsId,destIp), anchor='nw', justify=LEFT, font='等线')
    canvas.create_text(10, 446, text='\n我的ID:%s\n'%myId, anchor='nw', justify=LEFT, font='等线')

    '''创建分区'''
    main_frame = Frame(tk)
    f_msglist = Frame(tk,height=350, width=500)  # 创建<消息列表分区 >
    f_msgsend = Frame(tk,height=150, width=500)  # 创建<发送消息分区 >
    f_floor = Frame(tk,height=100, width=500)  # 创建<按钮分区>
    f_right = Frame(tk,height=600, width=200)  # 创建<图片分区>
    '''创建控件'''

    txt_msglist = scrolledtext.ScrolledText(f_msglist, height=35, width=100, bg="#F5F5F5", bd=0)
    # 消息列表分区中创建文本控件

    txt_msglist.tag_config('green', foreground='pink')  # 消息列表分区中创建标签
    txt_msgsend = Text(f_msgsend, height=15, width=100, bg="#FFFFF0", bd=0)  # 发送消息分区中创建文本控件
    txt_msgsend.bind('<KeyPress-Up>', msgsendEvent)  # 发送消息分区中，绑定‘UP’键与消息发送。
    '''txt_right = Text(f_right) #图片显示分区创建文本控件'''
    button_send = Button(f_floor, text='Send', bd=0, bg='YellowGreen', width=8, font='等线',command=lambda:sendData(s,destIp,destPort))  # 按钮分区中创建按钮并绑定发送消息函数
    button_cancel = Button(f_floor, text='Cancel', bd=0, bg='white', width=8, font='等线',command=lambda:cancel())  # 分区中创建取消按钮并绑定取消函数
    button_close = Button(f_floor, text='Close', bd=0, bg='white', width=8, font='等线',command=lambda:closechatwindow(s))  #退出聊天窗口


    '''分区布局'''
    f_msglist.grid(row=0, column=0)  # 消息列表分区
    f_msgsend.grid(row=1, column=0)  # 发送消息分区

    f_floor.grid(row=2, column=0)  # 按钮分区
    canvas.grid(row=0, column=3, rowspan=3)  # 图片显示分区
    txt_msglist.grid()  # 消息列表文本控件加载
    txt_msgsend.grid()  # 消息发送文本控件加载
    button_send.grid(row=0, column=0, sticky=W)  # 发送按钮控件加载
    button_cancel.grid(row=0, column=1, sticky=W)  # 取消按钮控件加载
    button_close.grid(row=0, column=2, sticky=W)  #关闭窗口按钮控件加载
    #label.grid()  # 右侧分区加载标签控件

    #tk.protocol('WM_DELETE_WINDOW', closechatwindow(s))
    tr = Thread(target=recvData,args=())
    tr.start()
    #canvas.mainloop()
    tk.mainloop()
    #tr.join()

if __name__ == '__main__':
    chatting('1','1','127.0.0.1',5555,'1')