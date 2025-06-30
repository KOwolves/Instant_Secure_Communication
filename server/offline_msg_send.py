import pymysql

# -*- coding:utf-8 -*-


# 服务器端发送离线消息函数
def s_to_c_offline_msg(msg):  # msg的格式为：“user_name”

    dbhost = 'localhost'
    dbuser = 'root'
    dbpass = '111111'
    dbname = 'user'

    # 打开数据库连接
    db = pymysql.connect(host=dbhost, user=dbuser, password=dbpass, database=dbname)
    # 新建游标对象
    cursor = db.cursor()

    # 利用sql语句查询user_name的offlineMsg，并将返回的信息保存在data中
    sql = "select offlineMsg from first where user_name = '%s'" % msg
    try:
        cursor.execute(sql)
        db.commit()
        data = cursor.fetchone()
        db.close()
    except:
        db.rollback()

    data = data[0]
    data = str(data)
    return data
