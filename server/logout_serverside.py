import pymysql

# -*- coding:utf-8 -*-


# 服务器端退出登录函数
def logout(msg):

    dbhost = 'localhost'
    dbuser = 'root'
    dbpass = '111111'
    dbname = 'user'

    # 打开数据库连接
    db = pymysql.connect(host=dbhost,user=dbuser,password=dbpass,database=dbname)
    # 新建一个游标对象
    cursor = db.cursor()


    try:
        # 利用sql语句将数据库中提交下线申请的用户的在线状态改为离线，即将state改为0
        sql = "update first set state = 0 where user_name = '%s'" % msg
        cursor.execute(sql)
        db.commit()
        # 利用sql语句将数据库中提交下线申请的用户的ip地址更新为“offline”
        sql = "update first set ip_address = 'offline' where user_name = '%s'" % msg
        cursor.execute(sql)  # 执行sql语句
        db.commit()  # 提交
        db.close()
    except:
        db.rollback()

