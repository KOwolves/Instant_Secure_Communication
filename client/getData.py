import pymysql
import json
import sendmessage

#从数据库读取好友信息
def getFrdInfo(myID):
    msg='7' + '|' + myID
    #print(msg)
    result=sendmessage.sendMsg(msg)  #好友信息请求格式
    #print(msg)
    if result == "no friend":
        return -1
    result = json.loads(result)
    return result