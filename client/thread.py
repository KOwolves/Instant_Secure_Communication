from tkinter import *
import time
import socket
from threading import Thread
from tkinter import scrolledtext
import hashlib
import AES
import key

'''
定义消息发送函数：
1、在<消息列表分区>的文本控件中实时添加时间；
2、获取<发送消息分区>的文本内容，添加到列表分区的文本中；
3、将<发送消息分区>的文本内容清空。
'''
#----------------------------------------------------------
udpSocket = None
destIp = ""
destPort = 0
count = 0
chatkey = ""

# ----------------------------------------------------------------------
def connect():
    global destIp
    global destPort
    global udpSocket
    destIp = "10.21.170.91"
    #input("对方的IP：")
    destPort = 8083 #int(input("对方的端口："))
    udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udpSocket.bind(("", 8082))


def msgshow(ID,sendInfo):
    msg = ID + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) + '\n'
    txt_msglist.insert(END, msg, 'green')  # 添加时间
    txt_msglist.insert(END, sendInfo)  # 获取发送消息，添加文本到消息列表
    txt_msgsend.delete('0.0', END)  # 清空发送消息


def sendData():
    global count
    global chatkey
    if count == 0:
        chatkey = key.send_key()
        print("chatkey"+chatkey)
        udpSocket.sendto(chatkey.encode("gb2312"), (destIp, destPort))
        count = 1
    else:
        sendInfo = txt_msgsend.get('0.0', END)
        print(sendInfo)

        sendc=AES.encrypt(chatkey,sendInfo)
        h=hashlib.md5()
        h.update(sendc.encode("gb2312"))
        md=h.hexdigest()
        md="############"+md
        all_msg=(sendc+md).encode("gb2312")
        udpSocket.sendto(all_msg, (destIp, destPort))
        msgshow('blabla', sendInfo)


def recvData():
    global count
    global chatkey
    while True:
        print("count = %d" %count)

        recvInfo = udpSocket.recvfrom(1024)
        if count == 0:
            chatkey = recvInfo[0].decode("gb2312")
            count = 1
        else:
            if recvInfo:
                print(recvInfo)
                cnt = 0
                for i in range(1024):
                    print(cnt)

                    if cnt == 12:
                        break
                    if chr(recvInfo[0][i]) == '#':
                        print("here1")
                        cnt = cnt + 1
                    if chr(recvInfo[0][i]) != '#':
                        print("here")
                        cnt = 0
                print(cnt)
                temp = i
                if (cnt != 12):
                    #print("here")
                    print("MD5验证失败")
                else:
                    hh = hashlib.md5()
                    hh.update((recvInfo[0][0:temp - 12]))
                    recv_md5 = hh.hexdigest()

                    for i in range(len(recv_md5)):
                        if (recv_md5[i] != chr(recvInfo[0][i + temp])):
                            print("MD5验证失败！")
                            break
                    if (i == len(recv_md5) - 1):
                        print("MD5验证成功！")
                        print(chatkey)
                        print(type(recvInfo[0].decode("gb2312")))
                        recvm = AES.decrypt(chatkey, recvInfo[0].decode("gb2312"))
                        print("here!")
                        msgshow('w老板', recvm)
        #print(">>%s%s"%(recvInfo[1],recvInfo[0].decode("gb2312")))  # .decode("gb2312")

'''定义取消发送 消息 函数'''


def cancel():
    txt_msgsend.delete('0.0', END)  # 取消发送消息，即清空发送消息


'''绑定up键'''


def msgsendEvent(event):
    if event.keysym == 'Up':
        msgshow()


# ------------------------------------------------------------------------------
connect()  # 创建socket

tk = Tk()
tk.title('blabla')
tk.geometry('900x800')

'''创建画布'''
canvas = Canvas(tk, bg='#FFFAF0', height=660, width=250)
'''打开图片文件'''
image_head1 = PhotoImage(file=r'C:\Users\diandian\Desktop\head1.gif')
head1 = canvas.create_image(0, 0, anchor='nw', image=image_head1)
image_head2 = PhotoImage(file=r'C:\Users\diandian\Desktop\head2.gif')
head2 = canvas.create_image(0, 320, anchor='nw', image=image_head2)
'''好友信息文本框'''
canvas.create_text(10, 126, text='\n好友姓名：\n\n好友IP:\n', anchor='nw', justify=LEFT,font='等线')
canvas.create_text(10, 446, text='\n我的姓名：\n\n本地IP:\n', anchor='nw', justify=LEFT,font='等线')



'''创建分区'''
main_frame = Frame(tk)
f_msglist = Frame(height=350, width=500)  # 创建<消息列表分区 >
f_msgsend = Frame(height=150, width=500)  # 创建<发送消息分区 >
f_floor = Frame(height=100, width=500)  # 创建<按钮分区>
f_right = Frame(height=600, width=200)  # 创建<图片分区>
'''创建控件'''

txt_msglist = scrolledtext.ScrolledText(f_msglist, height=35, width=100, bg="#F5F5F5", bd=0)
# 消息列表分区中创建文本控件

txt_msglist.tag_config('green', foreground='pink')  # 消息列表分区中创建标签
txt_msgsend = Text(f_msgsend,height=15, width=100, bg="#FFFFF0", bd=0)  # 发送消息分区中创建文本控件
txt_msgsend.bind('<KeyPress-Up>', msgsendEvent)  # 发送消息分区中，绑定‘UP’键与消息发送。
'''txt_right = Text(f_right) #图片显示分区创建文本控件'''
button_send = Button(f_floor, text='Send', bd=0, bg='YellowGreen', width=8, font='等线', command=sendData)  # 按钮分区中创建按钮并绑定发送消息函数
button_cancel = Button(f_floor, text='Cancel', bd=0, bg='white',width=8, font='等线', command=cancel)  # 分区中创建取消按钮并绑定取消函数
photo = PhotoImage(file=r'C:\Users\diandian\Desktop\ts.txt')
label = Label(f_right, image=photo)  # 右侧分区中添加标签（绑定图片）
label.image = photo

'''分区布局'''
f_msglist.grid(row=0, column=0)  # 消息列表分区
f_msgsend.grid(row=1, column=0)  # 发送消息分区

f_floor.grid(row=2, column=0)  # 按钮分区
canvas.grid(row=0, column=3, rowspan=3) # 图片显示分区
txt_msglist.grid()  # 消息列表文本控件加载
txt_msgsend.grid()  # 消息发送文本控件加载
button_send.grid(row=0, column=0, sticky=W)  # 发送按钮控件加载
button_cancel.grid(row=0, column=1, sticky=W)  # 取消按钮控件加载
label.grid()  # 右侧分区加载标签控件


tr = Thread(target=recvData)

tr.start()
canvas.mainloop()
tk.mainloop()
#tr.join()
