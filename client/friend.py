from tkinter import *
from tkinter import ttk
from tkinter import messagebox
import socket
import getData
from threading import *
import time
import sendmessage
import main_interface
import chatting
import key
import RSA
import file_send
import offlinechat

c = ['#ADD8E6', '#062F4F', 'white', '#EEAA7B', '#E37222']

#更新好友列表
def frdFresh(frm1,frm2,myId):
    while 1:
        time.sleep(2)
        onfrd=getData.getFrdInfo(myId)  #从服务器拿到用户的好友信息
        buildTree(frm1,onfrd,myId)  #构建好友列表

# 好友相关操作：聊天、删除、添加
def operate(itsId,order,myId):
    if order==1:#发消息
        #print("发送消息给"+itsId)
        onfrd=getData.getFrdInfo(myId)
        lenth=len(onfrd)
        destPort = ''
        destIp = ''
        itspublic_key = ''
        for i in range(lenth):
            item = onfrd[i]
            if (item[0] == itsId and item[3] == 1):  #根据用户ID及其在线状态，进一步获取好友的公钥
                destIp = item[1]
                itspublic_key = item[4]
                itspublic_key = itspublic_key.split('%%%')
                itspublic_key = itspublic_key[1]  #获得好友公钥
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  #创建新的套接字，准备对话申请
                s.bind(("", 2222))
                chatkey = key.send_key()  #随机生成对称密钥
                encrpt_chatkey = RSA.encrypt(chatkey, itspublic_key)  #用好友的公钥对对称密钥进行加密
                msg1 = ('1' + '/' + myId).encode()
                msg2 = encrpt_chatkey
                s.sendto(msg1, (destIp, 6666))
                time.sleep(1)
                s.sendto(msg2, (destIp, 6666))
                s.close()
                chatting.chatting(destIp, 7777, itsId, myId, chatkey.encode())  #进入对话函数
                # 传给后台，弹出对话框
                break
            elif(item[0] == itsId and item[3] == 0):  #好友未在线，跳转至离线消息发送函数
                messagebox.showerror("Attention", "好友" + itsId + "未在线")
                offlinechat.send(myId,itsId)
                break


    elif order == 2: #删除好友
        ok=messagebox.askyesno(title="Attention",message="是否删除好友"+itsId)
        if ok==True:
            msg = '12' + '|' + myId + '/' + itsId
            print(msg)
            response = sendmessage.sendMsg(msg)
            if response == '13':
                messagebox.showerror("Attention","好友删除成功")
            #buildTree()
        else:
            messagebox.showerror("Attention", "好吧")
            #传给后台
    elif order == 3:  #文件传输
        onfrd = getData.getFrdInfo(myId)  #获取好友IP
        lenth = len(onfrd)
        destPort = ''
        destIp = ''
        for i in range(lenth):
            item = onfrd[i]
            if (item[0] == itsId and item[3] == 1):  #好友在线，进入文件传输函数
                destIp = item[1]
                file_send.send(destIp,myId)
                break
            elif (item[0] == itsId and item[3] == 0):
                messagebox.showerror("Attention", "好友" + itsId + "未在线，可以选择给他发送离线消息哟~")
                break


    else:#添加好友
        msg = '9' + '|' +  myId + '/' + itsId
        #print(msg)
        response = sendmessage.sendMsg(msg)
        if response == '10':
            messagebox.showinfo(title="Attention", message="好友添加成功")
            #发送好友申请，传给后台
        elif response == '11':
            messagebox.showinfo(title="Error", message="好友添加失败")


#提示弹窗函数
def tipFun(tip,frdId,myId):
    tip.title('提示')
    frm = Frame(tip, width=360, height=300, bg=c[0])
    frm.grid()
    frm.grid_propagate(0)
    p1 = Frame(frm, width=216, height=60, bg=c[0])
    p2 = Frame(frm, width=216, height=50, bg=c[0])
    p3 = Frame(frm, width=216, height=50, bg=c[0])
    p4 = Frame(frm, width=216, height=50, bg=c[0])
    p5 = Frame(frm, width=216, height=50, bg=c[0])
    p6 = Frame(frm, width=216, height=60, bg=c[0])
    p1.grid(row=0, column=0, padx=75, pady=30)
    p2.grid(row=1)
    p3.grid(row=2)
    p4.grid(row=3)
    p5.grid(row=4)
    p6.grid(row=4)
    p1.grid_propagate(0)
    p2.grid_propagate(0)
    p3.grid_propagate(0)
    p4.grid_propagate(0)
    p5.grid_propagate(0)
    p6.grid_propagate(0)

    def choseOrd(itsId, i, myId):  # 选择操作并执行相应函数
        if i != 0:
            operate(itsId, i, myId)
        #tip.destroy()

    Label(p1, bg=c[0], fg=c[2], text='悄悄告诉我\n你想干嘛咧', font=('等线', 16, 'bold'), anchor='center').grid(row=0, column=0,
                                                                                                    sticky=SE, padx=20)
    Button(p2, bd=0, bg=c[1], fg=c[2], text='聊    天', font=('等线', 14), width=17,
           command=lambda: choseOrd(frdId, 1, myId)).grid()
    Button(p3, bd=0, bg=c[1], fg=c[2], text='删    除', font=('等线', 14), width=17,
           command=lambda: choseOrd(frdId, 2, myId)).grid()
    Button(p4, bd=0, bg=c[1], fg=c[2], text='发送文件', font=('等线', 14), width=17,
           command=lambda: choseOrd(frdId, 3, myId)).grid()
    # Button(p5, bd=0, bg=c[1], fg=c[2], text='取    消', font=('等线', 14), width=17,command=lambda: choseOrd(frdId, 0, myId)).grid()


#构建好友列表
def buildTree(root,frdlist,myId):
    #print(frdlist)
    #print(type(frdlist))
    tree=ttk.Treeview(root,height=14,columns=['c1','c2'],show='headings')
    tree.column('c1',width=110,anchor='center')
    tree.column('c2',width=110,anchor='center')
    tree.heading('c1',text='ID')
    tree.heading('c2',text='状态')

    if frdlist == -1:
        #print(frdlist)
        tree.insert('',1,values=('空','空'))
    else:
        lenth = len(frdlist)
        #for i in range(10):
        for i in range(lenth):
            item=frdlist[i]
            #print(item[3])
            if item[3] == 1:
                tree.insert('',i,values=(item[0],'在线'))
            else:
                tree.insert('',i,values=(item[0],'离线'))

    scbar=ttk.Scrollbar(root,command=tree.yview)
    tree.configure(yscrollcommand=scbar.set)
    tree.grid(row=0,column=0,sticky=NSEW)
    tree.grid_propagate(0)
    scbar.grid(row=0,column=1,sticky=NSEW)
    #tree.tag_configure('on',background=c[3])
    items=tree.get_children()
    #for i in range(lenth):
    #    if frdlist[i][1]==1:
    #
    #       tree.item(items[i],tags='on')
    #双击弹出提示窗口
    def tvClick(event):
        for item in tree.selection():
           item_text=tree.item(item,"values")
        frdId=item_text[0]
        print(frdId)
        tip=Toplevel()
        tipFun(tip,frdId,myId)

    tree.bind('<Double-Button-1>',tvClick)

#构建页面布局
def frdList(page,myId):
    p1 = Frame(page, width=216, height=80, bg=c[0])
    p5 = Frame(page, width=360, height=3, bg=c[2])
    p2 = Frame(page, width=216, height=30, bg=c[0])
    p3 = Frame(page, width=216, height=30, bg=c[0])
    frm1 = Frame(page, width=226, height=350, bg=c[0])
    frm2 = Frame(page, width=226, height=350, bg=c[0])
    p1.grid(row=0, column=0, padx=70, pady=30)
    p5.grid(row=1)
    p2.grid(row=2, column=0)
    p3.grid(row=3, column=0, pady=4)
    frm1.grid(row=4, column=0, pady=4)
    frm2.grid(row=5, column=0, pady=5)
    p1.grid_propagate(0)
    p2.grid_propagate(0)
    p3.grid_propagate(0)
    frm1.grid_propagate(0)
    frm2.grid_propagate(0)
    Label(p1, bg=c[0], fg='white', text='输入好友ID,可以添加好友。', font=('等线', 10, 'bold'), anchor='center').grid(row=0, columnspan=2,sticky=NSEW)
    idE = Entry(p1, width=26, textvariable=StringVar, font=('17'))
    idE.grid(row=1, column=0, columnspan=2, pady=2)  # 输入ID的文本框
    btn1 = Button(p1, bg=c[0], fg=c[1], text='添加好友', font=('等线', 11), width=8, anchor='center',command=lambda: operate(idE.get(), 4, myId))
    btn1.grid(row=2, columnspan=2)
    # 好友列表
    Label(p2, bg=c[0], fg='white', text='好 友 列 表 ', font=('等线', 17), anchor='center').grid(row=0, column=0, padx=42)

    # temp_name=main_interface.get_value()
    allfrd = getData.getFrdInfo(myId)  #从服务器获得好友信息
    buildTree(frm1, allfrd, myId)  #建立好友列表
    frm1.grid()
    Label(frm1, bg=c[0], text='双击好友可以发送消息、文件，删除好友。').grid(row=2, column=0, columnspan=4, pady=10)
    #Label(frm2, bg=c[0], text='双击好友可以发送消息、文件，删除好友。').grid(row=2, column=0, columnspan=4, pady=10)

    try:
        frdFreshT=Thread(target=frdFresh,args=(frm1,frm2,myId,))
        frdFreshT.setDaemon(True)
        frdFreshT.start()
    except:
        print('FRIENDLIST FRESH ERROR')


if __name__=='__main__':
    root=Tk()
    root.geometry("360x600")
    root.title("安全即时通信系统")
    f=Frame(root,bg=c[0])
    f.grid()
    frdList(f,main_interface.__name__)
    root.mainloop()