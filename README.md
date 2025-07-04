# 安全即时通讯系统——密语

## 1. 系统概述

该系统是一个安全聊天系统，包含客户端和服务器两个部分：
- 客户端：提供Web界面，支持用户注册、登录、好友管理和安全聊天功能
- 服务器：处理用户认证、好友关系管理、消息转发和密钥分发等功能

## 2. 系统功能

本系统按照“安全、可靠、易用”的设计原则，将核心功能划分为客户端和服务器两大部分，各自承担不同职责，协同实现端到端的安全即时通信。

### 2.1 客户端功能

1. **用户注册与登录**  
   - 用户可通过唯一用户名、密码和邮箱完成注册，客户端对密码进行 SHA-256 哈希后再传输。  
   - 登录时提交用户名和哈希后的密码，服务器验证通过后返回 JWT 或会话标识。
![image text](https://github.com/KOwolves/Instant_Secure_Communication/blob/master/data/%E5%9B%BE%E7%89%871.png)
1. **密钥管理**  
   - 注册时生成 RSA-2048 公私钥对，私钥经用户登录密码派生的 AES 密钥加密后本地存储，公钥上传服务器。  
   - 登录后解密加载私钥到内存；登出或超时后立即清除。

3. **好友管理**  
   - **添加/删除好友**：支持按用户名搜索、扫码或直接输入账号发起好友申请；可在联系人列表右键删除好友，带二次确认并同步清除聊天记录。  
   - **在线状态**：实时显示好友在线／离线状态；心跳机制保证状态同步。

4. **即时通讯**  
   - **端到端加密（E2EE）**：  
     1. 客户端 A 向服务器请求 B 的公钥。  
     2. A 生成一次性 AES-256 会话密钥，用 B 的公钥加密后发送给 B。  
     3. 双方在 P2P 连接上使用 AES-GCM 加密／认证所有消息。  
         ![image text](https://github.com/KOwolves/Instant_Secure_Communication/blob/master/data/565b0690aaa73b4d4e9418f9c22ca6a.png)

5. **多媒体消息**  
   - **图片传输**：支持普通图片和隐写图片发送。  
   - **隐写功能**：在 PNG 文件 LSB 中嵌入秘密文本，发送前对隐写图及隐藏消息再次进行 RSA+AES 加密，接收方点击“锁”形图标可提取并在安全模态框中查看。  
   - **语音聊天**：基于 UDP 的实时语音流采集与加密传输，客户端录制时显示波形。

6. **离线与存储**  
   - **离线消息**：对离线用户的消息在服务器端以密文形式暂存，用户上线后自动补发。  
   - **本地缓存**：使用 IndexedDB 缓存最近 N 条消息，加速历史回溯。

7. **会话管理**  
   - 在消息列表右键可 “隐藏此聊天” 归档会话，或 “删除聊天记录” 完全清空。

8. **人机交互**  
   - 界面采用三栏式布局：导航栏、好友/会话列表、聊天主区；登录/注册界面简洁现代，操作提示清晰。  

### 2.2 服务器功能

1. **用户认证**  
   - 接收注册／登录请求，校验用户名唯一性，存储 Salt+SHA-256 哈希密码。  
   - 登录成功后生成并分发 JWT / 会话令牌。

2. **公钥管理与分发**  
   - 存储用户注册时上传的 RSA 公钥；按需向客户端分发其他用户公钥，支持端到端密钥协商。

3. **在线状态维护**  
   - 维护在线用户表（含 IP、P2P 端口、最后活跃时间）；基于心跳检测自动上下线并广播给其好友。

4. **好友关系管理**  
   - 转发并确认好友申请，将双向好友关系持久化存储；向客户端返回完整的好友列表及状态信息。

5. **消息转发与缓存**  
   - 对在线目标用户：将客户端加密后的消息原封不动推送至目标。  
   - 对离线用户：将密文存入离线消息表，用户上线后按序补发。

6. **密钥分发服务**  
   - 作为 PKI 信任根，仅存储和分发公钥，不保留或解密任何聊天内容。

7. **日志与监控**  
   - 记录注册、登录、好友管理、消息转发、心跳等操作日志；提供健康检查和异常报警接口。
## 3. 环境要求

### 基本环境
- **Python版本**：3.8
- **操作系统**：Windows 10/11
- **数据库**：SQL Server（Microsoft SQL Server）

## 4. 安装依赖

1. 首先，克隆或下载代码到本地

2. 安装Python依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 安装SQL Server相关组件：
   - 安装Microsoft SQL Server（Express版本即可）
   - 安装SQL Server管理工具（SQL Server Management Studio）
   - 确保安装ODBC Driver 17 for SQL Server

## 5. 数据库配置
```sql
1. 创建数据库和用户：
   - 打开SQL Server Management Studio
   - 连接到您的SQL Server实例
   - 执行以下SQL语句：
     ```sql
    -- 创建数据库
   CREATE DATABASE secure_communication;
   GO
   
   -- 使用新创建的数据库
   USE secure_communication;
   GO
   
   -- 创建Users表
   CREATE TABLE Users (
       UserID INT IDENTITY(1,1) PRIMARY KEY,
       Username NVARCHAR(50) NOT NULL UNIQUE,
       Password NVARCHAR(64) NOT NULL,
       PublicKey NVARCHAR(MAX) NOT NULL,
       RegistrationDate DATETIME DEFAULT GETDATE()
   );
   
   -- 创建Friendships表
   CREATE TABLE Friendships (
       UserID INT NOT NULL,
       FriendID INT NOT NULL,
       PRIMARY KEY (UserID, FriendID),
       FOREIGN KEY (UserID) REFERENCES Users(UserID),
       FOREIGN KEY (FriendID) REFERENCES Users(UserID),
       CONSTRAINT CK_FriendshipOrder CHECK (UserID < FriendID),
       CONSTRAINT CK_NotSelfFriend CHECK (UserID <> FriendID)
   );
   
   -- 创建OnlineStatus表
   CREATE TABLE OnlineStatus (
       UserID INT PRIMARY KEY,
       IPAddress VARCHAR(45) NOT NULL,
       P2PPort INT NOT NULL,
       LastActive DATETIME DEFAULT GETDATE(),
       FOREIGN KEY (UserID) REFERENCES Users(UserID)
   );
   
   -- 创建新的数据库登录和用户
   CREATE LOGIN secure_chat_user WITH PASSWORD = 'SecureChat123!';
   GO
   
   -- 将新登录用户与数据库用户关联
   USE secure_communication;
   GO
   CREATE USER secure_chat_user FOR LOGIN secure_chat_user;
   GO
   
   -- 授予数据库访问权限
   EXEC sp_addrolemember 'db_owner', 'secure_chat_user';
   GO
     ```

## 6. 配置服务器

1. 修改服务器配置文件 `./server/config.py`：
   ```python
   # 数据库信息
   db_info = {
       "host": "localhost",  # 或您的SQL Server实例地址
       "port": 1433,         # 默认SQL Server端口
       "user": "secure_chat_user",
       "password": "SecureChat123!",
       "database": "secure_communication",
   }

   # 服务器配置
   SERVER_HOST = "127.0.0.1"  # 保持为本地地址或设置为服务器公网地址
   SERVER_PORT = 50000        # 确保此端口未被占用
   ```

## 7. 配置客户端

1. 修改客户端配置文件 `./client/config.py`：
   ```python
   # 服务器配置
   SERVER_HOST = '127.0.0.1'  # 设置为服务器的IP地址
   SERVER_PORT = 50000        # 与服务器配置一致

   # 客户端P2P监听配置
   P2P_LISTEN_HOST = '0.0.0.0'  # 监听所有可用接口
   P2P_LISTEN_PORT = 0          # 自动选择端口

   # 密钥文件路径
   PRIVATE_KEY_FILE = './private_key.pem'  # 修改为适合您的路径
   PUBLIC_KEY_FILE = './public_key.pem'    # 修改为适合您的路径
   ```

## 8. 启动系统

### 启动服务器

1. 进入服务器目录：
   ```bash
   cd ./server_new
   ```

2. 启动服务器：
   ```bash
   python main.py
   ```

3. 服务器启动成功后会在控制台显示相关日志信息

### 启动客户端

1. 进入客户端目录：
   ```bash
   cd ./client_new
   ```

2. 启动客户端Web应用：
   ```bash
   python main.py
   ```

3. 打开浏览器访问：`http://localhost:5000/`

## 9. 故障排除

1. **数据库连接错误**：
   - 检查SQL Server服务是否正在运行
   - 验证数据库用户名和密码
   - 确认已安装ODBC Driver 17 for SQL Server

2. **客户端无法连接服务器**：
   - 检查服务器是否已启动
   - 验证客户端配置中的服务器地址和端口
   - 检查网络防火墙设置

3. **P2P通信问题**：
   - 确保NAT设置允许P2P连接
   - 检查防火墙是否允许动态端口通信
