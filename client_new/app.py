import logging
import threading

from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify
from flask_socketio import SocketIO, emit, join_room
import sys

# 导入自定义模块
from chat_client import ChatClient

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

# Flask 应用初始化
app = Flask(__name__, template_folder='template')
app.config['SECRET_KEY'] = 'i_love_bupt_scss'  # 替换为强密钥，用于会话加密
socketio = SocketIO(app, async_mode='eventlet')  # 使用 eventlet 作为异步模式

# 全局字典来存储 ChatClient 实例
# 键是 Flask session ID (sid)，值是对应的 ChatClient 实例
# 这是一个简化的会话管理，生产环境可能需要更复杂的持久化方案
active_clients = {}
active_clients_lock = threading.Lock()  # 保护 active_clients 字典


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

        # 获取或创建 ChatClient 实例
        # 对于登录，理论上应该根据username获取其Client实例，这里为了简化，
        # 暂时为每个请求尝试创建一个ChatClient，并在登录成功后存储
        # 实际生产环境会更复杂，例如在服务器端维护一个全局ChatClient池，并按需分配

        # 创建临时的 ChatClient 实例进行登录尝试
        # 注意：这里直接传入socketio实例，Login成功后会设置P2PManager的身份信息
        temp_client = ChatClient(socketio)

        # 尝试登录
        if temp_client.login(username, password):
            # 登录成功，将客户端信息存储到会话和全局活跃客户端字典
            session['username'] = username
            session['user_id'] = temp_client.logged_in_user_id
            session['client_socket_port'] = temp_client.p2p_manager.p2p_actual_port  # P2P实际监听端口
            # 存储 ChatClient 实例
            with active_clients_lock:
                active_clients[session['username']] = temp_client  # 用用户名作为键
            logger.info(f"用户 {username} (SID: {session.get('username')}) 登录成功并添加到活跃客户端。")
            flash('登录成功！', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('登录失败，用户名或密码错误。', 'danger')
            # 登录失败，确保临时客户端的资源被清理
            temp_client.disconnect_server()
            temp_client.p2p_manager.stop_p2p_listener()
            temp_client.p2p_manager.close_all_p2p_connections()
            logger.warning(f"用户 {username} 登录失败。")
            return render_template('index.html', username=username)
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
    client = active_clients.get(username) if username else None

    if not client:
        flash('会话已过期或客户端实例丢失，请重新登录。', 'danger')
        return redirect(url_for('logout'))  # 强制登出

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
    client = active_clients.get(session['username'])
    if client and client.add_friend(friend_username):
        flash(f'已发送好友请求给 {friend_username}。', 'success')  # 简化，这里直接加好友
    else:
        flash(f'添加好友 {friend_username} 失败。', 'danger')
    return redirect(url_for('dashboard'))


@app.route('/remove_friend', methods=['POST'])
def remove_friend():
    """删除好友路由。"""
    if 'username' not in session:
        return redirect(url_for('login'))

    friend_username = request.form['friend_username']
    client = active_clients.get(session['username'])
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
    return render_template('main.html',
                           username=username,
                           recipient=recipient_username)


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

    client = active_clients.get(session['username'])
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


@app.route('/logout')
def logout():
    """登出路由。"""
    username = session.get('username', '未知用户')
    client = active_clients.get(username) if username else None
    if client:
        client.logout()  # 调用 ChatClient 的登出方法
        with active_clients_lock:
            del active_clients[username]  # 从全局字典中移除客户端实例
        logger.info(f"用户 {username} (SID: {session.get('username')}) 已登出并从活跃客户端中移除。")
    session.clear()  # 清除 Flask 会话
    flash('您已成功登出。', 'info')
    return redirect(url_for('login'))


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.form or request.json
    username = data.get('username')
    password = data.get('password')
    temp_client = ChatClient(socketio)
    if temp_client.login(username, password):
        session['username'] = username
        session['user_id'] = temp_client.logged_in_user_id
        session['client_socket_port'] = temp_client.p2p_manager.p2p_actual_port
        with active_clients_lock:
            active_clients[session['username']] = temp_client
        logger.info(f"用户 {username} (SID: {session.get('username')}) 登录成功并添加到活跃客户端。")
        return jsonify({'success': True, 'message': '登录成功！'})
    else:
        temp_client.disconnect_server()
        temp_client.p2p_manager.stop_p2p_listener()
        temp_client.p2p_manager.close_all_p2p_connections()
        logger.warning(f"用户 {username} 登录失败。")
        return jsonify({'success': False, 'message': '登录失败，用户名或密码错误。'})

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.form or request.json
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
    data = request.form or request.json
    friend_username = data.get('friend_username')
    client = active_clients.get(session['username'])
    if client and client.add_friend(friend_username):
        return jsonify({'success': True, 'message': f'已发送好友请求给 {friend_username}。'})
    else:
        return jsonify({'success': False, 'message': f'添加好友 {friend_username} 失败。'})

@app.route('/api/remove_friend', methods=['POST'])
def api_remove_friend():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    data = request.form or request.json
    friend_username = data.get('friend_username')
    client = active_clients.get(session['username'])
    if client and client.remove_friend(friend_username):
        return jsonify({'success': True, 'message': f'已将 {friend_username} 从好友列表中移除。'})
    else:
        return jsonify({'success': False, 'message': f'删除好友 {friend_username} 失败。'})

@app.route('/api/send_steg_image', methods=['POST'])
def api_send_steg_image():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    recipient_username = request.form.get('recipient_username')
    hidden_message = request.form.get('hidden_message')
    if 'image_file' not in request.files:
        return jsonify({'success': False, 'message': '未选择图片文件。'})
    image_file = request.files['image_file']
    if image_file.filename == '':
        return jsonify({'success': False, 'message': '未选择图片文件。'})
    client = active_clients.get(session['username'])
    if not client:
        return jsonify({'success': False, 'message': '会话已过期或客户端实例丢失，请重新登录。'})
    image_bytes = image_file.read()
    if client.send_steg_image_message(recipient_username, image_bytes, hidden_message):
        return jsonify({'success': True, 'message': f'隐写图片已成功发送给 {recipient_username}。'})
    else:
        return jsonify({'success': False, 'message': f'发送隐写图片给 {recipient_username} 失败。'})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True, 'message': '已登出'})

# --- SocketIO 事件处理 ---

@socketio.on('connect')
def handle_connect():
    """处理SocketIO客户端连接事件。"""
    # 当浏览器通过 SocketIO 连接时，将其 SID 与 Flask 会话关联起来
    if 'username' in session and session.get('username') in active_clients:
        client = active_clients[session.get('username')]
        client.current_socketio_sid = request.sid  # 将 SocketIO 的 request.sid 存储到 ChatClient 实例中
        logger.info(
            f"SocketIO连接建立: 用户 {session['username']} (Flask SID: {session.get('username')}, SocketIO SID: {request.sid})")
        # 加入一个以 Flask session.sid 命名的房间，以便后续可以精确推送消息
        join_room(session.get('username'))
    else:
        logger.warning(f"SocketIO连接尝试，但Flask会话未找到或ChatClient实例不存在。SID: {request.sid}")
        # 如果没有有效的会话，断开SocketIO连接
        return False  # 拒绝连接


@socketio.on('disconnect')
def handle_disconnect():
    """处理SocketIO客户端断开连接事件。"""
    logger.info(
        f"SocketIO连接断开: 用户 {session.get('username', '未知')} (Flask SID: {session.get('username')}, SocketIO SID: {request.sid})")
    # 注意：这里不执行logout，因为可能是浏览器刷新，ChatClient实例仍在后台运行。
    # 真正的logout应该通过 /logout 路由触发。


@socketio.on('send_message')
def handle_send_message(data):
    """处理来自Web客户端的发送聊天消息事件。"""
    if 'username' not in session:
        emit('message_error', {'error': '未登录'}, room=request.sid)
        return

    recipient_username = data.get('recipient')
    message_content = data.get('message')

    client = active_clients.get(session.get('username'))
    if client and recipient_username and message_content:
        logger.info(f"用户 {session['username']} 尝试向 {recipient_username} 发送消息: {message_content}")
        if client.send_p2p_message(recipient_username, message_content):
            # 消息已发送（加密），可以通过 SocketIO 实时更新发送者自己的聊天窗口
            emit('receive_message', {'sender': '我', 'message': message_content}, room=request.sid)
            logger.info(f"消息已发送并推送到发送者浏览器。")
        else:
            emit('message_error', {'error': '消息发送失败'}, room=request.sid)
            logger.error(f"消息发送失败从用户 {session['username']} 到 {recipient_username}")
    else:
        emit('message_error', {'error': '无效的收件人或消息内容。'}, room=request.sid)
