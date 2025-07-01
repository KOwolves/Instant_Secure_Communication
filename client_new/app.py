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

# 防重复登出机制
logout_in_progress = set()
logout_lock = threading.Lock()


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
        # 通知被添加的好友更新其好友列表
        friend_client = active_clients.get(friend_username)
        if friend_client:
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

def _handle_logout(username, force=False):
    """统一的登出处理函数，消除重复代码。"""
    if not username or username == '未知用户':
        logger.warning("登出处理：用户名无效或未提供")
        session.clear()
        return True
    
    client = active_clients.get(username)
    
    try:
        if client:
            try:
                if force:
                    # 强制登出：直接清理资源，不调用客户端的 logout 方法
                    logger.info(f"开始强制登出用户 {username}")
                    client.logged_in_username = None
                    client.logged_in_user_id = None
                    client.online_friends_info.clear()
                    client.current_socketio_sid = None
                    client.disconnect_server()
                    logger.info(f"用户 {username} 强制登出完成")
                else:
                    # 正常登出：调用客户端的 logout 方法
                    logger.info(f"开始正常登出用户 {username}")
                    client.logout()
                    logger.info(f"用户 {username} 正常登出完成")
            except Exception as client_error:
                logger.error(f"客户端登出过程中出错: {client_error}")
                # 即使客户端登出失败，也要尝试清理资源
                try:
                    if hasattr(client, 'disconnect_server'):
                        client.disconnect_server()
                except Exception as cleanup_error:
                    logger.error(f"清理客户端资源时出错: {cleanup_error}")
            
            # 从活跃客户端字典中移除
            try:
                with active_clients_lock:
                    if username in active_clients:
                        del active_clients[username]
                        logger.info(f"已从活跃客户端字典中移除用户 {username}")
            except Exception as dict_error:
                logger.error(f"从活跃客户端字典中移除用户时出错: {dict_error}")
        else:
            logger.info(f"用户 {username} 的客户端实例不存在，跳过客户端清理")
        
        # 清除 Flask 会话
        try:
            session.clear()
            logger.info(f"已清除用户 {username} 的Flask会话")
        except Exception as session_error:
            logger.error(f"清除Flask会话时出错: {session_error}")
        
        return True
    except Exception as e:
        logger.error(f"登出处理时出现未预期的错误: {e}")
        # 确保即使出错也要尝试清理会话
        try:
            session.clear()
        except:
            pass
        return False

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
        # 通知被添加的好友更新其好友列表
        friend_client = active_clients.get(friend_username)
        if friend_client:
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


@app.route('/api/get_all_friends', methods=['GET'])
def api_get_all_friends():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    client = active_clients.get(session['username'])
    if client:
        friends = client.get_all_friends()
        return jsonify({'success': True, 'friends': friends})
    else:
        return jsonify({'success': False, 'message': '客户端实例丢失'})

@app.route('/api/refresh_friends', methods=['POST'])
def api_refresh_friends():
    """刷新好友列表API。"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    client = active_clients.get(session['username'])
    if client:
        # 更新在线好友和所有好友列表
        client.get_online_friends()
        all_friends = client.get_all_friends()
        return jsonify({
            'success': True, 
            'online_friends': list(client.online_friends_info.values()),
            'all_friends': all_friends
        })
    else:
        return jsonify({'success': False, 'message': '客户端实例丢失'})

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
    username = session.get('username', '未知')
    logger.info(
        f"SocketIO连接断开: 用户 {username} (Flask SID: {session.get('username')}, SocketIO SID: {request.sid})")
    
    # 清理客户端实例的 SocketIO SID
    if username in active_clients:
        client = active_clients[username]
        if hasattr(client, 'current_socketio_sid'):
            client.current_socketio_sid = None
        logger.info(f"已清理用户 {username} 的 SocketIO SID")
    
    # 注意：这里不执行完整的logout，因为可能是浏览器刷新，ChatClient实例仍在后台运行。
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

@socketio.on('refresh_friends')
def handle_refresh_friends():
    """处理刷新好友列表请求。"""
    if 'username' not in session:
        emit('refresh_friends_error', {'error': '未登录'}, room=request.sid)
        return

    client = active_clients.get(session.get('username'))
    if client:
        # 更新好友列表
        client.get_online_friends()
        all_friends = client.get_all_friends()
        
        # 发送更新后的好友列表给客户端
        emit('friends_updated', {
            'online_friends': list(client.online_friends_info.values()),
            'all_friends': all_friends
        }, room=request.sid)
        logger.info(f"已为用户 {session['username']} 刷新好友列表")
    else:
        emit('refresh_friends_error', {'error': '客户端实例丢失'}, room=request.sid)

@socketio.on('refresh_online_friends')
def handle_refresh_online_friends():
    if 'username' not in session:
        emit('refresh_friends_error', {'error': '未登录'}, room=request.sid)
        return
    client = active_clients.get(session['username'])
    if client:
        client.get_online_friends()
        # 只推送在线好友
        emit('online_friends_updated', {
            'online_friends': list(client.online_friends_info.values())
        }, room=request.sid)
        logger.info(f"已为用户 {session['username']} 刷新在线好友列表")
    else:
        emit('refresh_friends_error', {'error': '客户端实例丢失'}, room=request.sid)
