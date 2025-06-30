import pymysql
import json
import time

# -*- coding:utf-8 -*-



def request_friend_list(msg,status):  # msg的格式为：“user_name”，status是保存用户上一次链接到服务器时间的字典

    dbhost = 'localhost'
    dbuser = 'root'
    dbpass = '111111'
    dbname = 'user'

    # 打开数据库连接
    db = pymysql.connect(host=dbhost, user=dbuser, password=dbpass, database=dbname)

    # 新建一个游标对象
    cursor = db.cursor()

    # 利用sql语句查询user_name的好友列表，并将返回的好友列表保存在data中
    sql = "select f0,f1,f2,f3,f4,f5,f6,f7,f8,f9 from first where user_name = '%s'" % msg
    fNum = 0
    try:
        #print('one')
        cursor.execute(sql)
        #print('two')
        db.commit()
        #print('three')
        #data = cursor.fetchall()
        data = cursor.fetchone() #返回单个的元组，也就是一条记录(row)，如果没有结果 则返回 None
        #print('four')
        data = list(data)  # 将data转为列表格式
        #fNum = 0
        for num in range(0,10):
            if data[num] is not None:
                fNum = fNum + 1
    except:
         print('qwert')
         db.rollback()

    # 如果fNum为零，即用户好友列表为空，则返回“no friend"
    if fNum == 0:
        db.close()
        return 'no friend'

    else:
        fNames = []
        for i in range(0,10):
            if data[i] is not None:
                fNames.append(data[i])  # 将用户的好友列表中的好友用户名保存在fNames中

        all_friends = []
        for name in fNames:
            try:
                # 返回用户名为name的用户的user_name,ip_address,port,state,certification这些信息并且保存在data中
                sql = "select user_name,ip_address,port,state,certification from first where user_name = '%s'"%name
                cursor.execute(sql)
                #data = cursor.fetchall()
                data = cursor.fetchone()
                data = list(data)
                data[2] = str(data[2])
                ip = data[1]
                # 如果在字典中没有这个用户，说明此用户在服务器启动之后没有对服务器进行链接，将其在线状态改为不在线
                if name not in status.keys():
                    data[3] = 0
                    sql = "update first set state = 0 and ip_address='offline' where user_name = '%s'" % name
                    try:
                        cursor.execute(sql)
                        db.commit()
                    except:
                        db.rollback()
                else:  # 如果用户上一次链接服务器的时间在三秒之前，将其状态改为不在线
                    if time.time() - status[name] > 3:
                        data[3] = 0
                        sql = "update first set state = 0 and ip_address='offline' where user_name = '%s'" % name
                        try:
                            cursor.execute(sql)
                            db.commit()
                        except:
                            db.rollback()

                    else:  # 除了以上两种情况，认为用户在线
                        data[3] = 1
                        sql = "update first set state = 1 and ip_address='%s' where user_name = '%s'" % (ip,name)
                        try:
                            cursor.execute(sql)
                            db.commit()
                        except:
                            db.rollback()

                all_friends.append(data)
            except:
                db.rollback()

        all_friends = json.dumps(all_friends)
        cursor.close()
        db.close()

        return all_friends

