# 服务器配置
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 50000

# 客户端P2P监听配置
P2P_LISTEN_HOST = '0.0.0.0' # 监听所有可用接口，以便其他设备连接
P2P_LISTEN_PORT = 0         # 自动选择端口，客户端启动后会获取实际端口

# 数据传输缓冲区大小
BUFFER_SIZE = 4096

# 密钥文件路径
PRIVATE_KEY_FILE = 'D:\\Projects\\Python\\Instant_Secure_Communication\\client_copy\\private_key.pem'
PUBLIC_KEY_FILE = 'D:\\Projects\\Python\\Instant_Secure_Communication\\client_copy\\public_key.pem'

# 日志文件名
LOG_FILE = 'D:\\Projects\\Python\\Instant_Secure_Communication\\client_copy\\client.log'

# Flask应用配置
SECRET_KEY = 'i_love_bupt_scss'  # 用于会话加密的密钥
UPLOAD_FOLDER = 'uploads'        # 上传文件保存目录
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}  # 允许上传的文件类型

# 实例心跳配置
MAX_HEARTBEAT_INTERVAL = 60  # 最大心跳间隔（秒），超过此时间的实例将被视为离线
