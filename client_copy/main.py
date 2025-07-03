import logging
import sys
import eventlet
import time
import threading
import argparse
import socket

# 确保在导入其他模块前执行monkey_patch
eventlet.monkey_patch()

# 导入 Flask 应用
from app import app, socketio, ensure_instance_registry_integrity, start_heartbeat_thread

# 配置客户端应用的全局日志
logging.basicConfig(level=logging.INFO,  # 默认日志级别为 INFO
                    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s',  # 简化日志格式
                    handlers=[
                        logging.StreamHandler(sys.stdout)  # 确保日志输出到标准输出
                    ])

# 为核心模块设置合适的日志级别，专注于通信状态
logging.getLogger('utils.RSA').setLevel(logging.INFO) # 只显示重要RSA操作
logging.getLogger('utils.AES').setLevel(logging.INFO) # 只显示重要AES操作
logging.getLogger('p2p_manager').setLevel(logging.INFO) # 显示P2P连接状态
logging.getLogger('chat_client').setLevel(logging.INFO) # 显示消息发送和接收状态
logging.getLogger('flask_app').setLevel(logging.WARNING) # 减少不必要的Flask日志

# 检查端口是否被占用
def is_port_available(port):
    """检查指定端口是否可用"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('0.0.0.0', port))
        sock.close()
        return result != 0
    except:
        return False

# 添加启动时的自动修复功能
def startup_repair():
    """启动时的自动修复函数，确保在启动后定期检查实例完整性"""
    logger = logging.getLogger(__name__)
    logger.info("开始执行启动时的自动修复...")
    
    # 立即进行第一次检查
    try:
        ensure_instance_registry_integrity()
        logger.info("启动时的实例完整性检查完成")
    except Exception as e:
        logger.error(f"启动修复过程中出错: {str(e)}")
    
    # 确保心跳线程启动
    try:
        start_heartbeat_thread()
        logger.info("心跳监控线程已启动")
    except Exception as e:
        logger.error(f"启动心跳监控线程时出错: {str(e)}")

# Flask-SocketIO 推荐通过 socketio.run(app) 来启动应用
if __name__ == "__main__":
    logger = logging.getLogger(__name__)  # 获取 main_client 模块的 logger 实例
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='启动客户端应用')
    parser.add_argument('--port', type=int, default=5001, help='指定服务器端口 (默认: 5001)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='指定服务器主机 (默认: 0.0.0.0)')
    args = parser.parse_args()
    
    # 检查端口是否可用
    if not is_port_available(args.port):
        # 如果端口不可用，尝试使用其他端口
        for port in range(5001, 5100):
            if is_port_available(port):
                logger.warning(f"端口 {args.port} 已被占用，使用备用端口 {port}")
                args.port = port
                break
        else:
            logger.error(f"无法找到可用端口，尝试使用端口 {args.port}")
    
    # 根据端口动态设置唯一的会话Cookie名称，防止多实例会话冲突
    app.config['SESSION_COOKIE_NAME'] = f'p2p_chat_session_port_{args.port}'
    
    logger.info(f"客户端Web应用启动于 {args.host}:{args.port}")
    
    # 启动自动修复线程
    repair_thread = threading.Thread(target=startup_repair)
    repair_thread.daemon = True
    repair_thread.start()
    
    # 启动 Flask-SocketIO 应用，它会使用 eventlet 或 gevent 运行
    socketio.run(app, host=args.host, port=args.port, debug=True, allow_unsafe_werkzeug=True)
    logger.info("客户端Web应用已停止。")
