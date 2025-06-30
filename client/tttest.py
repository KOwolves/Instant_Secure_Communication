import time
from tkinter import scrolledtext
from threading import Thread
from tkinter import *
from tkinter import messagebox
import socket
Server_ip = '10.21.170.91'
addr = (Server_ip, 55555)
myId = ''
def msgshow(ID, sendInfo):
    msg = ID + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) + '\n'
    txt_msglist.insert(END, msg, 'green')  # 添加时间
    txt_msglist.insert(END, sendInfo)  # 获取发送消息，添加文本到消息列表
    # txt_msgsend.delete('0.0', END)  # 清空发送消息
def talk(myId):


    '''
    info = txt_msgsend.get('0.0', END)
    info = txt_msgsend.get('0.0', END)
    msgshow(myId, info)
    txt_msgsend.delete('0.0', END)
    print(info)
    '''
    sendInfo = txt_msgsend.get('0.0', END)
    # sendInfo = AES.encrypt(kkey, sendInfo)

    msgshow(myId, sendInfo)
    txt_msgsend.delete('0.0', END)  # 清空发送消息
'''绑定up键'''
def msgsendEvent(event):
    if event.keysym == 'Up':
        talk( myId)
    '''取消发送消息，即清空发送消息'''
def cancel():
    txt_msgsend.delete('0.0', END)
'''关闭聊天窗口'''
def closechatwindow(s):
    ok = messagebox.askyesno(title='提示', message='是否关闭聊天界面？')
    if ok == True:
        print('连接断开')
        s.close()
        tk.destroy()

tk = Tk()
tk.title('群聊')
tk.geometry('900x800')
'''创建画布'''
canvas = Canvas(tk, bg='#FFFAF0', height=660, width=250)

'''创建分区'''
main_frame = Frame(tk)
f_msglist = Frame(tk, height=350, width=500)  # 创建<消息列表分区 >
f_msgsend = Frame(tk, height=150, width=500)  # 创建<发送消息分区 >
f_floor = Frame(tk, height=100, width=500)  # 创建<按钮分区>
f_right = Frame(tk, height=600, width=200)  # 创建<图片分区>
'''创建控件'''

txt_msglist = scrolledtext.ScrolledText(f_msglist, height=35, width=100, bg="#F5F5F5", bd=0)
# 消息列表分区中创建文本控件

txt_msglist.tag_config('green', foreground='pink')  # 消息列表分区中创建标签
txt_msgsend = Text(f_msgsend, height=15, width=100, bg="#FFFFF0", bd=0)  # 发送消息分区中创建文本控件
txt_msgsend.bind('<KeyPress-Up>', msgsendEvent)  # 发送消息分区中，绑定‘UP’键与消息发送。
'''txt_right = Text(f_right) #图片显示分区创建文本控件'''
button_send = Button(f_floor, text='Send', bd=0, bg='YellowGreen', width=8, font='等线',
                     command=lambda: talk( myId))  # 按钮分区中创建按钮并绑定发送消息函数
button_cancel = Button(f_floor, text='Cancel', bd=0, bg='white', width=8, font='等线',
                       command=lambda: cancel())  # 分区中创建取消按钮并绑定取消函数
button_close = Button(f_floor, text='Close', bd=0, bg='white', width=8, font='等线',
                      command=lambda: closechatwindow(s))  # 退出聊天窗口

'''分区布局'''
f_msglist.grid(row=0, column=0)  # 消息列表分区
f_msgsend.grid(row=1, column=0)  # 发送消息分区

f_floor.grid(row=2, column=0)  # 按钮分区
canvas.grid(row=0, column=3, rowspan=3)  # 图片显示分区
txt_msglist.grid()  # 消息列表文本控件加载
txt_msgsend.grid()  # 消息发送文本控件加载
button_send.grid(row=0, column=0, sticky=W)  # 发送按钮控件加载
button_cancel.grid(row=0, column=1, sticky=W)  # 取消按钮控件加载
button_close.grid(row=0, column=2, sticky=W)  # 关闭窗口按钮控件加载

tk.mainloop()
