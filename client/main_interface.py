from tkinter import *
from tkinter import messagebox
from PIL import Image, ImageTk
import sendmessage
import hash
import re
import mainPage
import socket
import RSA_key
import sys
# -*- coding:utf-8 -*-


c = ['#CCFFFF', '#062F4F', '#3333CC', '#EEAA7B', '#E37222'] #定义经常用到的颜色

global onfrd
global conname

def login(root, page):  #登录函数
    uname = StringVar()  #两个文本框获得用户输入的用户名、密码
    pwd = StringVar()

    # 检查帐号密码
    # root.geometry('300x200')
    def loginCheck():
        userid = uname.get()
        global conname
        conname=userid
        password = pwd.get()

        if (userid == '') | (password == ''):  # 用户id或密码为空
            messagebox.showerror(title="错误", message="用户名和密码不能为空！")

        else:
            hostname = socket.gethostname()  #获得本机的ip，随后传输给服务器
            hostip = socket.gethostbyname(hostname)
            #将标志位、用户名、密码的哈希值、本机IP作为信息传给服务器
            #4为用户登录时发给服务器的信息标识
            msg = '4' + '|' + userid + '/' + hash.hash_test(password) + '/' + hostip #hash.hash_test(password)
            response = sendmessage.sendMsg(msg)
            #print(response)
            # 登录验证
            if response == '6':  # 用户不存在
                messagebox.showerror(title="Error", message="用户或密码错误！")
            else:
                # 登录成功
                page.destroy() #通用的窗口小部件方法
                root.geometry('360x580') #窗口尺寸
                mainPage.mainpage(root, userid) #进入mainPage

    #各种控件的定义声明，登陆界面
    #输入密码需隐藏
    p1 = Frame(page, width=216, height=40, bg=c[0])
    p2 = Frame(page, width=216, height=30, bg=c[0])
    p3 = Frame(page, width=216, height=30, bg=c[0])
    p4 = Frame(page, width=216, height=34, bg='#87CEEB')

    p1.grid(row=1, column=1, padx=72, pady=20)
    p2.grid(row=2, column=1, pady=15)
    p3.grid(row=3, column=1, pady=15)
    p4.grid(row=4, column=1, pady=15)

    p1.grid_propagate(0)
    p2.grid_propagate(0)
    p3.grid_propagate(0)
    p4.grid_propagate(0)

    Label(p1, bg=c[0], fg='#99CCFF', text='Welcome', font=("等线", 30, 'bold'), anchor='center').grid(padx=40)
    Label(p2, bg=c[0], fg=c[2], text="帐号", font=('等线', 15), anchor='center').grid(row=0, column=0, sticky=NSEW)
    Entry(p2, bd=0,textvariable=uname, width=24,font=('等线', 10)).grid(row=0, column=1, columnspan=2, sticky=NSEW)
    Label(p3, bg=c[0], fg=c[2], text="密码", anchor='center', font=('等线', 15)).grid(row=0, column=0, sticky=NSEW)
    Entry(p3, bd=0,textvariable=pwd, show='*', width=24,font=('等线', 10)).grid(row=0, column=1, columnspan=2, sticky=NSEW)
    Button(p4, bg='#87CEEB', bd=0, fg='white', text="登   录", font=('等线', 15), width=16, command=loginCheck,anchor='center').grid(padx=15)

#用户注册函数
def register(root, page):
    uname = StringVar()
    pwd = StringVar()
    Email = StringVar()
    rpwd = StringVar()
    hostname = socket.gethostname()
    hostip = socket.gethostbyname(hostname)
    def rgCheck():
        name = uname.get() #用户名
        password = pwd.get() #第一次输入密码
        rPassword = rpwd.get() #第二次输入密码
        email = Email.get() #邮箱

        #检测用户输入的用户名、密码、邮箱格式是否正确
        if ((name == '') | (password == '') | (rPassword == '') | (email == '')):  # 注册信息中任意一项为空
            messagebox.showerror(title="Error", message="请完善注册信息！")
        else:
            # 两次输入密码不一致
            if password != rPassword:
                messagebox.showerror(title="Error", message="两次输入密码不一致！")
            # 昵称格式错误
            elif (re.match(r'^[a-z,_][a-zA-Z0-9]*$', name) == None): #正则表达式，表示以小写字母或下划线开头，只接收大小写字母和数字的字符串
                messagebox.showerror(title="Error", message="昵称只允许字母数字下划线，且以字母或下划线开头！")
            #昵称过长
            elif (len(name)>10):
                messagebox.showerror(title="Error", message="昵称长度应小于10！")
            # 邮箱格式错误
            elif (re.match(r'[a-zA-Z0-9_]+\@[a-zA-Z0-9]+\.[com,cn,net]', email) == None):
                messagebox.showerror(title="Error", message="请输入有效的邮箱格式")
            else:
                #所有输入数据格式正确之后，为该用户生成对应的公私钥，并将公钥等信息传送给服务器端
                public_key = str(RSA_key.cert_create(name))
                #public_key = public_key.decode()
                msg = '1' + '|' + name + '###' + hash.hash_test(password) + '###' +hostip + '###' + public_key + '###'+ '6666'
                response = sendmessage.sendMsg(msg)

                # 用户名已经存在
                if response == '3':
                    messagebox.showerror(title="Error", message="用户名已经存在")
                elif response == 'fail':
                    messagebox.showerror(title="Error", message="注册失败!")
                elif response == '2':
                    # 注册成功
                    messagebox.showinfo("Success","注册成功")

                    #进入程序界面
                    page.destroy()
                    root.geometry('360x580')
                    # root.quit()
                    mainPage.mainpage(root, name)

    #注册界面说明
    p1 = Frame(page, width=216, height=35, bg=c[0])
    p2 = Frame(page, width=216, height=20, bg=c[0])
    p3 = Frame(page, width=216, height=20, bg=c[0])
    p4 = Frame(page, width=216, height=20, bg=c[0])
    p5 = Frame(page, width=216, height=20, bg=c[0])
    p6 = Frame(page, width=216, height=30, bg='#87CEEB')
    p1.grid(row=1, column=1, padx=72, pady=10, columnspan=2)
    p2.grid(row=2, column=1, pady=6, ipady=3)
    p3.grid(row=3, column=1, pady=6, ipady=3)
    p5.grid(row=5, column=1, pady=6, ipady=3)
    p6.grid(row=6, column=1, pady=6, ipady=3)
    p4.grid(row=4, column=0, pady=6, ipady=3, padx=72, columnspan=2)
    p1.grid_propagate(0)
    p2.grid_propagate(0)
    p3.grid_propagate(0)
    p4.grid_propagate(0)
    p5.grid_propagate(0)
    p6.grid_propagate(0)
    Label(p1, bg=c[0], fg='#99CCFF', text='Register', font=("等线", 24, 'bold'), anchor='center').grid(padx=40)
    Label(p2, bg=c[0], fg=c[2], text="昵称", font=('等线', 12), anchor='center').grid(row=0, column=0, sticky=NSEW)
    Entry(p2, textvariable=uname, width=25).grid(row=0, column=1, columnspan=2, sticky=NSEW)
    Label(p3, bg=c[0], fg=c[2], text="密码", font=('等线', 12), anchor='center').grid(row=0, column=0, sticky=NSEW)
    Entry(p3, textvariable=pwd, show='*', width=25).grid(row=0, column=1, columnspan=2, sticky=NSEW)
    Label(p4, bg=c[0], fg=c[2], text="确认密码", font=('等线', 12), anchor='center').grid(row=0, column=0, sticky=NSEW)
    Entry(p4, textvariable=rpwd, width=24, show='*').grid(row=0, column=1, columnspan=2, sticky=NSEW)
    Label(p5, bg=c[0], fg=c[2], text="邮箱", font=('等线', 12), anchor='center').grid(row=0, column=0, sticky=NSEW)
    Entry(p5, textvariable=Email, width=25).grid(row=0, column=1, columnspan=2, sticky=NSEW)
    Button(p6, bd=0, bg='#87CEEB', fg='white', text="注   册", font=('等线', 15), width=20, command=rgCheck,anchor='center').grid()


def enterSystem(root):  #整个系统的入口
    loginF = Frame(root, bg=c[0])
    registF = Frame(root, bg=c[0])

    # 默认显示登录页面
    loginF.grid()
    login(root, loginF)

    def logView():
        loginF.grid()
        registF.grid_forget()
        login(root, loginF)

    def registView():
        loginF.grid_forget()
        registF.grid()
        register(root, registF)

    menubar = Menu(root)
    menubar.add_command(label='登录', command=logView)
    menubar.add_command(label='注册', command=registView)
    root['menu'] = menubar
    #root.mainloop()


if __name__ == "__main__": #获取到函数的名称

    root = Tk()
    root.geometry("360x260")
    root.title("安全即时通信系统")
    enterSystem(root)
    root.mainloop()
    #root.quit()
    print('quit')