import socket

def receive():
    hostip=socket.gethostbyname(socket.gethostname())
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    hostip = socket.getaddrinfo(socket.gethostname(), None)[7][4][0]  #获得本机的IP
    sock.bind((hostip, 8888))       #绑定端口

    sock.listen(3)                    #监听端口
    sc,sc_name = sock.accept()    #当有请求到指定端口是 accpte()会返回一个新的socket和对方主机的（ip,port）
    #print('收到{}请求'.format(sc_name))
    info = sc.recv(1024)       #首先接收一段数据，这段数据包含文件的长度和文件的名字，使用|分隔
    length,file_name = info.decode().split('|')
    if length and file_name:
        newfile = open(file_name ,'wb')  #这里可以使用从客户端解析出来的文件名，以二进制写方式打开，只能写文件， 如果文件不存在，创建该文件；如果文件已存在，则覆盖写
        #print('length {},filename {}'.format(length,file_name))
        sc.send(b'ok')   #表示收到文件长度和文件名
        file = b''
        total = int(length)
        get = 0
        while get < total:         #接收文件
            data = sc.recv(1024)
            file += data
            get = get + len(data)
        print('应该接收{},实际接收{}'.format(length,len(file)))
        if file:
            print('acturally length:{}'.format(len(file)))
            newfile.write(file[:])
            newfile.close()
            sc.send(b'copy')    #完整的收到文件了
    sock.close()
    sc.close()

#if  __name__ == '__main__':
    #server()