import pymysql

# -*- coding:utf-8 -*-

# 服务器端添加好友函数
def add_friend(msg):  # msg的格式为：“user_name/friend_name”

    msg = msg.split('/')
    user_name = msg[0]  # 用户名 记为a
    friend_name = msg[1]  # 好友用户名 记为b
    remainNum1 = 0  # a好友列表空余位置
    remainNum2 = 0  # b好友列表剩余位置
    judgeFlag = 0  # 用于判定a是否已经添加过b，如果已经添加过，则将judgeFlag设为1
    judgeArray = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # 用于存储a好友列表中未添加好友的好友位的编号
    arrayFlag = 0  # 在循环中用于标记位
    dataArray = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # 用于存储b好友列表中未添加好友的好友位的编号

    dbhost = 'localhost'
    dbuser = 'root'
    dbpass = '111111'
    dbname = 'user'

    # 打开数据库连接
    db = pymysql.connect(host=dbhost, user=dbuser, password=dbpass, database=dbname)
    # 新建一个游标对象
    cursor = db.cursor()

    # 利用sql语句查询b是否存在，若b不存在则返回“11”，即添加好友失败
    sql = "select user_name from first where user_name = '%s'" %friend_name
    try:
        cursor.execute(sql)
        db.commit()
        data = cursor.fetchone()
        if data:
            pass
        else:
            db.close()
            return '11'
    except:
        db.rollback()

    #返回a的好友列表
    sql = "select f0,f1,f2,f3,f4,f5,f6,f7,f8,f9 from first where user_name = '%s'" % user_name
    try:
        cursor.execute(sql)
        db.commit()
        judge = cursor.fetchone()  # judge为a的好友列表

        # 判断在judge中是否已经有b，如果已经存在则将judgeFlag置为1
        for judgeNum in range(0,10):
            if judge[judgeNum] == friend_name:
                judgeFlag = 1

        # 如果是，则返回“11”，即添加好友失败；如果不是则进行添加好友操作
        if judgeFlag == 1:
            return '11'
        else:
            for num in range(0,10):
                if judge[num] is None:
                    remainNum1 += 1
                    judgeArray[arrayFlag] = num  # 将a的空余好友位的编号保存在judgeArray中
                    arrayFlag += 1

            # 如果空余好友位个数为零则返回11，即添加好友失败
            if remainNum1 == 0:
                db.close()
                return '11'

            # 如果空余好友位不为零则开始进行添加好友操作
            else:
                # 利用sql语句返回数据库中b的好友列表，并将返回的好友列表保存在data中
                sql = "select f0,f1,f2,f3,f4,f5,f6,f7,f8,f9 from first where user_name = '%s'" % friend_name
                try:
                    cursor.execute(sql)
                    db.commit()
                    data = cursor.fetchone()
                    # 将arrayFlag重置为零
                    arrayFlag = 0
                    for num in range(0, 10):
                        if data[num] == None:
                            remainNum2 += 1
                            dataArray[arrayFlag] = num  # 将b的空余好友位编号保存在dataArray中
                            arrayFlag += 1
                except:
                    db.rollback()

                # 如果b的好友列表中空余好友位个数为零，则返回“11”，即添加好友失败
                if remainNum2 == 0:
                    db.close()
                    return '11'
                else:
                    # 利用sql语句将a添加在b的好友列表中的第一个空余位
                    sql = "update first\
                          set f%d='%s'\
                          where user_name='%s'" % (dataArray[0], user_name, friend_name)
                    try:
                        cursor.execute(sql)
                        db.commit()
                    except:
                        db.rollback()

                    # 利用sql语句将b添加在a的好友列表中的第一个空余位
                    sql = "update first\
                          set f%d='%s'\
                          where user_name='%s'" % (judgeArray[0], friend_name, user_name)
                    try:
                        cursor.execute(sql)
                        db.commit()
                        db.close()
                        return '10'
                    except:
                        db.rollback()
    except:
        db.rollback()

    db.close()
