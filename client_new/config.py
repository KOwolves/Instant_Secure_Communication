# 服务器配置
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 50000

# 客户端P2P监听配置
P2P_LISTEN_HOST = '0.0.0.0' # 监听所有可用接口，以便其他设备连接
P2P_LISTEN_PORT = 0         # 自动选择端口，客户端启动后会获取实际端口

# 数据传输缓冲区大小
BUFFER_SIZE = 4096

# 密钥文件路径
PRIVATE_KEY_FILE = 'private_key.pem'
PUBLIC_KEY_FILE = 'public_key.pem'

# 日志文件名
LOG_FILE = 'client.log'
