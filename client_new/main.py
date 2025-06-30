import logging
import sys
import eventlet # 导入 eventlet，因为 Flask-SocketIO 使用它作为异步工作器

# 导入 Flask 应用
from app import app, socketio

# 配置客户端应用的全局日志
logging.basicConfig(level=logging.INFO, # 默认日志级别为 INFO
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s', # 日志格式
                    handlers=[
                        logging.StreamHandler(sys.stdout) # 确保日志输出到标准输出
                    ])

# 可以为特定模块设置更详细的日志级别，例如，开启 DEBUG 级别的日志
logging.getLogger('rsa_utils').setLevel(logging.DEBUG)
logging.getLogger('aes_utils').setLevel(logging.DEBUG)
logging.getLogger('p2p_manager').setLevel(logging.DEBUG)
logging.getLogger('chat_client').setLevel(logging.DEBUG) # 开启 chat_client 的 DEBUG 日志
logging.getLogger('flask_app').setLevel(logging.DEBUG) # 开启 flask_app 的 DEBUG 日志

# Flask-SocketIO 推荐通过 socketio.run(app) 来启动应用
if __name__ == "__main__":
    logger = logging.getLogger(__name__) # 获取 main_client 模块的 logger 实例
    logger.info("客户端Web应用启动。")
    # 启动 Flask-SocketIO 应用，它会使用 eventlet 或 gevent 运行
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True) # debug=True 方便开发，allow_unsafe_werkzeug 允许在生产环境以外使用调试器
    logger.info("客户端Web应用已停止。")