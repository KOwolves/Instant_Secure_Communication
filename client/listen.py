from threading import Thread
import socket
import datetime

#持续监听消息
def conlisten(itsID):
    hostname=socket.gethostname() #返回程序正在运行的计算机的名字。系统调用gethostbyname()可以使用这个名字来决定你的机器的IP地址
    hostip=socket.gethostbyname(hostname)

    self = socket.socket(socket.AF_INET,socket.SOCK_STREAM) #定义socket类型，网络通信
    self.bind(('hostip',6666)) #监听端口
    self.listen(10)

    recvData()
    tr = Thread(target=recvData)
    tr.start()
    tr.join()

udpSocket = None
def recvData(itsID):
    while True:
        recvInfo = udpSocket.recvfrom(1024)
        sTime = datetime.datetime.strftime(time1,'%Y-%m-%d %H:%M:%S')
        itsInfo = ' ' + itsID + ':  ' + sTime + '\n '
        txtMsgList.insert(END, itsInfo, 'recvColor')
        txtMsgList.insert(END, strMsg + '\n', 'msgF')

def sendData():
    while True:
        sendInfo = input("<<")
        udpSocket.sendto(sendInfo.encode("gb2312"),(destIp,destPort))


def main():
    conlisten()

if __name__ == "__main__":
    main()