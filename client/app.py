import logging
import threading
import uuid  # 导入uuid模块用于生成唯一标识符
import time  # 导入time模块用于定时任务
import os
import socket
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room, send
import sys
import eventlet
import json
import base64

# 确保Socket.IO和Eventlet正确集成
eventlet.monkey_patch()

# 导入配置
# 导入配置
from config import SECRET_KEY, UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from config import SERVER_HOST, SERVER_PORT, P2P_LISTEN_HOST, P2P_LISTEN_PORT, BUFFER_SIZE
from config import MAX_HEARTBEAT_INTERVAL

# 导入自定义模块
from chat_client import ChatClient

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [UI] %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

# Flask 应用初始化
app = Flask(__name__, static_folder="static", template_folder="template")
app.config['SECRET_KEY'] = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上传文件大小为16MB
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# 全局字典来存储 ChatClient 实例
# 修改为使用(username, instance_id, port)作为键，值是对应的 ChatClient 实例
active_clients = {}
active_clients_lock = threading.Lock()  # 保护 active_clients 字典

# 全局实例注册表，用于跟踪所有活跃的实例
# 格式: {username: {instance_id: {last_heartbeat: timestamp, port: port_number, sid: socketio_sid}}}
instance_registry = {}
registry_lock = threading.Lock()

# 最长心跳间隔，超过此时间的实例将被视为不活跃 (秒)
MAX_HEARTBEAT_INTERVAL = 60

# 防重复登出机制
logout_in_progress = set()
logout_lock = threading.Lock()

# 心跳检查和广播间隔 (秒)
HEARTBEAT_INTERVAL = 10

# 心跳线程
heartbeat_thread = None
stop_heartbeat = threading.Event()

# 获取当前服务器端口
def get_server_port():
    """获取当前服务器正在使用的端口"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('0.0.0.0', 0))
        port = sock.getsockname()[1]
        sock.close()
        return port
    except:
        # 如果无法获取，返回默认端口
        return request.environ.get('SERVER_PORT', 5000)

# 生成客户端实例键
def generate_client_key(username, instance_id, port=None):
    """生成用于active_clients字典的唯一键"""
    if port is None:
        port = get_server_port()
    return f"{username}:{instance_id}:{port}"

def register_instance(username, instance_id, port=None):
    """
    将实例注册到全局实例注册表
    """
    if not username or not instance_id:
        return
    
    with registry_lock:
        if username not in instance_registry:
            instance_registry[username] = {}
        
        instance_registry[username][instance_id] = {
            'last_heartbeat': time.time(),
            'port': port,
            'sid': None  # SocketIO SID，将在连接时更新
        }
    
    logger.info(f"已注册实例: 用户 {username} (实例ID: {instance_id}, 端口: {port})")


def update_instance_heartbeat(username, instance_id, sid=None, port=None):
    """
    更新实例的最后心跳时间和可选的SocketIO SID
    """
    if not username or not instance_id:
        return
    
    with registry_lock:
        if username in instance_registry and instance_id in instance_registry[username]:
            instance_registry[username][instance_id]['last_heartbeat'] = time.time()
            if sid:
                instance_registry[username][instance_id]['sid'] = sid
            if port is not None:
                instance_registry[username][instance_id]['port'] = port
            return True
    
    return False


def deregister_instance(username, instance_id, port=None):
    """
    从注册表中移除实例
    """
    if not username or not instance_id:
        return
    
    with registry_lock:
        if username in instance_registry and instance_id in instance_registry[username]:
            del instance_registry[username][instance_id]
            if not instance_registry[username]:  # 如果用户没有更多实例，移除用户
                del instance_registry[username]
            logger.info(f"已注销实例: 用户 {username} (实例ID: {instance_id}, 端口: {port})")
            return True
    
    return False


def get_active_instances(username):
    """
    获取用户的所有活跃实例ID
    """
    active_instances = []
    current_time = time.time()
    
    with registry_lock:
        if username in instance_registry:
            for instance_id, info in list(instance_registry[username].items()):
                # 检查实例是否活跃
                if current_time - info['last_heartbeat'] <= MAX_HEARTBEAT_INTERVAL:
                    active_instances.append(instance_id)
                else:
                    # 移除不活跃的实例
                    logger.info(f"移除不活跃实例: 用户 {username} (实例ID: {instance_id})")
                    del instance_registry[username][instance_id]
    
    return active_instances


def broadcast_registry_update():
    """
    向所有实例广播注册表更新
    """
    # 清理不活跃的实例
    cleanup_inactive_instances()
    
    # 广播更新 - 修复broadcast参数错误
    with registry_lock:
        # 使用正确的Flask-SocketIO广播方式
        socketio.emit('registry_update', {'registry': instance_registry}, room='/')


def cleanup_inactive_instances():
    """
    清理不活跃的实例
    """
    current_time = time.time()
    removed = []
    
    with registry_lock:
        for username in list(instance_registry.keys()):
            for instance_id in list(instance_registry[username].keys()):
                if current_time - instance_registry[username][instance_id]['last_heartbeat'] > MAX_HEARTBEAT_INTERVAL:
                    port = instance_registry[username][instance_id].get('port')
                    del instance_registry[username][instance_id]
                    removed.append((username, instance_id, port))
                    logger.info(f"清理不活跃实例: 用户 {username} (实例ID: {instance_id}, 端口: {port})")
            
            # 如果用户没有更多实例，移除用户
            if not instance_registry[username]:
                del instance_registry[username]
    
    # 同时从active_clients移除
    with active_clients_lock:
        for username, instance_id, port in removed:
            client_key = generate_client_key(username, instance_id, port)
            if client_key in active_clients:
                del active_clients[client_key]
                logger.info(f"从活跃客户端字典中移除不活跃实例: {client_key}")
    
    return removed


def ensure_instance_registry_integrity():
    """
    确保实例注册表完整性和一致性的函数
    这是为了解决实例丢失的核心问题
    """
    try:
        # 打印当前状态
        logger.info(f"开始实例完整性检查: 活跃客户端数量: {len(active_clients)}, 注册表用户数: {len(instance_registry)}")
        
        # 1. 检查所有active_clients中的实例是否正确注册
        with active_clients_lock:
            for client_key, client in list(active_clients.items()):
                parts = client_key.split(':')
                if len(parts) >= 2:  # 新格式 username:instance_id[:port]
                    username = parts[0]
                    instance_id = parts[1]
                    port = int(parts[2]) if len(parts) > 2 else None
                    
                    # 确保该实例在注册表中
                    with registry_lock:
                        if username not in instance_registry or instance_id not in instance_registry[username]:
                            # 发现未注册的实例，进行注册
                            if hasattr(client, 'p2p_manager') and hasattr(client.p2p_manager, 'p2p_actual_port'):
                                if port is None:  # 如果client_key中没有端口，使用p2p_actual_port
                                    port = client.p2p_manager.p2p_actual_port
                            
                            register_instance(username, instance_id, port)
                            logger.info(f"自动修复: 为活跃客户端 {client_key} 重新注册到实例注册表")
                else:  # 旧格式 username
                    # 为旧格式创建新的实例ID并迁移
                    username = client_key
                    instance_id = str(uuid.uuid4())
                    
                    # 获取端口
                    port = None
                    if hasattr(client, 'p2p_manager') and hasattr(client.p2p_manager, 'p2p_actual_port'):
                        port = client.p2p_manager.p2p_actual_port
                    
                    # 创建新的客户端键
                    new_client_key = generate_client_key(username, instance_id, port)
                    
                    # 迁移客户端
                    active_clients[new_client_key] = client
                    del active_clients[username]
                    
                    # 注册新实例
                    register_instance(username, instance_id, port)
                    logger.info(f"自动修复: 将旧格式客户端 {username} 迁移为 {new_client_key}")
        
        # 2. 检查所有注册表中的实例是否都有对应的active_client
        with registry_lock:
            for username, instances in list(instance_registry.items()):
                for instance_id in list(instances.keys()):
                    port = instance_registry[username][instance_id].get('port')
                    client_key = generate_client_key(username, instance_id, port)
                    
                    with active_clients_lock:
                        # 如果注册表中的实例没有对应的客户端，检查是否应该移除
                        if client_key not in active_clients:
                            # 检查是否有另一个端口的相同(username, instance_id)的客户端存在
                            found = False
                            for key in active_clients.keys():
                                if key.startswith(f"{username}:{instance_id}:"):
                                    found = True
                                    # 更新注册表中的端口信息
                                    new_port = int(key.split(':')[2])
                                    instance_registry[username][instance_id]['port'] = new_port
                                    logger.info(f"自动修复: 更新实例 {username}:{instance_id} 的端口从 {port} 到 {new_port}")
                                    break
                            
                            # 如果确实没有找到，并且超过心跳时间，则移除
                            if not found:
                                current_time = time.time()
                                last_heartbeat = instance_registry[username][instance_id]['last_heartbeat']
                                if current_time - last_heartbeat > MAX_HEARTBEAT_INTERVAL:
                                    del instance_registry[username][instance_id]
                                    logger.info(f"自动修复: 从注册表移除无效实例 {username}:{instance_id}")
                                    # 如果用户没有更多实例，移除用户
                                    if not instance_registry[username]:
                                        del instance_registry[username]
                                        break
        
        # 打印最终状态
        logger.info(f"完整性检查完成: 活跃客户端数量: {len(active_clients)}, 注册表用户数: {len(instance_registry)}")
        
        # 记录所有活跃客户端的键和注册表内容
        active_keys = list(active_clients.keys())
        logger.info(f"活跃客户端: {active_keys}")
        logger.info(f"注册表实例: {instance_registry}")
    
    except Exception as e:
        logger.error(f"实例完整性检查时发生错误: {str(e)}")


def heartbeat_thread_function():
    """
    心跳线程函数，定期执行以下操作:
    1. 清理不活跃的实例
    2. 广播注册表更新
    3. 确保实例注册表完整性
    """
    logger.info("心跳线程启动")
    
    while not stop_heartbeat.is_set():
        try:
            # 首先运行自动修复功能
            ensure_instance_registry_integrity()
            
            # 广播注册表更新
            broadcast_registry_update()
            
            # 每个间隔检查一次停止事件
            stop_heartbeat.wait(HEARTBEAT_INTERVAL)
        except Exception as e:
            logger.error(f"心跳线程发生错误: {str(e)}")
            # 在出错后等待短暂时间避免CPU占用过高
            time.sleep(1)
    
    logger.info("心跳线程停止")


def start_heartbeat_thread():
    """
    启动心跳线程
    """
    global heartbeat_thread, stop_heartbeat
    
    if heartbeat_thread and heartbeat_thread.is_alive():
        return
    
    stop_heartbeat.clear()
    heartbeat_thread = threading.Thread(target=heartbeat_thread_function)
    heartbeat_thread.daemon = True
    heartbeat_thread.start()


def stop_heartbeat_thread():
    """
    停止心跳线程
    """
    global stop_heartbeat
    
    stop_heartbeat.set()
    if heartbeat_thread:
        heartbeat_thread.join(timeout=2.0)


# 根据用户名和实例ID获取客户端实例的辅助函数
def get_client_instance(username, instance_id=None, port=None):
    """
    根据用户名和可选的实例ID获取客户端实例
    如果没有提供实例ID，尝试从会话中获取
    增强了实例查找能力，支持更复杂的恢复场景
    """
    if not username:
        return None
    
    # 记录寻找实例的详细日志
    logger.info(f"尝试获取用户 {username} 的客户端实例, 实例ID: {instance_id}, 端口: {port}")
    
    # 如果未提供端口，尝试获取当前端口
    if port is None:
        port = get_server_port()
    
    found_client = None
    
    # 1. 如果提供了实例ID，直接尝试获取
    if instance_id:
        client_key = generate_client_key(username, instance_id, port)
        found_client = active_clients.get(client_key)
        if found_client:
            logger.info(f"已通过实例ID直接找到客户端: {client_key}")
            return found_client
        
        # 如果指定端口找不到，尝试查找任何端口的相同(username, instance_id)
        with active_clients_lock:
            for key, client in active_clients.items():
                if key.startswith(f"{username}:{instance_id}:"):
                    found_client = client
                    logger.info(f"已找到不同端口的客户端实例: {key}")
                    # 更新会话中的实例ID
                    if 'instance_id' not in session or session.get('instance_id') != instance_id:
                        session['instance_id'] = instance_id
                    return found_client
    
    # 2. 如果没有提供实例ID或找不到，尝试从会话中获取
    if not found_client and 'instance_id' in session:
        session_instance_id = session.get('instance_id')
        if session_instance_id:
            client_key = generate_client_key(username, session_instance_id, port)
            found_client = active_clients.get(client_key)
            if found_client:
                logger.info(f"已通过会话中的实例ID找到客户端: {client_key}")
                return found_client
            else:
                # 尝试查找任何端口的相同(username, session_instance_id)
                with active_clients_lock:
                    for key, client in active_clients.items():
                        if key.startswith(f"{username}:{session_instance_id}:"):
                            found_client = client
                            logger.info(f"已找到不同端口的客户端实例: {key}")
                            return found_client
                
                logger.warning(f"会话中存在实例ID {session_instance_id}，但未找到对应的客户端实例")
    
    # 3. 如果仍然找不到，检查是否有任何活跃的实例
    if not found_client:
        logger.info(f"尝试查找用户 {username} 的任何活跃实例")
        active_instances = get_active_instances(username)
        logger.info(f"找到活跃实例: {active_instances}")
        
        for inst_id in active_instances:
            # 首先尝试指定端口
            client_key = generate_client_key(username, inst_id, port)
            if client_key in active_clients:
                found_client = active_clients[client_key]
                # 更新会话中的实例ID
                if 'instance_id' not in session or session.get('instance_id') != inst_id:
                    session['instance_id'] = inst_id
                    logger.info(f"已切换到活跃实例: {inst_id} (用户: {username}, 端口: {port})")
                return found_client
            
            # 如果指定端口找不到，尝试任何端口
            with active_clients_lock:
                for key, client in active_clients.items():
                    if key.startswith(f"{username}:{inst_id}:"):
                        found_client = client
                        # 更新会话中的实例ID
                        if 'instance_id' not in session or session.get('instance_id') != inst_id:
                            session['instance_id'] = inst_id
                            logger.info(f"已切换到活跃实例: {inst_id} (用户: {username}, 其他端口)")
                        return found_client
    
    # 4. 兼容旧版：如果找不到任何实例，尝试直接用用户名获取
    if not found_client:
        found_client = active_clients.get(username)
        logger.info(f"尝试查找旧格式实例 (用户: {username}): {'成功' if found_client else '失败'}")
        
        # 5. 如果找到了旧版实例，自动迁移到新的命名方式
        if found_client and not instance_id:
            # 创建新的实例ID
            new_instance_id = str(uuid.uuid4())
            session['instance_id'] = new_instance_id
            
            # 获取端口信息
            client_port = port
            if hasattr(found_client, 'p2p_manager') and hasattr(found_client.p2p_manager, 'p2p_actual_port'):
                client_port = found_client.p2p_manager.p2p_actual_port
            
            # 迁移实例
            client_key = generate_client_key(username, new_instance_id, client_port)
            with active_clients_lock:
                active_clients[client_key] = found_client
                # 从旧键中删除
                if username in active_clients:
                    del active_clients[username]
                # 注册实例
                register_instance(username, new_instance_id, client_port)
            
            logger.info(f"已将旧版实例 {username} 迁移至新格式 {client_key}")
            return found_client
    
    # 6. 如果仍然找不到，尝试通过自动检查和修复来恢复
    if not found_client:
        logger.warning(f"未找到用户 {username} 的任何实例，尝试自动修复...")
        ensure_instance_registry_integrity()
        
        # 再次尝试获取
        if instance_id:
            client_key = generate_client_key(username, instance_id, port)
            found_client = active_clients.get(client_key)
            if found_client:
                logger.info(f"修复后找到客户端: {client_key}")
                return found_client
            
            # 尝试查找任何端口的相同(username, instance_id)
            with active_clients_lock:
                for key, client in active_clients.items():
                    if key.startswith(f"{username}:{instance_id}:"):
                        found_client = client
                        logger.info(f"修复后找到不同端口的客户端实例: {key}")
                        return found_client
        
        # 尝试旧格式
        if not found_client:
            found_client = active_clients.get(username)
            if found_client:
                logger.info(f"修复后找到旧格式客户端: {username}")
                return found_client
    
    # 最终结果
    if found_client:
        logger.info(f"成功获取用户 {username} 的客户端实例")
    else:
        logger.error(f"无法获取用户 {username} 的客户端实例，可能已丢失")
    
    return found_client


# --- Flask 路由 ---

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录路由：显示登录表单，处理登录请求。"""
    if 'username' in session:  # 如果用户已登录，重定向到仪表板
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # 为新会话创建唯一的实例ID
        instance_id = str(uuid.uuid4())
        
        # 获取当前端口
        current_port = get_server_port()

        # 创建临时的 ChatClient 实例进行登录尝试
        temp_client = ChatClient(socketio)

        # 尝试登录
        if temp_client.login(username, password):
            # 登录成功，将客户端信息存储到会话
            session['username'] = username
            session['user_id'] = temp_client.logged_in_user_id
            
            # 确保P2P端口已正确配置
            if hasattr(temp_client, 'p2p_manager') and hasattr(temp_client.p2p_manager, 'p2p_actual_port'):
                p2p_port = temp_client.p2p_manager.p2p_actual_port
                session['client_socket_port'] = p2p_port
            else:
                logger.warning(f"无法获取P2P端口，用户 {username}")
                p2p_port = None
            
            session['instance_id'] = instance_id  # 存储实例ID到会话
            session['server_port'] = current_port  # 存储服务器端口到会话
            
            # 使用组合键(username:instance_id:port)存储 ChatClient 实例
            client_key = generate_client_key(username, instance_id, current_port)
            with active_clients_lock:
                active_clients[client_key] = temp_client
            
            # 注册实例到注册表
            register_instance(username, instance_id, current_port)
            
            # 确保心跳线程正在运行
            start_heartbeat_thread()
            
            logger.info(f"用户 {username} (实例ID: {instance_id}, 端口: {current_port}) 登录成功并添加到活跃客户端。")
            flash('登录成功！', 'success')
            return redirect(url_for('dashboard'))
        else:
            temp_client.disconnect_server()
            if hasattr(temp_client, 'p2p_manager'):
                temp_client.p2p_manager.stop_p2p_listener()
                temp_client.p2p_manager.close_all_p2p_connections()
            flash('登录失败，请检查用户名和密码。', 'danger')
    
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """注册路由：显示注册表单，处理注册请求。"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        temp_client = ChatClient(socketio)
        if temp_client.register(username, password):
            flash('注册成功，请登录！', 'success')
            logger.info(f"新用户 {username} 注册成功。")
            temp_client.disconnect_server()
            return redirect(url_for('login'))
        else:
            flash('注册失败，用户名可能已存在或服务器错误。', 'danger')
            logger.warning(f"用户 {username} 注册失败。")
            temp_client.disconnect_server()
            return render_template('index.html', username=username)
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    """仪表板路由：显示当前用户、在线好友和所有好友。"""
    if 'username' not in session:
        flash('请先登录。', 'warning')
        return redirect(url_for('login'))

    username = session['username']
    instance_id = session.get('instance_id')
    port = session.get('server_port', get_server_port())
    client = get_client_instance(username, instance_id, port)

    if not client:
        logger.warning(f"用户 {username} 的仪表板加载失败：客户端实例丢失")
        
        # 尝试恢复机制：查找该用户的其他活跃实例
        active_instances = get_active_instances(username)
        
        if active_instances:
            # 找到了其他活跃实例，尝试切换
            logger.info(f"尝试切换到用户 {username} 的其他活跃实例: {active_instances}")
            
            for inst_id in active_instances:
                # 尝试查找任何端口的实例
                with active_clients_lock:
                    for key, client_inst in active_clients.items():
                        if key.startswith(f"{username}:{inst_id}:"):
                            client = client_inst
                            session['instance_id'] = inst_id
                            # 从键中提取端口
                            parts = key.split(':')
                            if len(parts) > 2:
                                try:
                                    port = int(parts[2])
                                    session['server_port'] = port
                                except:
                                    pass
                            logger.info(f"成功切换到实例 {inst_id}, 端口: {port}")
                            
                            # 确保心跳更新
                            update_instance_heartbeat(username, inst_id, None, port)
                            break
                    if client:
                        break
        
        # 如果仍然没有找到客户端实例，清理会话并要求重新登录
        if not client:
            flash('会话已过期或客户端实例丢失，请重新登录。', 'danger')
            return redirect(url_for('logout'))  # 强制登出
    
    # 确保实例注册表更新
    if instance_id != session.get('instance_id') and session.get('instance_id'):
        instance_id = session.get('instance_id')
        logger.info(f"实例ID已在恢复过程中更新为: {instance_id}")

    # 更新好友列表
    client.get_online_friends()  # 获取在线好友
    all_friends = client.get_all_friends()  # 获取所有好友

    return render_template('main.html',
                           username=username,
                           online_friends=client.online_friends_info.values(),
                           all_friends=all_friends)


@app.route('/add_friend', methods=['POST'])
def add_friend():
    """添加好友路由。"""
    if 'username' not in session:
        return redirect(url_for('login'))

    friend_username = request.form['friend_username']
    username = session['username']
    instance_id = session.get('instance_id')
    port = session.get('server_port', get_server_port())
    client = get_client_instance(username, instance_id, port)
    
    if client and client.add_friend(friend_username):
        # 通知被添加的好友更新其好友列表
        # 注意：这里需要遍历所有实例查找friend_username的所有可能实例
        with active_clients_lock:
            for key, friend_client in active_clients.items():
                # 检查是否是friend_username的任何实例
                parts = key.split(':')
                if len(parts) >= 1 and parts[0] == friend_username:
                    # 更新被添加方的好友列表
                    friend_client.get_online_friends()
                    friend_client.get_all_friends()
                    # 通过SocketIO通知被添加方
                    if hasattr(friend_client, 'current_socketio_sid') and friend_client.current_socketio_sid:
                        socketio.emit('friend_added', {
                            'friend': session['username'],
                            'message': f'{session["username"]} 已添加您为好友'
                        }, room=friend_client.current_socketio_sid)
        
        flash(f'已成功添加 {friend_username} 为好友。', 'success')
    else:
        flash(f'添加好友 {friend_username} 失败。', 'danger')
    return redirect(url_for('dashboard'))


@app.route('/remove_friend', methods=['POST'])
def remove_friend():
    """删除好友路由。"""
    if 'username' not in session:
        return redirect(url_for('login'))

    friend_username = request.form['friend_username']
    username = session['username']
    instance_id = session.get('instance_id')
    port = session.get('server_port', get_server_port())
    client = get_client_instance(username, instance_id, port)
    
    if client and client.remove_friend(friend_username):
        flash(f'已将 {friend_username} 从好友列表中移除。', 'info')
    else:
        flash(f'删除好友 {friend_username} 失败。', 'danger')
    return redirect(url_for('dashboard'))


@app.route('/chat/<recipient_username>')
def chat_window(recipient_username):
    """聊天窗口路由。"""
    if 'username' not in session:
        flash('请先登录。', 'warning')
        return redirect(url_for('login'))

    username = session['username']
    instance_id = session.get('instance_id')
    port = session.get('server_port', get_server_port())
    
    # 确保客户端实例存在
    client = get_client_instance(username, instance_id, port)
    if not client:
        flash('会话已过期或客户端实例丢失，请重新登录。', 'danger')
        return redirect(url_for('logout'))
    
    # 获取在线好友和所有好友信息
    client.get_online_friends()
    all_friends = client.get_all_friends()
    
    return render_template('main.html',
                           username=username,
                           recipient=recipient_username,
                           online_friends=client.online_friends_info.values(),
                           all_friends=all_friends)


@app.route('/send_steg_image', methods=['POST'])
def send_steg_image():
    """处理隐写图片发送请求。"""
    if 'username' not in session:
        return redirect(url_for('login'))

    recipient_username = request.form['recipient_username']
    hidden_message = request.form['hidden_message']

    # 确保文件被上传
    if 'image_file' not in request.files:
        flash('未选择图片文件。', 'danger')
        return redirect(url_for('dashboard'))  # 或者重定向到聊天窗口

    image_file = request.files['image_file']
    if image_file.filename == '':
        flash('未选择图片文件。', 'danger')
        return redirect(url_for('dashboard'))

    client = get_client_instance(session['username'])
    if not client:
        flash('会话已过期或客户端实例丢失，请重新登录。', 'danger')
        return redirect(url_for('logout'))

    # 读取图片字节数据
    image_bytes = image_file.read()

    if client.send_steg_image_message(recipient_username, image_bytes, hidden_message):
        flash(f'隐写图片已成功发送给 {recipient_username}。', 'success')
    else:
        flash(f'发送隐写图片给 {recipient_username} 失败。', 'danger')

    return redirect(url_for('chat_window', recipient_username=recipient_username))  # 发送后回到聊天窗口

def _handle_logout(username, force=False):
    """统一处理用户登出的内部函数。"""
    if not username:
        logger.warning("_handle_logout: 无效的用户名")
        return False

    # 获取实例ID和端口
    instance_id = session.get('instance_id')
    port = session.get('server_port', get_server_port())
    
    # 防止重复登出
    with logout_lock:
        logout_key = generate_client_key(username, instance_id, port) if instance_id else username
        if logout_key in logout_in_progress and not force:
            logger.warning(f"用户 {username} 已在登出过程中，跳过重复登出")
            return False
        logout_in_progress.add(logout_key)

    try:
        # 获取客户端实例
        client = get_client_instance(username, instance_id, port)
        
        if client:
            # 从客户端注销
            logger.info(f"正在关闭用户 {username} (实例ID: {instance_id}, 端口: {port}) 的客户端实例资源...")
            # 向服务器发送登出消息
            client.logout()
            
            # 关闭客户端与服务器的连接
            client.disconnect_server()
            
            # 关闭 P2P 相关资源
            if hasattr(client, 'p2p_manager'):
                client.p2p_manager.stop_p2p_listener()
                client.p2p_manager.close_all_p2p_connections()
            
            # 从活跃客户端字典中移除
            with active_clients_lock:
                # 移除使用组合键的客户端
                if instance_id:
                    client_key = generate_client_key(username, instance_id, port)
                    if client_key in active_clients:
                        del active_clients[client_key]
                        logger.info(f"已从活跃客户端字典移除用户 {username} (实例ID: {instance_id}, 端口: {port})")
                
                # 兼容旧版：也尝试移除直接使用用户名的客户端
                if username in active_clients:
                    del active_clients[username]
                    logger.info(f"已从活跃客户端字典移除用户 {username} (旧版直接使用用户名)")
            
            # 从实例注册表中移除
            deregister_instance(username, instance_id, port)
            
            # 广播注册表更新
            broadcast_registry_update()
        
        # 清理会话
        session.clear()
        logger.info(f"用户 {username} 登出成功")
        return True
        
    except Exception as e:
        logger.error(f"登出用户 {username} 时发生错误: {str(e)}")
        # 即使发生错误，也尝试清理会话
        session.clear()
        return False
    finally:
        # 确保总是移除登出标记
        with logout_lock:
            logout_in_progress.discard(logout_key)

@app.route('/logout')
def logout():
    """登出路由。"""
    username = session.get('username', '未知用户')
    if _handle_logout(username, force=False):
        flash('您已成功登出。', 'info')
    else:
        flash('登出过程中出现异常，但已清理会话。', 'warning')
    return redirect(url_for('login'))

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """API登出路由。"""
    try:
        # 获取当前用户名，如果不存在则使用默认值
        username = session.get('username')
        if not username:
            logger.warning("API登出：会话中未找到用户名")
            # 确保会话已清理
            session.clear()
            return jsonify({'success': True, 'message': '已成功登出（用户未登录）'})
        
        # 防重复登出检查
        with logout_lock:
            if username in logout_in_progress:
                logger.warning(f"API登出：用户 {username} 的登出请求正在进行中，忽略重复请求")
                return jsonify({'success': True, 'message': '登出请求已处理'})
            logout_in_progress.add(username)
        
        try:
            logger.info(f"API登出：开始处理用户 {username} 的登出请求")
            
            # 调用统一的登出处理函数
            if _handle_logout(username, force=False):
                logger.info(f"API登出：用户 {username} 登出成功")
                return jsonify({'success': True, 'message': '已成功登出'})
            else:
                logger.warning(f"API登出：用户 {username} 登出过程中出现异常")
                return jsonify({'success': True, 'message': '登出完成（清理过程中出现异常，但会话已清理）'})
        finally:
            # 清理登出状态
            with logout_lock:
                logout_in_progress.discard(username)
            
    except Exception as e:
        logger.error(f"API登出路由出现未预期的错误: {e}")
        # 确保即使出错也要清理会话和登出状态
        try:
            session.clear()
        except:
            pass
        with logout_lock:
            logout_in_progress.discard(username)
        return jsonify({'success': True, 'message': '登出完成（出现异常，但会话已清理）'})


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or request.form
    username = data.get('username')
    password = data.get('password')
    
    # 为新会话创建唯一的实例ID
    instance_id = str(uuid.uuid4())
    
    # 获取当前端口
    current_port = get_server_port()
    
    temp_client = ChatClient(socketio)
    if temp_client.login(username, password):
        session['username'] = username
        session['user_id'] = temp_client.logged_in_user_id
        
        # 确保P2P端口已正确配置
        if hasattr(temp_client, 'p2p_manager') and hasattr(temp_client.p2p_manager, 'p2p_actual_port'):
            p2p_port = temp_client.p2p_manager.p2p_actual_port
            session['client_socket_port'] = p2p_port
        else:
            logger.warning(f"无法获取P2P端口，用户 {username}")
            p2p_port = None
            
        session['instance_id'] = instance_id  # 存储实例ID到会话
        session['server_port'] = current_port  # 存储服务器端口到会话
        
        # 使用组合键存储客户端实例
        client_key = generate_client_key(username, instance_id, current_port)
        with active_clients_lock:
            active_clients[client_key] = temp_client
        
        # 注册实例到注册表
        register_instance(username, instance_id, current_port)
        
        # 确保心跳线程正在运行
        start_heartbeat_thread()
        
        logger.info(f"用户 {username} (实例ID: {instance_id}, 端口: {current_port}) 登录成功并添加到活跃客户端。")
        return jsonify({'success': True, 'message': '登录成功！'})
    else:
        temp_client.disconnect_server()
        if hasattr(temp_client, 'p2p_manager'):
            temp_client.p2p_manager.stop_p2p_listener()
            temp_client.p2p_manager.close_all_p2p_connections()
        logger.warning(f"用户 {username} 登录失败。")
        return jsonify({'success': False, 'message': '登录失败，用户名或密码错误。'})

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json(silent=True) or request.form
    username = data.get('username')
    password = data.get('password')
    temp_client = ChatClient(socketio)
    if temp_client.register(username, password):
        logger.info(f"新用户 {username} 注册成功。")
        temp_client.disconnect_server()
        return jsonify({'success': True, 'message': '注册成功，请登录！'})
    else:
        temp_client.disconnect_server()
        logger.warning(f"用户 {username} 注册失败。")
        return jsonify({'success': False, 'message': '注册失败，用户名可能已存在或服务器错误。'})

@app.route('/api/add_friend', methods=['POST'])
def api_add_friend():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    data = request.get_json(silent=True) or request.form
    friend_username = data.get('friend_username')
    client = get_client_instance(session['username'])
    if client and client.add_friend(friend_username):
        # 通知被添加的好友更新其好友列表
        # 遍历所有实例查找friend_username的所有可能实例
        with active_clients_lock:
            for key, friend_client in active_clients.items():
                if key.startswith(f"{friend_username}:") or key == friend_username:
                    # 更新被添加方的好友列表
                    friend_client.get_online_friends()
                    friend_client.get_all_friends()
                    # 通过SocketIO通知被添加方
                    if hasattr(friend_client, 'current_socketio_sid') and friend_client.current_socketio_sid:
                        socketio.emit('friend_added', {
                            'friend': session['username'],
                            'message': f'{session["username"]} 已添加您为好友'
                        }, room=friend_client.current_socketio_sid)
        
        return jsonify({'success': True, 'message': f'已成功添加 {friend_username} 为好友。'})
    else:
        return jsonify({'success': False, 'message': f'添加好友 {friend_username} 失败。'})

@app.route('/api/remove_friend', methods=['POST'])
def api_remove_friend():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    data = request.get_json(silent=True) or request.form
    friend_username = data.get('friend_username')
    client = get_client_instance(session['username'])
    if client and client.remove_friend(friend_username):
        return jsonify({'success': True, 'message': f'已将 {friend_username} 从好友列表中移除。'})
    else:
        return jsonify({'success': False, 'message': f'删除好友 {friend_username} 失败。'})

@app.route('/api/send_steg_image', methods=['POST'])
def api_send_steg_image():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    # 获取参数，使用与前端匹配的参数名
    recipient = request.form.get('recipient')
    hidden_message = request.form.get('hidden_message')
    
    # 检查图片文件
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': '未选择图片文件。'})
    
    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'success': False, 'message': '未选择图片文件。'})
    
    # 获取客户端实例
    client = get_client_instance(session['username'])
    if not client:
        return jsonify({'success': False, 'message': '会话已过期或客户端实例丢失，请重新登录。'})
    
    # 读取图片字节数据
    image_bytes = image_file.read()
    
    # 记录发送信息
    logger.info(f"尝试发送隐写图片给 {recipient}，图片大小: {len(image_bytes)} 字节")
    
    # 发送隐写图片消息
    success = client.send_steg_image_message(recipient, image_bytes, hidden_message)
    
    if success:
        logger.info(f"隐写图片已成功发送给 {recipient}")
        # 生成临时图片URL返回给前端
        temp_image_filename = f"temp_steg_image_sent_{os.urandom(4).hex()}.png"
        temp_image_path_abs = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', temp_image_filename)
        
        try:
            with open(temp_image_path_abs, "wb") as f:
                f.write(image_bytes)
            
            # 生成URL路径
            image_url = url_for('static', filename=temp_image_filename)
            
            return jsonify({
                'success': True, 
                'message': f'隐写图片已成功发送给 {recipient}。',
                'image_url': image_url
            })
        except Exception as e:
            logger.error(f"保存临时图片时出错: {e}")
            return jsonify({
                'success': True,
                'message': f'隐写图片已成功发送给 {recipient}，但无法生成预览。'
            })
    else:
        logger.error(f"发送隐写图片给 {recipient} 失败")
        return jsonify({'success': False, 'message': f'发送隐写图片给 {recipient} 失败。'})


@app.route('/api/get_all_friends', methods=['GET'])
def api_get_all_friends():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    client = get_client_instance(session['username'])
    if client:
        friends = client.get_all_friends()
        return jsonify({'success': True, 'friends': friends})
    else:
        return jsonify({'success': False, 'message': '客户端实例丢失'})

@app.route('/api/refresh_friends', methods=['POST'])
def api_refresh_friends():
    """刷新好友列表API。支持通过用户ID或session查询"""
    # 获取请求数据
    data = request.get_json() or {}
    user_id = data.get('user_id')
    
    client = None
    
    # 优先使用用户ID查询
    if user_id:
        # 根据用户ID查找对应的客户端实例
        # 由于active_clients是以(username:instance_id)为键存储的，需要遍历查找
        for key, client_instance in active_clients.items():
            if hasattr(client_instance, 'logged_in_user_id') and str(client_instance.logged_in_user_id) == str(user_id):
                client = client_instance
                logger.info(f"通过用户ID {user_id} 找到对应的客户端实例 {key}")
                
                # 提取用户名和实例ID
                username = key.split(':')[0] if ':' in key else key
                instance_id = key.split(':')[1] if ':' in key else None
                
                # 更新心跳
                if username and instance_id:
                    update_instance_heartbeat(username, instance_id)
                
                break
    
    # 如果通过ID未找到，尝试通过session查询
    if client is None and 'username' in session:
        username = session.get('username')
        instance_id = session.get('instance_id')
        
        # 尝试获取客户端实例
        client = get_client_instance(username, instance_id)
        
        # 更新心跳
        if client and username and instance_id:
            update_instance_heartbeat(username, instance_id)
            logger.info(f"通过session找到对应的客户端实例 {username}:{instance_id}")
    
    # 如果找到客户端实例，返回好友列表
    if client:
        try:
            # 更新在线好友和所有好友列表
            client.get_online_friends()
            all_friends = client.get_all_friends()
            return jsonify({
                'success': True, 
                'online_friends': list(client.online_friends_info.values()),
                'all_friends': all_friends
            })
        except Exception as e:
            logger.error(f"刷新好友列表时出错: {str(e)}")
            return jsonify({'success': False, 'message': f'获取好友列表时出错: {str(e)}'})
    else:
        if user_id:
            logger.warning(f"未能通过用户ID {user_id} 找到对应的客户端实例")
        
        # 检查是否有可用的实例
        if 'username' in session:
            username = session.get('username')
            active_instances = get_active_instances(username)
            
            if active_instances:
                # 找到其他活跃实例
                return jsonify({
                    'success': False, 
                    'message': '当前会话的客户端实例丢失，但存在其他活跃实例',
                    'active_instances': active_instances
                })
        
        return jsonify({'success': False, 'message': '未找到客户端实例，请检查用户ID或登录状态'})

@app.route('/api/force_logout', methods=['POST'])
def api_force_logout():
    """强制登出API，用于处理异常情况。"""
    try:
        # 获取当前用户名，如果不存在则使用默认值
        username = session.get('username')
        if not username:
            logger.warning("强制登出API：会话中未找到用户名")
            session.clear()
            return jsonify({'success': True, 'message': '强制登出成功（用户未登录）'})
        
        logger.info(f"强制登出API：开始处理用户 {username} 的强制登出请求")
        
        # 调用统一的登出处理函数，使用强制模式
        if _handle_logout(username, force=True):
            logger.info(f"强制登出API：用户 {username} 强制登出成功")
            return jsonify({'success': True, 'message': '强制登出成功'})
        else:
            logger.warning(f"强制登出API：用户 {username} 强制登出过程中出现异常")
            return jsonify({'success': True, 'message': '强制登出完成（清理过程中出现异常，但会话已清理）'})
            
    except Exception as e:
        logger.error(f"强制登出API路由出现未预期的错误: {e}")
        # 确保即使出错也要清理会话
        try:
            session.clear()
        except:
            pass
        return jsonify({'success': True, 'message': '强制登出完成（出现异常，但会话已清理）'})

@app.route('/api/get_current_user', methods=['GET'])
def api_get_current_user():
    """获取当前登录用户的ID和用户名"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    try:
        username = session.get('username')
        client = get_client_instance(username)
        
        if not client:
            return jsonify({'success': False, 'message': '客户端实例丢失'})
        
        # 返回用户信息
        return jsonify({
            'success': True, 
            'user_id': client.logged_in_user_id,
            'username': username
        })
    except Exception as e:
        logger.error(f"获取当前用户信息时出错: {str(e)}")
        return jsonify({'success': False, 'message': f'获取用户信息时出错: {str(e)}'})

@app.route('/api/heartbeat', methods=['POST'])
def api_heartbeat():
    """接收客户端心跳，更新实例状态"""
    try:
        if 'username' not in session:
            return jsonify({'success': False, 'message': '未登录'}), 401
        
        username = session.get('username')
        instance_id = session.get('instance_id')
        
        if not username or not instance_id:
            return jsonify({'success': False, 'message': '会话信息不完整'}), 400
        
        # 更新实例心跳
        update_instance_heartbeat(username, instance_id)
        logger.debug(f"已更新用户 {username} 实例 {instance_id} 的心跳")
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"处理心跳时出错: {str(e)}")
        return jsonify({'success': False, 'message': f'处理心跳时出错: {str(e)}'}), 500

@app.route('/api/diagnostics', methods=['GET'])
def api_diagnostics():
    """消息传递诊断API，检查SocketIO连接和P2P连接状态"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    try:
        username = session.get('username')
        instance_id = session.get('instance_id')
        port = session.get('server_port', get_server_port())
        
        # 确保实例注册表完整性
        try:
            ensure_instance_registry_integrity()
        except Exception as e:
            logger.error(f"诊断时调用完整性检查出错: {str(e)}")
        
        # 收集诊断数据，即使客户端丢失也尽可能多地收集信息
        diagnostics_data = {
            'success': False,  # 默认设为失败，如果成功找到客户端再改为True
            'username': username,
            'instance_id': instance_id,
            'port': port,
            'socketio_connected': False,
            'socketio_sid': None,
            'p2p_connections': {},
            'online_friends': [],
            'logged_in': False,
            'active_instances': [],
            'current_time': time.time()
        }
        
        # 获取活跃实例信息，不依赖客户端实例
        try:
            active_instances = []
            for inst_id in get_active_instances(username):
                with registry_lock:
                    if username in instance_registry and inst_id in instance_registry[username]:
                        inst_info = instance_registry[username][inst_id]
                        if inst_info:  # 确保inst_info不是None
                            inst_port = inst_info.get('port') if inst_info else None
                            last_heartbeat = inst_info.get('last_heartbeat') if inst_info else None
                            sid = inst_info.get('sid') if inst_info else None
                            active_instances.append({
                                'instance_id': inst_id,
                                'port': inst_port,
                                'last_heartbeat': last_heartbeat,
                                'sid': sid,
                                'is_current': inst_id == instance_id and inst_port == port
                            })
            diagnostics_data['active_instances'] = active_instances
        except Exception as e:
            logger.error(f"获取活跃实例信息时出错: {str(e)}")
        
        # 更新心跳，即使没有实例ID也尝试更新
        if username:
            if instance_id:
                update_instance_heartbeat(username, instance_id, None, port)
            else:
                # 如果没有实例ID，尝试创建一个
                instance_id = str(uuid.uuid4())
                session['instance_id'] = instance_id
                session['server_port'] = port
                register_instance(username, instance_id, port)
                logger.info(f"诊断时为用户 {username} 创建新实例ID: {instance_id}, 端口: {port}")
                diagnostics_data['instance_id'] = instance_id
                diagnostics_data['port'] = port
        
        # 先尝试获取客户端实例
        client = get_client_instance(username, instance_id, port)
        
        # 如果找不到实例，尝试恢复机制
        if not client:
            logger.warning(f"诊断API: 未找到用户 {username} 的实例 {instance_id}，端口 {port}，尝试恢复...")
            
            # 查找其他实例
            active_instances = get_active_instances(username)
            
            if active_instances:
                # 找到了其他活跃实例，提供详细信息
                other_instances = []
                for inst_id in active_instances:
                    if inst_id != instance_id:  # 排除当前实例
                        with registry_lock:
                            if username in instance_registry and inst_id in instance_registry[username]:
                                inst_info = instance_registry[username][inst_id]
                                # 确保inst_info不是None
                                if inst_info:
                                    inst_port = inst_info.get('port') if inst_info else None
                                    last_heartbeat = inst_info.get('last_heartbeat') if inst_info else None
                                    other_instances.append({
                                        'instance_id': inst_id,
                                        'port': inst_port,
                                        'last_heartbeat': last_heartbeat,
                                        'sid': inst_info.get('sid') if inst_info else None
                                    })
                                    
                                    # 尝试切换到该实例
                                    client_key = generate_client_key(username, inst_id, inst_port)
                                    with active_clients_lock:
                                        if client_key in active_clients:
                                            client = active_clients[client_key]
                                            session['instance_id'] = inst_id
                                            session['server_port'] = inst_port
                                            logger.info(f"诊断时自动切换到实例: {inst_id}, 端口: {inst_port}")
                                            diagnostics_data['instance_id'] = inst_id
                                            diagnostics_data['port'] = inst_port
                                            break
                
                if client:
                    # 成功切换到其他实例
                    logger.info(f"成功恢复用户 {username} 的客户端实例")
                else:
                    # 找到了实例但无法切换
                    diagnostics_data['other_instances'] = other_instances
                    diagnostics_data['recovery'] = '请尝试重新登录或刷新页面'
                    # 但继续执行，尽可能收集信息
            
            # 尝试最后的恢复措施：检查是否有直接使用用户名的旧实例
            if not client:
                with active_clients_lock:
                    if username in active_clients:
                        client = active_clients[username]
                        logger.info(f"诊断时从旧版实例恢复用户 {username} 的客户端")
                        
                        # 注册这个实例
                        if not instance_id:
                            instance_id = str(uuid.uuid4())
                            session['instance_id'] = instance_id
                            diagnostics_data['instance_id'] = instance_id
                        
                        # 获取端口信息
                        client_port = port
                        if hasattr(client, 'p2p_manager') and hasattr(client.p2p_manager, 'p2p_actual_port'):
                            client_port = client.p2p_manager.p2p_actual_port
                            session['server_port'] = client_port
                            diagnostics_data['port'] = client_port
                        
                        # 将旧实例迁移到新的键
                        client_key = generate_client_key(username, instance_id, client_port)
                        active_clients[client_key] = client
                        del active_clients[username]  # 删除旧键
                        register_instance(username, instance_id, client_port)
                        logger.info(f"已将旧实例迁移到: {client_key}")
        
        # 如果找到了客户端，收集详细信息
        if client:
            diagnostics_data['success'] = True
            diagnostics_data['logged_in'] = client.logged_in_username is not None
        
            # 检查SocketIO连接
            try:
                diagnostics_data['socketio_connected'] = client.check_socketio_connection()
                diagnostics_data['socketio_sid'] = client.current_socketio_sid
            except Exception as e:
                logger.error(f"检查SocketIO连接时出错: {str(e)}")
        
            # 获取P2P连接信息
            try:
                p2p_connections = {}
                if hasattr(client, 'p2p_manager') and client.p2p_manager:
                    for peer, conn in client.p2p_manager.active_p2p_connections.items():
                        p2p_connections[peer] = {
                            'connected': conn is not None,
                            'details': str(conn) if conn else 'None'
                        }
                    diagnostics_data['p2p_connections'] = p2p_connections
            except Exception as e:
                logger.error(f"获取P2P连接信息时出错: {str(e)}")
        
            # 获取在线好友信息
            try:
                online_friends = []
                if hasattr(client, 'online_friends_info'):
                    online_friends = list(client.online_friends_info.keys())
                diagnostics_data['online_friends'] = online_friends
            except Exception as e:
                logger.error(f"获取在线好友信息时出错: {str(e)}")
        
        # 返回诊断信息
        return jsonify(diagnostics_data)
    except Exception as e:
        logger.error(f"获取诊断信息时出错: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'获取诊断信息时出错: {str(e)}',
            'username': session.get('username'),
            'instance_id': session.get('instance_id'),
            'port': session.get('server_port'),
            'current_time': time.time()
        })

@app.route('/api/search_user', methods=['POST'])
def api_search_user():
    """搜索用户API，用于查找可能添加的好友"""
    if 'username' not in session:
        logger.warning("搜索用户API：未登录用户尝试访问")
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    data = request.get_json() or {}
    search_term = data.get('username', '')
    logger.info(f"搜索用户API：用户 {session['username']} 搜索关键词 '{search_term}'")
    
    if not search_term:
        logger.warning("搜索用户API：未提供搜索关键词")
        return jsonify({'success': False, 'message': '请提供搜索关键词'})
    
    client = get_client_instance(session['username'])
    if not client:
        logger.error(f"搜索用户API：用户 {session['username']} 的客户端实例丢失")
        return jsonify({'success': False, 'message': '客户端实例丢失'})
    
    try:
        # 向服务器发送获取所有用户的请求
        logger.info(f"搜索用户API：向服务器发送GET_ALL_USERS命令")
        if client._send_request("GET_ALL_USERS"):
            response = client._receive_response()
            if response and response.get("status") == "success":
                all_users = response["data"]["users"]
                logger.info(f"搜索用户API：从服务器获取了 {len(all_users)} 个用户")
                
                # 根据搜索词过滤用户
                filtered_users = []
                for user in all_users:
                    if search_term.lower() in user["username"].lower():
                        filtered_users.append({
                            "username": user["username"],
                            "user_id": user["user_id"]
                        })
                
                # 排除当前用户自己
                filtered_users = [user for user in filtered_users if user["username"] != session['username']]
                
                logger.info(f"搜索用户API：找到 {len(filtered_users)} 个匹配 '{search_term}' 的用户")
                return jsonify({'success': True, 'users': filtered_users})
            else:
                error_msg = response.get('message', '未知错误') if response else '服务器无响应'
                logger.error(f"搜索用户API：获取用户列表失败: {error_msg}")
                return jsonify({'success': False, 'message': f'获取用户列表失败: {error_msg}'})
        else:
            logger.error("搜索用户API：向服务器发送GET_ALL_USERS命令失败")
            return jsonify({'success': False, 'message': '服务器请求失败'})
    except Exception as e:
        logger.error(f"搜索用户API：搜索用户时出错: {str(e)}")
        return jsonify({'success': False, 'message': f'搜索用户时出错: {str(e)}'})

# 页面加载API，用于恢复客户端实例
@app.route('/api/page_loaded', methods=['POST'])
def api_page_loaded():
    """页面加载时调用，确保客户端实例正确恢复"""
    try:
        if 'username' not in session:
            return jsonify({
                'success': False,
                'message': '未登录',
                'action': 'redirect',
                'redirect_url': '/login'
            }), 401
        
        username = session.get('username')
        instance_id = session.get('instance_id')
        
        # 如果没有实例ID，生成一个新的
        if not instance_id:
            instance_id = str(uuid.uuid4())
            session['instance_id'] = instance_id
            logger.info(f"页面加载API: 为用户 {username} 创建新实例ID: {instance_id}")
        
        # 确保实例注册表完整性
        try:
            ensure_instance_registry_integrity()
        except Exception as e:
            logger.error(f"页面加载时调用完整性检查出错: {str(e)}")
        
        # 尝试获取客户端实例
        client = get_client_instance(username, instance_id)
        
        # 收集诊断数据
        result = {
            'success': client is not None,
            'username': username,
            'instance_id': instance_id,
            'logged_in': False,
            'current_time': time.time()
        }
        
        # 如果找到了客户端实例
        if client:
            result['logged_in'] = client.logged_in_username is not None
            
            # 更新心跳
            update_instance_heartbeat(username, instance_id)
            
            # 尝试检查连接状态
            try:
                result['socketio_connected'] = client.check_socketio_connection()
                result['socketio_sid'] = client.current_socketio_sid
            except Exception as e:
                logger.error(f"页面加载API: 检查SocketIO连接时出错: {str(e)}")
        else:
            # 尝试恢复过程
            logger.warning(f"页面加载API: 未找到用户 {username} 的实例 {instance_id}，尝试恢复...")
            
            # 查找其他活跃实例
            active_instances = get_active_instances(username)
            
            if active_instances:
                other_instances = []
                for inst_id in active_instances:
                    if inst_id != instance_id:
                        with registry_lock:
                            if username in instance_registry and inst_id in instance_registry[username]:
                                inst_info = instance_registry[username][inst_id]
                                if inst_info:
                                    other_instances.append({
                                        'instance_id': inst_id,
                                        'port': inst_info.get('port') if inst_info else None,
                                        'last_heartbeat': inst_info.get('last_heartbeat') if inst_info else None
                                    })
                
                if other_instances:
                    # 找到了其他实例，尝试切换
                    target_instance = other_instances[0]['instance_id']
                    client_key = f"{username}:{target_instance}"
                    
                    if client_key in active_clients:
                        client = active_clients[client_key]
                        session['instance_id'] = target_instance
                        logger.info(f"页面加载API: 自动切换到实例 {target_instance}")
                        
                        result['success'] = True
                        result['instance_id'] = target_instance
                        result['logged_in'] = client.logged_in_username is not None
                        
                        # 更新心跳
                        update_instance_heartbeat(username, target_instance)
                    else:
                        # 找到了实例信息但没有实例对象
                        result['other_instances'] = other_instances
                        result['message'] = '找到其他实例但无法切换'
            
            # 如果没有其他实例或切换失败，尝试从旧格式恢复
            if not result['success'] and username in active_clients:
                client = active_clients[username]
                logger.info(f"页面加载API: 从旧格式实例恢复用户 {username}")
                
                # 如果没有实例ID，创建一个
                if not instance_id:
                    instance_id = str(uuid.uuid4())
                    session['instance_id'] = instance_id
                
                # 迁移旧实例
                with active_clients_lock:
                    client_key = f"{username}:{instance_id}"
                    active_clients[client_key] = client
                    register_instance(username, instance_id, 
                                     getattr(client.p2p_manager, 'p2p_actual_port', None))
                
                result['success'] = True
                result['instance_id'] = instance_id
                result['logged_in'] = client.logged_in_username is not None
        
        # 返回结果
        return jsonify(result)
    except Exception as e:
        logger.error(f"处理页面加载请求时出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'处理页面加载请求时出错: {str(e)}',
            'username': session.get('username'),
            'instance_id': session.get('instance_id'),
            'current_time': time.time()
        }), 500

# --- SocketIO 事件处理 ---

@socketio.on('connect')
def handle_connect():
    """处理SocketIO连接事件。"""
    try:
        sid = request.sid
        username = session.get('username')
        instance_id = session.get('instance_id')
        port = session.get('server_port', get_server_port())
        
        if username and instance_id:
            # 加入用户特定的房间
            user_room = f'user_{username}'
            join_room(user_room)
            logger.info(f"SocketIO连接: SID={sid}，加入房间 {user_room}")
            
            # 更新SocketIO会话ID
            client = get_client_instance(username, instance_id, port)
            if client:
                client.current_socketio_sid = sid
                # 更新注册表中的SID
                update_instance_heartbeat(username, instance_id, sid, port)
                logger.info(f"已更新用户 {username} (实例ID: {instance_id}, 端口: {port}) 的SocketIO SID")
            else:
                logger.warning(f"用户 {username} 的客户端实例未找到，无法更新SocketIO SID")
        else:
            logger.info(f"SocketIO连接: SID={sid}, 无用户关联")
    except Exception as e:
        logger.error(f"处理SocketIO连接时出错: {str(e)}")


@socketio.on('disconnect')
def handle_disconnect():
    """处理SocketIO断开连接事件。"""
    try:
        sid = request.sid
        username = session.get('username')
        instance_id = session.get('instance_id')
        port = session.get('server_port', get_server_port())
        
        if username:
            user_room = f'user_{username}'
            leave_room(user_room)
            logger.info(f"SocketIO连接断开: SID={sid}")
            logger.info(f"用户 {username} 的房间 {user_room} 连接已断开")
            
            # 不要立即注销用户，这只是SocketIO断开，用户可能仍在使用
            # 但可以清除客户端实例中的socketio_sid
            client = get_client_instance(username, instance_id, port)
            if client:
                client.current_socketio_sid = None
                logger.info(f"已清除用户 {username} (实例ID: {instance_id}, 端口: {port}) 的SocketIO SID")
    except Exception as e:
        logger.error(f"处理SocketIO断开连接时出错: {str(e)}")


@socketio.on('heartbeat')
def handle_heartbeat(data):
    """处理从客户端发送的心跳消息，更新实例活跃状态。"""
    try:
        sid = request.sid
        username = session.get('username')
        instance_id = session.get('instance_id')
        port = session.get('server_port', get_server_port())
        
        if not all([username, instance_id]):
            return {'success': False, 'message': '未登录或会话不完整'}
        
        # 更新心跳时间
        update_instance_heartbeat(username, instance_id, sid, port)
        logger.debug(f"收到用户 {username} (实例ID: {instance_id}, 端口: {port}) 的心跳")
        
        # 获取客户端实例
        client = get_client_instance(username, instance_id, port)
        
        if client:
            # 更新SocketIO SID
            client.current_socketio_sid = sid
            return {'success': True, 'timestamp': time.time()}
        else:
            logger.warning(f"心跳处理: 未找到用户 {username} (实例ID: {instance_id}) 的客户端实例")
            return {'success': False, 'message': '客户端实例丢失'}
    except Exception as e:
        logger.error(f"处理心跳时出错: {str(e)}")
        return {'success': False, 'message': f'错误: {str(e)}'}


def send_to_user(username, event, data):
    """向特定用户的所有实例发送SocketIO事件。"""
    try:
        # 创建用户特定的房间名
        room_name = f'user_{username}'
        # 发送到用户的房间
        socketio.emit(event, data, room=room_name)
        logger.debug(f"已向用户 {username} 的房间 {room_name} 发送事件 {event}")
        return True
    except Exception as e:
        logger.error(f"向用户 {username} 发送事件 {event} 时出错: {str(e)}")
        return False

@socketio.on('send_message')
def handle_send_message(data):
    """处理来自Web客户端的发送聊天消息事件。"""
    if 'username' not in session:
        socketio.emit('message_error', {'error': '未登录'}, room=request.sid)
        return

    recipient_username = data.get('recipient', '')
    message_content = data.get('message', '')
    
    logger.info(f"收到发送消息请求：用户 {session.get('username')} (实例ID: {session.get('instance_id')}) 向 {recipient_username} 发送消息")
    logger.info(f"当前SocketIO SID: {request.sid}")

    client = get_client_instance(session.get('username'))
    if client and recipient_username and message_content:
        
        # 触发前端显示加密状态
        socketio.emit('message_status', {'status': 'encrypting', 'message': message_content}, room=request.sid)
        
        # 调用客户端的P2P加密消息发送方法
        send_result = client.send_p2p_message(recipient_username, message_content)
        
        if send_result:
            # 消息已发送（加密），可以通过 SocketIO 实时更新发送者自己的聊天窗口
            logger.info(f"准备在UI上显示发送成功的消息，发送到SID: {request.sid}")
            socketio.emit('receive_message', {
                'sender': client.logged_in_user_id, 
                'recipient': recipient_username, 
                'message': message_content
            }, room=request.sid)
            socketio.emit('message_status', {'status': 'sent', 'message': message_content}, room=request.sid)
            logger.info(f"UI通知: 用户 {session['username']} 成功向 {recipient_username} 发送消息")
        else:
            logger.error(f"消息发送失败: 用户 {session.get('username')} 向 {recipient_username} 发送消息: \"{message_content}\"")
            socketio.emit('message_error', {'error': '加密消息发送失败'}, room=request.sid)
            socketio.emit('message_status', {'status': 'failed', 'message': message_content}, room=request.sid)
            logger.error(f"UI通知: 用户 {session['username']} 向 {recipient_username} 发送消息失败")
    else:
        logger.warning(f"消息发送条件不满足: client存在: {client is not None}, 收件人: {recipient_username}, 消息内容长度: {len(message_content) if message_content else 0}")
        socketio.emit('message_error', {'error': '无效的收件人或消息内容。'}, room=request.sid)

@socketio.on('refresh_friends')
def handle_refresh_friends():
    """处理刷新好友列表请求。"""
    if 'username' not in session:
        socketio.emit('refresh_friends_error', {'error': '未登录'}, room=request.sid)
        return

    client = get_client_instance(session.get('username'))
    if client:
        client.get_online_friends()
        client.get_all_friends()
        
        # 从客户端实例中获取在线好友和所有好友信息
        all_friends = client.get_all_friends()
        
        socketio.emit('friends_refreshed', {
            'online_friends': list(client.online_friends_info.values()),
            'all_friends': all_friends
        }, room=request.sid)
        logger.info(f"已为用户 {session['username']} 刷新好友列表")
    else:
        socketio.emit('refresh_friends_error', {'error': '客户端实例丢失'}, room=request.sid)

@socketio.on('refresh_online_friends')
def handle_refresh_online_friends():
    if 'username' not in session:
        socketio.emit('refresh_friends_error', {'error': '未登录'}, room=request.sid)
        return
    client = get_client_instance(session['username'])
    if client:
        client.get_online_friends()
        
        socketio.emit('online_friends_updated', {
            'online_friends': list(client.online_friends_info.values())
        }, room=request.sid)
        logger.info(f"已为用户 {session['username']} 刷新在线好友列表")
    else:
        socketio.emit('refresh_friends_error', {'error': '客户端实例丢失'}, room=request.sid)

@socketio.on('force_reconnect')
def handle_force_reconnect(data):
    """处理前端请求的强制重连操作，用于实例恢复"""
    try:
        sid = request.sid
        if 'username' not in session:
            logger.warning("未登录用户尝试强制重连")
            return
        
        username = session.get('username')
        current_instance_id = session.get('instance_id')
        target_instance_id = data.get('instance_id')
        
        logger.info(f"用户 {username} 请求强制重连, 当前实例: {current_instance_id}, 目标实例: {target_instance_id}")
        
        if not target_instance_id or current_instance_id == target_instance_id:
            # 无需切换实例，只需重新加入房间
            room_name = f"user_{username}"
            join_room(room_name)
            logger.info(f"用户 {username} 重新加入房间: {room_name}, SID: {sid}")
            
            # 更新当前实例的SID
            client = get_client_instance(username, current_instance_id)
            if client:
                client.current_socketio_sid = sid
                logger.info(f"已更新用户 {username} 当前实例的SocketIO SID: {sid}")
                
                # 发送确认消息
                socketio.emit('reconnect_result', {
                    'success': True,
                    'message': '已重新连接到当前实例',
                    'instance_id': current_instance_id
                })
            else:
                logger.error(f"强制重连失败: 找不到用户 {username} 的当前实例")
                socketio.emit('reconnect_result', {
                    'success': False,
                    'message': '找不到当前实例'
                })
        else:
            # 尝试切换到目标实例
            client_key = f"{username}:{target_instance_id}"
            if client_key in active_clients:
                # 更新会话中的实例ID
                session['instance_id'] = target_instance_id
                
                # 加入新的房间
                room_name = f"user_{username}"
                join_room(room_name)
                
                # 更新实例的SID
                client = active_clients[client_key]
                if client:
                    client.current_socketio_sid = sid
                    logger.info(f"已切换到实例 {target_instance_id} 并更新SocketIO SID: {sid}")
                    
                    # 发送确认消息
                    socketio.emit('reconnect_result', {
                        'success': True,
                        'message': '已切换到目标实例',
                        'instance_id': target_instance_id
                    })
                else:
                    logger.error(f"切换实例失败: 找不到目标实例 {target_instance_id}")
                    socketio.emit('reconnect_result', {
                        'success': False,
                        'message': '找不到目标实例'
                    })
            else:
                logger.error(f"切换实例失败: 找不到目标实例 {target_instance_id}")
                socketio.emit('reconnect_result', {
                    'success': False,
                    'message': '找不到目标实例'
                })
    except Exception as e:
        logger.error(f"处理强制重连请求时出错: {str(e)}")
        socketio.emit('reconnect_result', {
            'success': False,
            'message': f'处理重连请求时出错: {str(e)}'
        })

@app.route('/api/send_audio', methods=['POST'])
def api_send_audio():
    """处理语音消息发送请求"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    # 检查音频文件
    if 'audio' not in request.files:
        return jsonify({'success': False, 'message': '未选择音频文件。'})
    
    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'success': False, 'message': '未选择音频文件。'})
    
    # 获取接收者用户名
    recipient = request.form.get('recipient')
    if not recipient:
        return jsonify({'success': False, 'message': '未指定接收者。'})
    
    # 获取客户端实例
    client = get_client_instance(session['username'])
    if not client:
        return jsonify({'success': False, 'message': '会话已过期或客户端实例丢失，请重新登录。'})
    
    # 读取音频字节数据
    audio_bytes = audio_file.read()
    
    # 记录发送信息
    logger.info(f"尝试发送语音消息给 {recipient}，音频大小: {len(audio_bytes)} 字节")
    
    # 发送语音消息
    success = client.send_audio_message(recipient, audio_bytes)
    
    if success:
        logger.info(f"语音消息已成功发送给 {recipient}")
        # 生成持久化音频文件名，使用发送者ID_接收者_时间戳格式
        timestamp = int(time.time())
        sender_id = str(client.logged_in_user_id).replace(" ", "_")
        recipient_clean = recipient.replace(" ", "_")
        temp_audio_filename = f"audio_sent_{sender_id}_{recipient_clean}_{timestamp}.wav"
        temp_audio_path_abs = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', temp_audio_filename)
        
        try:
            with open(temp_audio_path_abs, "wb") as f:
                f.write(audio_bytes)
            
            # 生成URL路径
            audio_url = url_for('static', filename=temp_audio_filename)
            
            return jsonify({
                'success': True, 
                'message': f'语音消息已成功发送给 {recipient}。',
                'audio_url': audio_url
            })
        except Exception as e:
            logger.error(f"保存临时音频时出错: {e}")
            return jsonify({
                'success': True,
                'message': f'语音消息已成功发送给 {recipient}，但无法生成预览。'
            })
    else:
        logger.error(f"发送语音消息给 {recipient} 失败")
        return jsonify({'success': False, 'message': f'发送语音消息给 {recipient} 失败。'})
