import pymysql

# -*- coding:utf-8 -*-


# 注册账户服务器端函数
def regist(msg,ip):  # msg的信息格式为：“user_name###password###ip_address###state###port”

    offline = 0  # 标记用户离线
    online = 1  # 标记用户在线
    # 打开数据库连接
    msg = msg.split('###')

    dbhost = 'localhost'
    dbuser = 'root'
    dbpass = '111111'
    dbname = 'user'

    # 打开数据库连接
    db = pymysql.connect(host=dbhost, user=dbuser, password=dbpass, database=dbname,charset='utf8')

    # 新建游标对象
    cursor = db.cursor()

    try:
        # 检验用户名是否存在
        sql = "SELECT * FROM first where user_name = '%s'"%msg[0]  # SQL查询
        cursor.execute(sql)  # 执行sql语句
        data = cursor.fetchone()  # 返回结果
        db.commit()  # 提交
        if data:
            db.close()
            return '3'

    except:
        db.rollback()

    # 将msg[4]中的数据转为int格式
    msg[4] = int(msg[4])
    # 利用sql语句将新用户的信息插入到数据库中
    sql = "insert into user.first(user_name,password,ip_address,state,certification,port)\
          values('%s', '%s', '%s', '%d', '%s', '%d')" %(msg[0],msg[1], ip, online, msg[0]+'%%%'+ msg[3],msg[4])
    #sql = 'insert into user.first(user_name,password,ip_address,state,certification,port)\
     #   values("%s", "%s", "%s", "%d", "%s", "%d")' % (msg[0], msg[1], ip, online, msg[0] + '%%%' + msg[3], msg[4])
    try:
        cursor.execute(sql)
        db.commit()
        db.close()
        return '2'
    except:
        db.rollback()
        db.close()
        return 'fail'



