import pymysql

# -*- coding:utf-8 -*-


# 服务器端删除好友函数
def delete_friend(msg):  # msg的格式为：“user_name/friend_name”

    msg = msg.split('/')
    user_name = msg[0]
    friend_name = msg[1]
    deleteFlag1 = 11
    deleteFlag2 = 11

    dbhost = 'localhost'
    dbuser = 'root'
    dbpass = '111111'
    dbname = 'user'

    # 打开数据库连接
    db = pymysql.connect(host=dbhost, user=dbuser, password=dbpass, database=dbname)
    # 新建一个游标对象
    cursor = db.cursor()

    # 判定用户想要删除的好友是否存在，如果不存在则返回“15”，即删除失败
    sql = "select user_name from first where user_name = '%s'" %friend_name
    try:
        cursor.execute(sql)
        db.commit()
        data = cursor.fetchone()
        if data:
            pass
        else:
            return '15'
    except:
        db.rollback()

    # 利用sql语句查询a的好友列表，并将返回的好友列表保存在data中
    sql = "select f0,f1,f2,f3,f4,f5,f6,f7,f8,f9 from first where user_name = '%s'" %user_name
    try:
        cursor.execute(sql)
        db.commit()
        data = cursor.fetchone()

        # 在a的好友列表中寻找b，如果b存在，则将deleteFlag1设为b所在的好友位编号；如果b不存在则deleteFlag1不变
        for num in range(0,10):
            if data[num] == friend_name:
                deleteFlag1 = num
    except:
        db.rollback()
    # 如果a的好友列表中没有b，即deleteFlag1==11，则返回“15”，即删除好友失败
    if deleteFlag1 == 11:
        return '15'
    else:
        pass

    # 利用sql语句查询b的好友列表，并将返回的好友列表保存在data中
    sql = "select f0,f1,f2,f3,f4,f5,f6,f7,f8,f9 from first where user_name = '%s'" % friend_name
    try:
        cursor.execute(sql)
        db.commit()
        data = cursor.fetchone()

        # 在b的好友列表中寻找a，如果a存在，则将deleteFlag2设为a所在的好友位编号；如果a不存在则deleteFlag2不变
        for num in range(0, 10):
            if data[num] == user_name:
                deleteFlag2 = num
    except:
        db.rollback()
    # 如果b的好友列表中没有a，即deleteFlag2==11，则返回“15”，即删除好友失败
    if deleteFlag2 == 11:
        return '15'
    else:
        pass

    # 利用sql语句在a的好友列表中删除b
    sql = "update first\
          set f%d=null\
          where user_name='%s'" %(deleteFlag1, user_name)
    try:
        cursor.execute(sql)
        db.commit()
    except:
        db.rollback()

    # 利用sql语句在b的好友列表中删除a
    sql = "update first \
          set f%d=null\
          where user_name='%s'" % (deleteFlag2, friend_name)
    try:
        cursor.execute(sql)
        db.commit()
        return '13'
    except:
        db.rollback()

    db.close()
