import socket
import main_interface
#import hash

#c/s连接的桥梁
#发送消息
def sendMsg(msg):
	#hashv = hash.hash_test(msg)
	#msg = msg + '*/' + hashv

	client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	client.connect(('10.21.170.91', 55555))  # 连接服务器

	client.send(msg.encode())   #发送数据,利用套接字传输的内容都以byte形式传输

	data = client.recv(1024).decode()    #接受数据

	client.close()	#关闭socket连接
	#data='5'
	return data