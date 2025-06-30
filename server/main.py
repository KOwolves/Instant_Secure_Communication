import socket
import time
from offline_msg_recieve import *
from regist_serverside import *
from login_serverside import *
from logout_serverside import *
from request_friend_list import *
from new_friend_serverside import *
from delete_friend_serverside import *
from offline_msg_send import *
import group_chat

# -*- coding:utf-8 -*-

HOST = '127.0.0.1'
PORT = 55555        # 监听的端口 (非系统级的端口: 大于 1023)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(5)
status = {}
# --- Add missing group chat variables ---
GROUP = 1  # Group number counter
contactingnames = {}  # {group_num: [usernames]}
socketmsg = {}        # {group_num: [socket objects]}
groupmsg = {}         # {group_num: [messages]}
# --------------------------------------
while True:
    conn,addr = server.accept()
    data = conn.recv(1024)
    data = data.decode()
    ip = addr[0]

    if not data:
        pass
    else:
        tag,msg = data.split('|')
        present_time = time.time()
        print('发送请求的ip：' + ip)
        name = msg.split('/')[0]
        status[name] = present_time

        if tag == '1':#注册
            flag = regist(msg,ip)
            conn.send(flag.encode())#后期加上公钥
        elif tag == '4':#登录
            flag = login(msg,ip)
            conn.send(flag.encode())
        elif tag == '14':#注销
            logout(msg)
            conn.send('注销成功'.encode())
        elif tag == '9':#加好友
            flag = add_friend(msg)
            conn.send(flag.encode())
        elif tag == '7':#申请在线好友列表
            json = request_friend_list(msg,status)
            conn.send(json.encode())
        elif tag == '12':#删除好友
            flag = delete_friend(msg)
            conn.send(flag.encode())
        elif tag == '6':  # 客户端向服务器发送离线消息
            flag = c_to_s_offline_msg(msg, conn)
            conn.send(flag.encode())
        elif tag == '20': #服务器向客户端发送离线消息
            m = s_to_c_offline_msg(msg)
            conn.send(m.encode())
        elif tag == '50': #心跳检测
            print("heartbeat"+name)
        elif tag == '66':  # 创建群聊
            contactingnames[GROUP] = []
            socketmsg[GROUP] = []
            groupmsg[GROUP] = []
            gnum = GROUP
            group_chat.chatserver(1, conn, gnum, name,groupmsg,socketmsg,contactingnames,GROUP)
            GROUP = GROUP + 1
        elif tag == '99':  # 加入群聊
            gnum = int(msg.split('@@@')[1])
            print(gnum)
            name = msg.split('@@@')[0]
            group_chat.chatserver(2, conn, gnum, name,groupmsg,socketmsg,contactingnames,GROUP)
        elif tag == '22':#接收并广播发送群聊消息
            gnum,name,text = msg.split('@@@')
            gnum = int(gnum)
            # Call the chat function inside chatserver
            group_chat.chatserver.__globals__['chat'](gnum, name, text, conn, socketmsg)