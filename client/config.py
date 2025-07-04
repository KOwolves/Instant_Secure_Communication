import pyaudio

# 服务器配置
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 50000
SERVER_API = f"http://{SERVER_HOST}:{SERVER_PORT}/api"

# 客户端P2P监听配置
P2P_LISTEN_HOST = '0.0.0.0' # 监听所有可用接口，以便其他设备连接
P2P_LISTEN_PORT = 0         # 自动选择端口，客户端启动后会获取实际端口

# 数据传输缓冲区大小
BUFFER_SIZE = 4096

# 密钥文件路径
PRIVATE_KEY_FILE = ''
PUBLIC_KEY_FILE = ''

# 日志文件名
LOG_FILE = ''

# Flask应用配置
SECRET_KEY = 'i_love_bupt_scss'  # 用于会话加密的密钥
UPLOAD_FOLDER = 'uploads'        # 上传文件保存目录
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}  # 允许上传的文件类型

# 实例心跳配置
MAX_HEARTBEAT_INTERVAL = 60  # 最大心跳间隔（秒），超过此时间的实例将被视为离线

# 讯飞语音识别API配置
XUNFEI_APPID = ''  # 讯飞开放平台应用ID
XUNFEI_API_KEY = ''  # 讯飞开放平台API Key
XUNFEI_API_SECRET = ''  # 讯飞开放平台API Secret

# 客户端配置
CLIENT_INFO_FILE = "client_info.json"

# 音频配置
AUDIO_FORMAT = pyaudio.paInt16  # 音频格式
CHUNK = 1024  # 每个缓冲区的帧数
CHANNELS = 1  # 单声道
RATE = 16000  # 采样率
RECORD_SECONDS = 5  # 默认录音时长
