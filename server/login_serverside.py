import pymysql

# -*- coding:utf-8 -*-



# 用户登录服务器端函数
def login(msg,ip):  # msg的格式为：“user_name/password”

    msg = msg.split('/')

    dbhost = 'localhost'
    dbuser = 'root'
    dbpass = '111111'
    dbname = 'user'

    # 打开数据库连接
    db = pymysql.connect(host=dbhost, user=dbuser, password=dbpass, database=dbname)
    # 新建一个游标对象
    cursor = db.cursor()

    try:
        # 检验用户名是否存在
        sql = "SELECT * FROM first where user_name = '%s' and password = '%s'"%(msg[0],msg[1])  # SQL查询
        cursor.execute(sql)  # 执行sql语句
        data = cursor.fetchone()  # 返回结果
        db.commit()  # 提交

        if data:
            try:
                # 将用户的在线状态更新为在线，即将state更新为1
                sql = "update first set state = 1 where user_name = '%s'"%msg[0]
                cursor.execute(sql)
                db.commit()
                # 将用户的ip地址更新为用户此次登录使用的ip地址
                sql = "update first set ip_address = '%s' where user_name = '%s'"%(ip,msg[0])
                cursor.execute(sql)
                db.commit()
            except:
                db.rollback()

            db.close()
            return '5'
        else:
            db.close()
            return '6'
    except:
        db.rollback()

