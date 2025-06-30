import socket
from tkinter import *
from tkinter import scrolledtext
def get_offline_msg(myId):  #获取离线消息
    Server_ip = '10.21.170.91'
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((Server_ip, 55555))  #跟服务器进行连接
    msg = '20'+'|'+myId  #请求离线消息标志位
    s.send(msg.encode())
    data = s.recv(1024).decode()  #获得的离线消息
    s.close()
    print(data)

    tk = Tk()
    tk.title('离线消息')
    tk.geometry('800x800')
    '''
    main_frame = Frame(tk)
    f_msglist = Frame(main_frame, height=350, width=500)  # 创建<消息列表分区 >
   '''

    txt_msglist = scrolledtext.ScrolledText(tk, height=35, width=100, bg="#F5F5F5", bd=0)
    txt_msglist.grid()
    txt_msglist.insert(END, data)  #显示离线消息

    tk.mainloop()