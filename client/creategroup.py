from tkinter import messagebox
import groupchatting
host = '10.122.228.62'
Server_ip = '10.122.204.34'
addr = (Server_ip, 55555)
'''creategroup的功能是创建群聊，返回群聊号，并将群主拉入聊天界面'''
def creategroup(myId,s):
    #标志位66，发送消息给服务器
    msg = '66' + '|' + myId
    try:
        s.send(msg.encode())
    except:
        print('command error')
    try:
    #服务器传送回欢迎消息，弹窗显示
        wel = s.recv(1024).decode()
        messagebox.showwarning(title='Attention', message='%s' % wel)
        wel = wel.split(':')
        gnum = wel[1]

    except:
        print("error ")
    #进入群聊界面
    groupchatting.start_group_chat(gnum,s,myId)
