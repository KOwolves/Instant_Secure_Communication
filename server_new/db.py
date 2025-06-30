"""
完成各类数据库操作
"""
import pyodbc
from config import db_info
import logging
from utils import hash_password

SQL_CONNECTION_STRING = ("DRIVER={ODBC Driver 17 for SQL Server};"
                         f"SERVER=localhost;DATABASE={db_info['database']};"
                         f"UID={db_info['user']};"
                         f"PWD={db_info['password']};")

# 获取logger实例，名称通常与模块名一致
logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        self.conn_str = SQL_CONNECTION_STRING
        logger.info("DatabaseManager: 正在初始化并尝试连接到数据库。")
        self.create_tables()
        logger.info("DatabaseManager: 数据库管理器初始化完成。")

    def _get_connection(self):
        """获取一个新的数据库连接。"""
        try:
            conn = pyodbc.connect(self.conn_str, autocommit=True)
            logger.debug("DatabaseManager: 成功获取数据库连接。")
            return conn
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            logger.error(f"DatabaseManager: 数据库连接失败! SQLSTATE: {sqlstate} - {ex}", exc_info=True)
            raise

    def create_tables(self):
        """如果不存在，则创建数据库表。"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            logger.info("DatabaseManager: 检查并创建 'Users' 表...")
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Users' and xtype='U')
                CREATE TABLE Users (
                    UserID INT IDENTITY(1,1) PRIMARY KEY,
                    Username NVARCHAR(50) NOT NULL UNIQUE,
                    Password NVARCHAR(64) NOT NULL,
                    PublicKey NVARCHAR(MAX) NOT NULL,
                    RegistrationDate DATETIME DEFAULT GETDATE()
                );
            """)

            logger.info("DatabaseManager: 检查并创建 'Friendships' 表...")
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Friendships' and xtype='U')
                CREATE TABLE Friendships (
                    UserID INT NOT NULL,
                    FriendID INT NOT NULL,
                    PRIMARY KEY (UserID, FriendID),                             -- 设置 (UserID, FriendID) 为复合主键
                    FOREIGN KEY (UserID) REFERENCES Users(UserID),
                    FOREIGN KEY (FriendID) REFERENCES Users(UserID),
                    CONSTRAINT CK_FriendshipOrder CHECK (UserID < FriendID),     -- 强制规范顺序 (较小的ID在前)
                    CONSTRAINT CK_NotSelfFriend CHECK (UserID <> FriendID)       -- 防止自己添加自己
                );
            """)

            logger.info("DatabaseManager: 检查并创建 'OnlineStatus' 表...")
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='OnlineStatus' and xtype='U')
                CREATE TABLE OnlineStatus (
                    UserID INT PRIMARY KEY,
                    IPAddress VARCHAR(45) NOT NULL,
                    P2PPort INT NOT NULL,
                    LastActive DATETIME DEFAULT GETDATE(),
                    FOREIGN KEY (UserID) REFERENCES Users(UserID)
                );
            """)

            # 显式提交确保表创建
            conn.commit()
            logger.info("DatabaseManager: 数据库表检查/创建完成。")
        except pyodbc.Error as ex:
            logger.error(f"DatabaseManager: 创建数据库表时出错: {ex}", exc_info=True)
        finally:
            if conn:
                conn.close()
                logger.debug("DatabaseManager: 已关闭创建表时的数据库连接。")

    def register_user(self, username, password, public_key):
        """注册一个新用户并将其信息存储到数据库。"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            password_hash = hash_password(password)

            sql = "INSERT INTO Users (Username, Password, PublicKey) VALUES (?, ?, ?)"
            logger.debug(f"DatabaseManager: 执行SQL注册用户: {sql} with username={username}")
            cursor.execute(sql, username, password_hash, public_key)
            logger.info(f"DatabaseManager: 用户 '{username}' 注册成功。")
            return True
        except pyodbc.IntegrityError as ex:
            # Username UNIQUE constraint violation (SQLSTATE for integrity constraint violation)
            if '23000' in str(ex) or '2627' in str(ex):  # 2627是SQL Server唯一约束错误码
                logger.warning(f"DatabaseManager: 注册失败: 用户名 '{username}' 已存在。")
                return False
            logger.error(f"DatabaseManager: 注册用户 '{username}' 时发生完整性错误: {ex}", exc_info=True)
            return False
        except pyodbc.Error as ex:
            logger.error(f"DatabaseManager: 注册用户 '{username}' 时出错: {ex}", exc_info=True)
            return False
        finally:
            if conn:
                conn.close()
                logger.debug("DatabaseManager: 已关闭注册用户时的数据库连接。")

    def authenticate_user(self, username, password):
        """验证用户凭据，如果成功则返回 UserID 和 PublicKey。"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            password_hash = hash_password(password)

            sql = "SELECT UserID, PublicKey FROM Users WHERE Username = ? AND Password = ?"
            logger.debug(f"DatabaseManager: 执行SQL认证用户: {sql} with username={username}")
            cursor.execute(sql, username, password_hash)
            row = cursor.fetchone()
            if row:
                logger.info(f"DatabaseManager: 用户 '{username}' 认证成功。")
                return row.UserID, row.PublicKey
            logger.warning(f"DatabaseManager: 用户 '{username}' 认证失败 (用户名或密码无效)。")
            return None, None
        except pyodbc.Error as ex:
            logger.error(f"DatabaseManager: 认证用户 '{username}' 时出错: {ex}", exc_info=True)
            return None, None
        finally:
            if conn:
                conn.close()
                logger.debug("DatabaseManager: 已关闭认证用户时的数据库连接。")

    def get_user_id(self, username):
        """根据用户名获取用户ID。"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            sql = "SELECT UserID FROM Users WHERE Username = ?"
            logger.debug(f"DatabaseManager: 执行SQL获取用户ID: {sql} with username={username}")
            cursor.execute(sql, username)
            row = cursor.fetchone()
            if row:
                logger.debug(f"DatabaseManager: 找到用户ID {row.UserID} 为用户名 '{username}'。")
                return row.UserID
            logger.warning(f"DatabaseManager: 未找到用户名 '{username}' 对应的用户ID。")
            return None
        except pyodbc.Error as ex:
            logger.error(f"DatabaseManager: 获取用户ID '{username}' 时出错: {ex}", exc_info=True)
            return None
        finally:
            if conn:
                conn.close()
                logger.debug("DatabaseManager: 已关闭获取用户ID时的数据库连接。")

    def get_username_by_id(self, user_id):
        """根据用户ID获取用户名。"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            sql = "SELECT Username FROM Users WHERE UserID = ?"
            logger.debug(f"DatabaseManager: 执行SQL获取用户名: {sql} with user_id={user_id}")
            cursor.execute(sql, user_id)
            row = cursor.fetchone()
            if row:
                logger.debug(f"DatabaseManager: 找到用户名 '{row.Username}' 为用户ID {user_id}。")
                return row.Username
            logger.warning(f"DatabaseManager: 未找到用户ID {user_id} 对应的用户名。")
            return None
        except pyodbc.Error as ex:
            logger.error(f"DatabaseManager: 根据ID获取用户名 {user_id} 时出错: {ex}", exc_info=True)
            return None
        finally:
            if conn:
                conn.close()
                logger.debug("DatabaseManager: 已关闭根据ID获取用户名时的数据库连接。")

    def get_public_key(self, username):
        """根据用户名获取用户的公钥。"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            sql = "SELECT PublicKey FROM Users WHERE Username = ?"
            logger.debug(f"DatabaseManager: 执行SQL获取公钥: {sql} with username={username}")
            cursor.execute(sql, username)
            row = cursor.fetchone()
            if row:
                logger.debug(f"DatabaseManager: 成功获取用户 '{username}' 的公钥。")
                return row.PublicKey
            logger.warning(f"DatabaseManager: 未找到用户 '{username}' 的公钥。")
            return None
        except pyodbc.Error as ex:
            logger.error(f"DatabaseManager: 获取公钥 '{username}' 时出错: {ex}", exc_info=True)
            return None
        finally:
            if conn:
                conn.close()
                logger.debug("DatabaseManager: 已关闭获取公钥时的数据库连接。")

    def add_friendship(self, uid1, uid2):
        """在两个用户之间建立好友关系。"""
        if uid1 == uid2:
            logger.warning(f"DatabaseManager: 尝试添加自己为好友 (UserID: {uid1})，操作被拒绝。")
            return False  # 不能添加自己为好友
        elif uid1 > uid2:
            user_id = uid2
            friend_id = uid1
        else:
            user_id = uid1
            friend_id = uid2

        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 检查是否已存在此好友关系
            sql_check = "SELECT 1 FROM Friendships WHERE UserID = ? AND FriendID = ?"
            logger.debug(f"DatabaseManager: 检查好友关系: {sql_check} with UserID={user_id}, FriendID={friend_id}")
            cursor.execute(sql_check, user_id, friend_id)
            if cursor.fetchone():
                logger.info(f"DatabaseManager: 用户 {user_id} 和 {friend_id} 已经是好友。")
                return False  # 已经是好友

            sql_insert = "INSERT INTO Friendships (UserID, FriendID) VALUES (?, ?)"
            logger.debug(f"DatabaseManager: 执行SQL添加好友: {sql_insert} with UserID={user_id}, FriendID={friend_id}")
            cursor.execute(sql_insert, user_id, friend_id)
            logger.info(f"DatabaseManager: 用户 {user_id} 添加好友 {friend_id} 成功。")
            return True
        except pyodbc.Error as ex:
            logger.error(f"DatabaseManager: 添加好友关系 UserID={user_id}, FriendID={friend_id} 时出错: {ex}",
                         exc_info=True)
            return False
        finally:
            if conn:
                conn.close()
                logger.debug("DatabaseManager: 已关闭添加好友时的数据库连接。")

    def remove_friendship(self, uid1, uid2):
        """删除好友关系。"""
        if uid1 == uid2:
            logger.warning(f"DatabaseManager: 操作被拒绝。")
            return False
        elif uid1 > uid2:
            user_id = uid2
            friend_id = uid1
        else:
            user_id = uid1
            friend_id = uid2

        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            sql = "DELETE FROM Friendships WHERE UserID = ? AND FriendID = ?"
            logger.debug(f"DatabaseManager: 执行SQL删除好友: {sql} with UserID={user_id}, FriendID={friend_id}")
            cursor.execute(sql, user_id, friend_id)
            if cursor.rowcount > 0:
                logger.info(f"DatabaseManager: 用户 {user_id} 成功移除好友 {friend_id}。")
                return True
            else:
                logger.warning(f"DatabaseManager: 尝试移除好友失败: 用户 {user_id} 和 {friend_id} 可能不是好友。")
                return False
        except pyodbc.Error as ex:
            logger.error(f"DatabaseManager: 删除好友关系 UserID={user_id}, FriendID={friend_id} 时出错: {ex}",
                         exc_info=True)
            return False
        finally:
            if conn:
                conn.close()
                logger.debug("DatabaseManager: 已关闭删除好友时的数据库连接。")

    def set_online_status(self, user_id, ip_address, p2p_port):
        """设置或更新用户的在线状态。"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            sql = """
                MERGE OnlineStatus AS target
                USING (VALUES (?, ?, ?)) AS source (UserID, IPAddress, P2PPort)
                ON (target.UserID = source.UserID)
                WHEN MATCHED THEN
                    UPDATE SET target.IPAddress = source.IPAddress,
                               target.P2PPort = source.P2PPort,
                               target.LastActive = GETDATE()
                WHEN NOT MATCHED THEN
                    INSERT (UserID, IPAddress, P2PPort)
                    VALUES (source.UserID, source.IPAddress, source.P2PPort);
            """
            logger.debug(
                f"DatabaseManager: 执行SQL设置在线状态: {sql.strip()} with UserID={user_id}, IP={ip_address}, Port={p2p_port}")
            cursor.execute(sql, user_id, ip_address, p2p_port)
            logger.info(f"DatabaseManager: 用户 {user_id} 在线状态更新成功: {ip_address}:{p2p_port}。")
            return True
        except pyodbc.Error as ex:
            logger.error(f"DatabaseManager: 设置在线状态 UserID={user_id} 时出错: {ex}", exc_info=True)
            return False
        finally:
            if conn:
                conn.close()
                logger.debug("DatabaseManager: 已关闭设置在线状态时的数据库连接。")

    def clear_online_status(self, user_id):
        """清除用户的在线状态（用户登出）。"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            sql = "DELETE FROM OnlineStatus WHERE UserID = ?"
            logger.debug(f"DatabaseManager: 执行SQL清除在线状态: {sql} with UserID={user_id}")
            cursor.execute(sql, user_id)
            if cursor.rowcount > 0:
                logger.info(f"DatabaseManager: 用户 {user_id} 在线状态已清除。")
                return True
            else:
                logger.warning(f"DatabaseManager: 尝试清除用户 {user_id} 在线状态，但记录不存在。")
                return False
        except pyodbc.Error as ex:
            logger.error(f"DatabaseManager: 清除在线状态 UserID={user_id} 时出错: {ex}", exc_info=True)
            return False
        finally:
            if conn:
                conn.close()
                logger.debug("DatabaseManager: 已关闭清除在线状态时的数据库连接。")

    def get_online_friends_info(self, user_id):
        """获取指定用户所有在线好友的信息（用户名、IP、端口、公钥）。"""
        conn = None
        online_friends = []
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            sql = """
                SELECT
                    u.Username
                FROM Friendships fs
                JOIN Users u ON fs.FriendID = u.UserID
                JOIN OnlineStatus os ON u.UserID = os.UserID
                WHERE fs.UserID = ?
            """
            logger.debug(f"DatabaseManager: 执行SQL获取在线好友信息: {sql.strip()} for UserID={user_id}")
            cursor.execute(sql, user_id)

            for row in cursor.fetchall():
                online_friends.append(row.Username)
            logger.info(f"DatabaseManager: 已为用户 {user_id} 检索到 {len(online_friends)} 个在线好友信息。")
            return online_friends
        except pyodbc.Error as ex:
            logger.error(f"DatabaseManager: 获取在线好友信息 UserID={user_id} 时出错: {ex}", exc_info=True)
            return []
        finally:
            if conn:
                conn.close()
                logger.debug("DatabaseManager: 已关闭获取在线好友信息时的数据库连接。")

    def get_all_friends_info(self, user_id):
        """获取指定用户的所有好友信息（在线或离线）。"""
        conn = None
        all_friends = []
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            # 查询作为 UserID 或 FriendID 的好友
            sql = """
                SELECT
                    u.UserID,
                FROM Friendships fs
                JOIN Users u ON (
                    (fs.UserID = ? AND u.UserID = fs.FriendID) OR   -- 当前用户是 UserID，查找 FriendID
                    (fs.FriendID = ? AND u.UserID = fs.UserID)      -- 当前用户是 FriendID，查找 UserID
                )
                WHERE (fs.UserID = ? OR fs.FriendID = ?)
            """
            logger.debug(f"DatabaseManager: 执行SQL获取所有好友信息: {sql.strip()} for UserID={user_id}")
            cursor.execute(sql, user_id, user_id, user_id, user_id)

            for row in cursor.fetchall():
                all_friends.append(row.UserID)
            logger.info(f"DatabaseManager: 已为用户 {user_id} 检索到 {len(all_friends)} 个所有好友信息。")
            return all_friends
        except pyodbc.Error as ex:
            logger.error(f"DatabaseManager: 获取所有好友信息 UserID={user_id} 时出错: {ex}", exc_info=True)
            return []
        finally:
            if conn:
                conn.close()
                logger.debug("DatabaseManager: 已关闭获取所有好友信息时的数据库连接。")

    def get_all_users_info(self):
        """获取所有注册用户的信息（用于查找好友等）。"""
        conn = None
        users_info = []
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            sql = "SELECT UserID, Username FROM Users"
            logger.debug(f"DatabaseManager: 执行SQL获取所有用户信息: {sql}")
            cursor.execute(sql)
            for row in cursor.fetchall():
                users_info.append({"user_id": row.UserID, "username": row.Username})
            logger.info(f"DatabaseManager: 已检索到所有 {len(users_info)} 个注册用户信息。")
            return users_info
        except pyodbc.Error as ex:
            logger.error(f"DatabaseManager: 获取所有用户信息时出错: {ex}", exc_info=True)
            return []
        finally:
            if conn:
                conn.close()
                logger.debug("DatabaseManager: 已关闭获取所有用户信息时的数据库连接。")