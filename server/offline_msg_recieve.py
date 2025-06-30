import pymysql

# -*- coding:utf-8 -*-



# 服务器端接收离线消息函数
def c_to_s_offline_msg(msg,conn):  # msg的格式为：“sender_id/rcver_id”

    msg = msg.split('/')
    sender_id = msg[0]
    rcver_id = msg[1]
    data = conn.recv(1024).decode()

    dbhost = 'localhost'
    dbuser = 'root'
    dbpass = '111111'
    dbname = 'user'

    # 打开数据库连接
    db = pymysql.connect(host=dbhost, user=dbuser, password=dbpass, database=dbname)
    cursor = db.cursor()

    # 利用sql语句查询rcver_id的offlineMsg，并将返回结果保存在oldData中
    sql = "select offlineMsg from first where user_name = '%s'" % rcver_id
    try:
        cursor.execute(sql)
        db.commit()
        oldData = cursor.fetchone()  # 新建变量oldData用于保存数据库中offlineMsg列中原有的信息
    except:
        db.rollback()

    newData = oldData[0]  # 由于oldData为元组变量，将oldData元组中的数据提取存储在newData中
    newData = str(newData)

    # 如果原有的offlineMsg为空，则直接将newData改为data；如果不为空，则将data添加到newData后面
    if newData == "None":
        newData = data
    else:
        newData = newData + data

    # 利用sql语句将rcver_id的offlineMsg更新为newData+'\n'，如果更新成功则返回16
    sql = "update first set offlineMsg = '%s' where user_name = '%s'" %((newData + '\n'), rcver_id)
    try:
        cursor.execute(sql)
        db.commit()
        db.close()
        return "16"
    except:
        db.rollback()
