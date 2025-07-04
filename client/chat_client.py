import socket
import json
import os
import time
import base64

from config import SERVER_HOST, SERVER_PORT, P2P_LISTEN_HOST, P2P_LISTEN_PORT, BUFFER_SIZE, PRIVATE_KEY_FILE, \
    PUBLIC_KEY_FILE
from utils.RSA import RSAUtils  # 导入 RSA 工具类
from utils.AES import AESUtils  # 导入 AES 工具类
from p2p_manager import P2PManager  # 导入P2P管理器
from utils.STEG import StegUtils  # 导入隐写术工具类
from utils.AUDIO import AudioUtils  # 导入音频工具类

import logging

logger = logging.getLogger(__name__)


class ChatClient:
    """
    ChatClient 是即时通讯客户端的核心类。
    它负责与中心服务器的通信、用户状态管理，并协调加密操作和P2P通信。
    """

    def __init__(self, socketio_instance):  # 构造函数中接收 SocketIO 实例
        self.server_socket = None  # 与中心服务器通信的socket对象
        self.logged_in_user_id = None  # 当前登录用户的唯一ID（由服务器分配）
        self.logged_in_username = None  # 当前登录用户的用户名
        self.my_public_key = None  # 当前用户的公钥对象（RSA公钥）
        self.my_public_key_pem = None  # 当前用户的公钥PEM格式字符串，用于网络传输和存储

        # 接收 Flask-SocketIO 实例，以便在 P2P 消息接收时可以向浏览器推送
        self.socketio_instance = socketio_instance
        # 用于存储当前 SocketIO 会话ID，以便向特定浏览器推送消息
        self.current_socketio_sid = None

        # 初始化 RSAUtils 实例，负责所有 RSA 加密相关操作
        self.rsa_util = RSAUtils()
        # 初始化 AESUtils 实例，负责所有 AES 对称加密相关操作
        self.aes_util = AESUtils()
        # 初始化 StegUtils 实例，负责图片隐写术操作
        self.steg_util = StegUtils()
        # 初始化 AudioUtils 实例，负责音频处理操作
        self.audio_util = AudioUtils()

        self._load_or_generate_key_pair()  # 在客户端启动时加载或生成密钥对

        # 初始化 P2PManager 实例，负责所有P2P连接的建立、监听和原始数据收发。
        self.p2p_manager = P2PManager(
            p2p_listen_host=P2P_LISTEN_HOST,
            p2p_listen_port=P2P_LISTEN_PORT,
            buffer_size=BUFFER_SIZE,
            socketio_instance=self.socketio_instance,
            sid_getter_callback=self._get_current_socketio_sid,
            decrypt_and_process_callback=self._handle_p2p_received_raw_data,  # 收到加密数据后的解密处理回调
            identity_info={"username": "初始化用户", "public_key_pem": self.my_public_key_pem}
        )

        # 存储在线好友的信息 {username: {user_id, ip, port, public_key_pem}}
        self.online_friends_info = {}

    def _get_current_socketio_sid(self):
        """获取当前SocketIO会话ID。"""
        return self.current_socketio_sid

    def check_socketio_connection(self):
        """检查SocketIO连接的状态，用于诊断问题。"""
        if not self.socketio_instance:
            logger.error("SocketIO实例不存在")
            return False
        
        if not self.current_socketio_sid:
            logger.error("SocketIO会话ID不存在，可能未连接")
            return False
        
        logger.info(f"当前SocketIO连接状态：已连接，SID: {self.current_socketio_sid}")
        # 检查rooms是否包含该SID
        try:
            if hasattr(self.socketio_instance, 'server'):
                # 改进错误处理: 检查rooms是否为字典而不是函数
                rooms_obj = self.socketio_instance.server.rooms
                if isinstance(rooms_obj, dict):
                    rooms = rooms_obj.get(self.current_socketio_sid, [])
                    logger.info(f"SocketIO服务器中SID {self.current_socketio_sid} 所在的房间: {rooms}")
                else:
                    logger.warning(f"SocketIO服务器rooms不是字典，无法检查房间: {type(rooms_obj)}")
        except Exception as e:
            logger.error(f"检查SocketIO房间时出错: {e}")
        
        # 即使发生错误，仍然返回连接状态
        return True

    def _load_or_generate_key_pair(self):
        """加载或生成RSA密钥对，并设置到RSAUtils和ChatClient实例中。"""
        private_key, public_key = self.rsa_util.load_key_pair(PRIVATE_KEY_FILE, PUBLIC_KEY_FILE)
        if private_key is None or public_key is None:
            logger.info("未找到密钥文件，正在生成新的RSA密钥对并保存...")
            private_key, public_key = self.rsa_util.generate_key_pair()
            self.rsa_util.save_key_pair(private_key, public_key, PRIVATE_KEY_FILE, PUBLIC_KEY_FILE)

        self.rsa_util.set_keys(private_key, public_key)
        self.my_public_key = public_key
        self.my_public_key_pem = self.rsa_util.get_public_key_pem(public_key)

    def _send_request(self, command, payload={}):
        """向中心服务器发送JSON请求。"""
        if not self.server_socket:
            logger.error("未连接到服务器。")
            return None

        request = {"command": command, "payload": payload}
        try:
            self.server_socket.sendall(json.dumps(request, ensure_ascii=False).encode('utf-8'))
            logger.debug(f"已发送请求: {command} {payload}")
            return True
        except socket.error as e:
            logger.error(f"发送请求到服务器失败: {e}")
            self.disconnect_server()
            return False

    def _receive_response(self):
        """从中心服务器接收JSON响应。"""
        if not self.server_socket:
            return None

        try:
            data = self.server_socket.recv(BUFFER_SIZE).decode('utf-8')
            if not data:
                logger.warning("服务器连接断开。")
                self.disconnect_server()
                return None
            response = json.loads(data)
            logger.debug(f"收到响应: {response}")
            return response
        except json.JSONDecodeError:
            logger.error(f"收到无效的JSON响应: {data}")
            return None
        except socket.error as e:
            logger.error(f"接收响应从服务器失败: {e}")
            self.disconnect_server()
            return None

    def connect_server(self):
        """连接到中心服务器。"""
        if self.server_socket:
            logger.info("已连接到服务器。")
            return True
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.connect((SERVER_HOST, SERVER_PORT))
            logger.info(f"成功连接到服务器 {SERVER_HOST}:{SERVER_PORT}")
            return True
        except socket.error as e:
            logger.error(f"连接服务器失败: {e}")
            self.server_socket = None
            return False

    def disconnect_server(self):
        """断开与中心服务器的连接，并清理所有P2P相关资源。"""
        if self.server_socket:
            try:
                self.server_socket.shutdown(socket.SHUT_RDWR)
                self.server_socket.close()
                logger.info("已断开与服务器的连接。")
            except socket.error as e:
                logger.warning(f"关闭服务器连接时出错: {e}")
            finally:
                self.server_socket = None
                # 移除重复的用户信息清理，由 logout 方法统一处理
                self.p2p_manager.stop_p2p_listener()
                self.p2p_manager.close_all_p2p_connections()

    def register(self, username, password):
        """
        用户注册功能。
        客户端将自己生成的公钥发送给服务器，服务器将其与新注册的用户名和哈希密码存储。
        """
        if not self.connect_server():
            return False

        payload = {"username": username, "password": password, "public_key": self.my_public_key_pem}
        if self._send_request("REGISTER", payload):
            response = self._receive_response()
            if response and response.get("status") == "success":
                logger.info(f"注册成功: {response.get('message')}")
                return True
            else:
                logger.error(f"注册失败: {response.get('message', '未知错误')}")
        return False

    def login(self, username, password):
        """用户登录功能。"""
        if self.logged_in_username:
            logger.warning(f"您已登录为 {self.logged_in_username}。请先登出。")
            return False

        if not self.connect_server():
            return False

        if not self.p2p_manager.start_p2p_listener():
            logger.error("P2P监听器未成功启动，无法登录。")
            return False

        # 确保p2p_listen_socket存在后再使用
        if self.p2p_manager.p2p_listen_socket:
            self.p2p_manager.p2p_listen_socket.settimeout(None)
            self.p2p_manager.p2p_actual_port = self.p2p_manager.p2p_listen_socket.getsockname()[1]
        else:
            logger.error("P2P监听socket未初始化，无法登录。")
            return False

        local_ip = '127.0.0.1'
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            logger.warning("无法确定外部可访问的本地IP，使用127.0.0.1。")

        self.p2p_manager.update_identity_info(username, self.my_public_key_pem)

        payload = {
            "username": username,
            "password": password,
            "p2p_ip": local_ip,
            "p2p_port": self.p2p_manager.p2p_actual_port
        }
        if self._send_request("LOGIN", payload):
            response = self._receive_response()
            if response and response.get("status") == "success":
                self.logged_in_username = response["data"]["username"]
                self.logged_in_user_id = response["data"]["user_id"]
                logger.info(f"登录成功: {self.logged_in_username}")
                self.get_online_friends()
                self.get_all_friends()
                self._notify_online_friends()
                return True
            else:
                logger.error(f"登录失败: {response.get('message', '未知错误')}")
        return False

    def _notify_online_friends(self):
        """向所有在线好友发送P2P上线通知。"""
        for friend in self.online_friends_info.values():
            try:
                payload = {"type": "online_notify", "username": self.logged_in_username}
                self.p2p_manager.send_p2p_raw_data(
                    friend["username"],
                    json.dumps(payload, ensure_ascii=False).encode('utf-8')
                )
            except Exception as e:
                logger.warning(f"向 {friend['username']} 发送上线通知失败: {e}")

    def logout(self):
        """用户登出功能。"""
        if not self.logged_in_username:
            logger.warning("您尚未登录。")
            return False

        try:
            # 尝试向服务器发送登出请求
            if self._send_request("LOGOUT"):
                response = self._receive_response()
                if response and response.get("status") == "success":
                    logger.info(f"登出成功: {response.get('message')}")
                else:
                    logger.warning(f"服务器登出响应异常: {response.get('message', '未知错误')}")
            else:
                logger.warning("无法向服务器发送登出请求，可能连接已断开")
        except Exception as e:
            logger.warning(f"发送登出请求时出错: {e}")

        # 统一清理所有本地资源
        return self._cleanup_local_resources()

    def _cleanup_local_resources(self):
        """统一清理本地资源的私有方法。"""
        try:
            # 清理用户信息
            self.logged_in_username = None
            self.logged_in_user_id = None
            
            # 清理好友信息缓存
            self.online_friends_info.clear()
            
            # 清理 SocketIO 相关
            self.current_socketio_sid = None
            
            # 断开服务器连接和P2P连接
            self.disconnect_server()
            
            logger.info("本地资源清理完成")
            return True
        except Exception as e:
            logger.error(f"清理本地资源时出错: {e}")
            return False

    def add_friend(self, friend_username):
        """添加好友功能。"""
        if not self.logged_in_username:
            logger.warning("请先登录。")
            return False
        payload = {"friend_username": friend_username}
        if self._send_request("ADD_FRIEND", payload):
            response = self._receive_response()
            if response and response.get("status") == "success":
                logger.info(f"添加好友成功: {response.get('message')}")
                # 更新当前用户的好友列表
                self.get_online_friends()
                self.get_all_friends()
                return True
            else:
                logger.error(f"添加好友失败: {response.get('message', '未知错误')}")
        return False

    def remove_friend(self, friend_username):
        """删除好友功能。"""
        if not self.logged_in_username:
            logger.warning("请先登录。")
            return False
        payload = {"friend_username": friend_username}
        if self._send_request("REMOVE_FRIEND", payload):
            response = self._receive_response()
            if response and response.get("status") == "success":
                logger.info(f"删除好友成功: {response.get('message')}")
                self.get_online_friends()
                return True
            else:
                logger.error(f"删除好友失败: {response.get('message', '未知错误')}")
        return False

    def get_online_friends(self):
        """从服务器获取在线好友列表，并更新本地缓存。"""
        if not self.logged_in_username:
            logger.warning("请先登录。")
            return False

        if self._send_request("GET_ONLINE_FRIENDS"):
            response = self._receive_response()
            if response and response.get("status") == "success":
                friends_list = response["data"]["friends"]
                self.online_friends_info.clear()
                for friend in friends_list:
                    # 确保字段名一致：ip_address 和 p2p_port
                    if 'IPAddress' in friend and 'ip_address' not in friend:
                        friend['ip_address'] = friend['IPAddress']
                    if 'P2PPort' in friend and 'p2p_port' not in friend:
                        friend['p2p_port'] = friend['P2PPort']
                    
                    # 自服务器数据库已修改，服务器现在直接提供public_key_pem字段
                    # 确保历史代码兼容性，如果有其他字段名也进行处理
                    if 'PublicKey' in friend and 'public_key_pem' not in friend:
                        friend['public_key_pem'] = friend['PublicKey']
                    
                    self.online_friends_info[friend["username"]] = friend
                    logger.info(f"friend: {friend}")
                    # logger.info(f"friend: {friend['public_key']}")
                logger.info(f"已更新在线好友列表。当前在线好友: {list(self.online_friends_info.keys())}")
                return True
            else:
                logger.error(f"获取在线好友失败: {response.get('message', '未知错误')}")
        return False

    def get_all_friends(self):
        """获取所有好友列表（无论在线或离线）。"""
        if not self.logged_in_username:
            logger.warning("请先登录。")
            return None

        if self._send_request("GET_ALL_FRIENDS"):
            response = self._receive_response()
            if response and response.get("status") == "success":
                friends_list = response["data"]["friends"]
                logger.info(f"已获取所有好友列表。共 {len(friends_list)} 位好友。")
                return friends_list
            else:
                logger.error(f"获取所有好友失败: {response.get('message', '未知错误')}")
        return None

    def get_public_key_from_server(self, username):
        """从服务器获取指定用户的公钥（如果不在在线好友列表里）。"""
        if not self.logged_in_username:
            logger.warning("请先登录。")
            return None

        if username in self.online_friends_info:
            return self.online_friends_info[username]["public_key_pem"]

        payload = {"username": username}
        if self._send_request("GET_PUBLIC_KEY", payload):
            response = self._receive_response()
            if response and response.get("status") == "success":
                logger.info(f"成功从服务器获取 {username} 的公钥。")
                return response["data"]["public_key_pem"]
            else:
                logger.error(f"从服务器获取 {username} 公钥失败: {response.get('message', '未知错误')}")
        return None

    def _handle_p2p_received_raw_data(self, peer_username, peer_public_key_pem, raw_data_bytes, sid=None):
        """
        P2PManager回调此函数，处理从P2P连接收到的原始（加密）数据。
        在此处进行解密操作，并将解密后的消息通过SocketIO推送到浏览器。
        支持处理完整JSON消息和大型二进制数据包。
        :param peer_username: 发送方的用户名。
        :param peer_public_key_pem: 发送方的公钥PEM格式字符串。
        :param raw_data_bytes: 从P2P连接收到的原始字节数据（加密的JSON）。
        :param sid: 接收到消息的Web客户端的SocketIO会话ID，用于精确推送。
        """
        try:
            # 尝试解析为JSON
            try:
                received_payload = json.loads(raw_data_bytes.decode('utf-8'))
                is_valid_json = True
            except json.JSONDecodeError:
                # 如果不是有效的JSON，可能是分块传输的大型二进制数据
                is_valid_json = False
                received_payload = None
                logger.warning(f"收到来自 {peer_username} 的数据不是有效的JSON格式，尝试按大型二进制数据处理")
            
            # 处理有效的JSON消息
            if is_valid_json and received_payload:
                message_type = received_payload.get("type", "chat_message")
                
                # 处理语音消息
                if message_type == "audio_message":
                    encrypted_key_b64 = received_payload.get("encrypted_key")
                    encrypted_audio_b64 = received_payload.get("encrypted_audio")
                    nonce_b64 = received_payload.get("nonce")
                    tag_b64 = received_payload.get("tag")

                    if not all([encrypted_key_b64, encrypted_audio_b64, nonce_b64, tag_b64]):
                        logger.warning(f"收到来自 {peer_username} 的不完整的语音消息。")
                        return
                    
                    # Base64解码回原始字节数据
                    encrypted_key = base64.b64decode(encrypted_key_b64)
                    encrypted_audio = base64.b64decode(encrypted_audio_b64)
                    nonce = base64.b64decode(nonce_b64)
                    tag = base64.b64decode(tag_b64)
                    
                    logger.debug(f"收到来自 {peer_username} 的加密语音消息，开始解密流程")
                    
                    # 1. 使用自己的RSA私钥解密出一次性对称密钥 (AES Key)
                    symmetric_key = self.rsa_util.decrypt_symmetric_key(encrypted_key)
                    if not symmetric_key:
                        logger.error(f"无法解密来自 {peer_username} 的语音消息的对称密钥。")
                        return
                    
                    # 2. 使用解密出的对称密钥解密语音数据
                    decrypted_audio_bytes = self.aes_util.decrypt_message(encrypted_audio, nonce, tag, symmetric_key)
                    if decrypted_audio_bytes is None:
                        logger.error(f"无法解密来自 {peer_username} 的语音消息，可能被篡改或密钥错误")
                        return
                    
                    # 3. 解码音频数据
                    audio_data_decoded = self.audio_util.decode_audio(decrypted_audio_bytes.decode('utf-8'))
                    if not audio_data_decoded:
                        logger.error(f"无法解码来自 {peer_username} 的语音消息数据")
                        return
                    
                    logger.info(f"成功接收并解密来自 {peer_username} 的语音消息")
                    
                    # 处理音频数据
                    self._process_audio_message(peer_username, audio_data_decoded, sid)
                    
                # 保留原有的处理逻辑
                elif message_type == "online_notify":
                    logger.info(f"收到来自 {peer_username} 的上线通知")
                    # 通知前端刷新聊天页面（只刷新在线好友）
                    if self.socketio_instance and sid:
                        self.socketio_instance.emit('refresh_online_friends', {}, room=sid)
                    return
                elif message_type == "chat_message":
                    encrypted_key_b64 = received_payload.get("encrypted_key")
                    encrypted_message_b64 = received_payload.get("encrypted_message")
                    nonce_b64 = received_payload.get("nonce")
                    tag_b64 = received_payload.get("tag")

                    if not all([encrypted_key_b64, encrypted_message_b64, nonce_b64, tag_b64]):
                        logger.warning(f"收到来自 {peer_username} 的不完整的加密P2P聊天消息。")
                        return

                    # Base64解码回原始字节数据
                    encrypted_key = base64.b64decode(encrypted_key_b64)
                    encrypted_message = base64.b64decode(encrypted_message_b64)
                    nonce = base64.b64decode(nonce_b64)
                    tag = base64.b64decode(tag_b64)
                    
                    logger.debug(f"收到来自 {peer_username} 的加密消息，开始解密流程")

                    # 1. 使用自己的RSA私钥解密出一次性对称密钥 (AES Key)
                    symmetric_key = self.rsa_util.decrypt_symmetric_key(encrypted_key)
                    if not symmetric_key:
                        logger.error(f"无法解密来自 {peer_username} 的聊天消息的对称密钥。")
                        return
                    logger.debug(f"已使用RSA私钥解密AES密钥")

                    # 2. 使用解密出的对称密钥解密实际消息
                    decrypted_message_bytes = self.aes_util.decrypt_message(encrypted_message, nonce, tag, symmetric_key)
                    if decrypted_message_bytes is None:
                        logger.error(f"✗✗✗ 无法解密来自 {peer_username} 的消息，可能被篡改或密钥错误")
                        return
                    
                    decrypted_message = decrypted_message_bytes.decode('utf-8')
                    logger.info(f"✓✓✓ 成功接收并解密来自 {peer_username} 的消息: \"{decrypted_message}\"")

                    # 使用当前SocketIO SID，如果没有提供
                    if not sid:
                        sid = self.current_socketio_sid
                        logger.info(f"使用当前客户端SID: {sid} (未提供SID)")

                    if sid:
                        # 先发送解密状态
                        self.socketio_instance.emit('message_status',
                                                   {'status': 'decrypting', 'message': ''},
                                                   room=sid)
                        
                        # 短暂延迟后显示解密后的消息
                        time.sleep(0.2)  # 模拟解密过程，实际上已经解密完成
                        
                        # 确保当前用户ID和用户名正确配置
                        user_id = str(self.logged_in_user_id) if self.logged_in_user_id else None
                        username = self.logged_in_username
                        logger.info(f"当前用户信息: ID={user_id}, 用户名={username}")
                        
                        # 发送解密后的消息，确保包含正确的发送者和接收者信息
                        logger.info(f"准备向SID: {sid} 发送来自 {peer_username} 的消息: \"{decrypted_message}\"")
                        self.socketio_instance.emit('receive_message',
                                                    {'sender': peer_username, 
                                                     'recipient': user_id, 
                                                     'message': decrypted_message},
                                                    room=sid)
                        logger.info(f"已完成向SID: {sid} 发送来自 {peer_username} 的消息")
                        
                        # 发送解密完成状态
                        self.socketio_instance.emit('message_status',
                                                   {'status': 'decrypted', 'message': ''},
                                                   room=sid)
                        
                        logger.info(f"UI通知: 接收到 {peer_username} 的消息并显示在用户界面，使用SID: {sid}")
                    else:
                        logger.warning(f"没有可用的SocketIO SID，聊天消息无法推送到浏览器。当前sid: {sid}")
                        # 广播消息到所有连接，尝试确保消息能被接收
                        try:
                            logger.info(f"尝试广播消息给所有连接")
                            
                            # 确保当前用户ID和用户名正确配置
                            user_id = str(self.logged_in_user_id) if self.logged_in_user_id else None
                            logger.info(f"广播消息时当前用户ID={user_id}")
                            
                            self.socketio_instance.emit('receive_message',
                                                        {'sender': peer_username, 
                                                         'recipient': user_id, 
                                                         'message': decrypted_message},
                                                        broadcast=True)
                        except Exception as e:
                            logger.error(f"广播消息失败: {e}")
                elif message_type == "steg_image":
                    # 提取隐写图片相关的数据
                    encrypted_image_data_b64 = received_payload.get("encrypted_image_data")
                    image_nonce_b64 = received_payload.get("image_nonce_b64")  # <--- 新增：图片自己的Nonce
                    image_tag_b64 = received_payload.get("image_tag_b64")  # <--- 新增：图片自己的Tag

                    # 提取隐藏消息的加密部分
                    hidden_message_crypto = received_payload.get("hidden_message_crypto")

                    if not all([encrypted_image_data_b64, image_nonce_b64, image_tag_b64, hidden_message_crypto]):
                        logger.warning(f"收到来自 {peer_username} 的不完整的隐写图片消息。")
                        return

                    # Base64解码图片数据自己的加密参数
                    encrypted_image_data = base64.b64decode(encrypted_image_data_b64)
                    image_nonce = base64.b64decode(image_nonce_b64)  # <--- 使用图片自己的Nonce
                    image_tag = base64.b64decode(image_tag_b64)  # <--- 使用图片自己的Tag

                    # Base64解码隐藏消息的加密参数
                    encrypted_key_for_hidden_msg = base64.b64decode(hidden_message_crypto.get("encrypted_key_b64", ""))
                    encrypted_hidden_msg = base64.b64decode(hidden_message_crypto.get("encrypted_hidden_msg_b64", ""))
                    nonce_hidden_msg = base64.b64decode(hidden_message_crypto.get("nonce_b64", ""))
                    tag_hidden_msg = base64.b64decode(hidden_message_crypto.get("tag_b64", ""))

                    # 1. 解密隐藏消息的对称密钥
                    symmetric_key_for_hidden = self.rsa_util.decrypt_symmetric_key(encrypted_key_for_hidden_msg)
                    if not symmetric_key_for_hidden:
                        logger.error(f"无法解密来自 {peer_username} 的隐写图片中隐藏消息的对称密钥。")
                        return

                    # 2. 解密隐藏消息
                    decrypted_hidden_message_bytes = self.aes_util.decrypt_message(
                        encrypted_hidden_msg, nonce_hidden_msg, tag_hidden_msg, symmetric_key_for_hidden
                    )
                    if decrypted_hidden_message_bytes is None:
                        logger.error(f"无法解密来自 {peer_username} 的隐写图片中的隐藏消息。")
                        return

                    decrypted_hidden_message = decrypted_hidden_message_bytes.decode('utf-8')
                    logger.info(f"隐写消息解密成功！[P2P隐藏消息 from {peer_username}]: {decrypted_hidden_message}")

                    # 3. 解密图片数据
                    decrypted_image_data_bytes = self.aes_util.decrypt_message(
                        encrypted_image_data, image_nonce, image_tag, symmetric_key_for_hidden  # <--- 使用图片自己的nonce和tag
                    )
                    if decrypted_image_data_bytes is None:
                        logger.error(f"无法解密来自 {peer_username} 的隐写图片数据。")
                        return

                    # 处理图片数据和隐藏消息
                    self._process_steg_image(peer_username, decrypted_image_data_bytes, decrypted_hidden_message, sid)
                
                # 其他类型的消息
                else:
                    logger.warning(f"收到来自 {peer_username} 的未知消息类型: {message_type}")
            
            # 处理大型二进制数据
            elif not is_valid_json and len(raw_data_bytes) > 1000:  # 如果数据量大于1KB，可能是分块传输的数据
                logger.info(f"收到来自 {peer_username} 的大型二进制数据 ({len(raw_data_bytes)} 字节)，尝试作为隐写图片消息处理")
                
                # 尝试从数据中提取有效的AES加密参数
                # 这里我们假设数据的前256字节是RSA加密的AES密钥
                try:
                    # 这是一个简化假设，根据实际情况调整
                    encrypted_key = raw_data_bytes[:256]  # 假设RSA加密的AES密钥是前256字节
                    
                    # 尝试解密AES密钥
                    symmetric_key = self.rsa_util.decrypt_symmetric_key(encrypted_key)
                    if not symmetric_key:
                        logger.error(f"无法从大型二进制数据中解密对称密钥，放弃处理")
                        return
                    
                    # 尝试从剩余数据中提取nonce、tag和加密内容
                    remaining_data = raw_data_bytes[256:]
                    if len(remaining_data) < 32:  # 至少需要16字节的nonce和16字节的tag
                        logger.error(f"大型二进制数据格式无效，数据长度不足")
                        return
                    
                    # 提取nonce和tag(各16字节)
                    nonce = remaining_data[:16]
                    tag = remaining_data[16:32]
                    encrypted_data = remaining_data[32:]
                    
                    # 尝试解密数据
                    decrypted_data = self.aes_util.decrypt_message(encrypted_data, nonce, tag, symmetric_key)
                    if decrypted_data is None:
                        logger.error(f"无法解密大型二进制数据，可能格式不符")
                        return
                    
                    # 假设解密后的数据是图片数据，尝试提取隐藏消息
                    hidden_message = self.steg_util.extract_text(decrypted_data)
                    if hidden_message:
                        logger.info(f"成功从大型二进制数据中提取隐藏消息: {hidden_message}")
                        # 处理图片数据和隐藏消息
                        self._process_steg_image(peer_username, decrypted_data, hidden_message, sid)
                    else:
                        logger.warning(f"大型二进制数据解密成功，但未能提取到隐藏消息")
                        # 仍然尝试作为图片处理
                        self._process_steg_image(peer_username, decrypted_data, "无法提取隐藏消息", sid)
                
                except Exception as e:
                    logger.error(f"处理大型二进制数据时出错: {e}", exc_info=True)
            
            else:
                logger.warning(f"收到来自 {peer_username} 的无法处理的数据格式")

        except json.JSONDecodeError:
            logger.error(f"收到来自 {peer_username} 的无效P2P消息JSON格式。")
        except Exception as ex:
            logger.error(f"处理或解密来自 {peer_username} 的P2P消息时出错: {ex}", exc_info=True)
    
    def _process_steg_image(self, peer_username, image_data_bytes, hidden_message, sid=None):
        """
        处理隐写图片数据和隐藏消息，将其显示在用户界面上。
        :param peer_username: 发送方用户名
        :param image_data_bytes: 解密后的图片字节数据
        :param hidden_message: 解密后的隐藏消息文本
        :param sid: SocketIO会话ID
        """
        try:
            # 保存图片到临时文件
            temp_image_filename = f"temp_steg_image_{os.urandom(4).hex()}.png"
            # Flask 的 static 目录通常位于应用程序根目录下
            temp_image_path_abs = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static',
                                               temp_image_filename)

            with open(temp_image_path_abs, "wb") as f:
                f.write(image_data_bytes)
            logger.info(f"隐写图片已保存到 {temp_image_path_abs}")

            # 尝试再次提取文本，验证隐写功能
            extracted_text = self.steg_util.extract_text(image_data_bytes) or "无法提取文本"

            # 使用当前SocketIO SID，如果没有提供
            if not sid:
                sid = self.current_socketio_sid
                logger.info(f"使用当前客户端SID: {sid} (未提供SID)")
                
            # 推送消息到浏览器
            if sid:
                # 导入Flask应用实例并创建应用上下文
                from flask import current_app
                
                # 生成图片URL
                image_url_for_web = f"/static/{temp_image_filename}"
                logger.info(f"生成图片URL: {image_url_for_web}")
                
                # 发送普通消息通知
                self.socketio_instance.emit('receive_message',
                                           {'sender': peer_username,
                                            'recipient': str(self.logged_in_user_id),
                                            'message': image_url_for_web,
                                            'type': 'steg_image',
                                            'hiddenMessage': hidden_message},
                                           room=sid)
                
                logger.info(f"通过SocketIO向SID {sid} 推送隐写图片消息。")
            else:
                logger.warning(f"没有可用的SocketIO SID，隐写图片消息无法推送到浏览器。")
                # 广播消息到所有连接，尝试确保消息能被接收
                try:
                    logger.info(f"尝试广播隐写图片消息给所有连接")
                    
                    # 生成图片URL
                    image_url_for_web = f"/static/{temp_image_filename}"
                    
                    self.socketio_instance.emit('receive_message',
                                              {'sender': peer_username,
                                               'recipient': str(self.logged_in_user_id),
                                               'message': image_url_for_web,
                                               'type': 'steg_image',
                                               'hiddenMessage': hidden_message},
                                              broadcast=True)
                except Exception as e:
                    logger.error(f"广播隐写图片消息失败: {e}")
        except Exception as e:
            logger.error(f"处理隐写图片时出错: {e}", exc_info=True)

    def send_p2p_message(self, recipient_username, message):
        """
        向指定好友发送加密的P2P文本消息。
        此函数协调 P2P 连接的建立（如果尚未建立）和消息的加密发送。
        使用接收方的公钥加密AES密钥，然后用AES加密消息内容。
        """
        if not self.logged_in_username:
            logger.warning("请先登录。")
            return False

        friend_info = self.online_friends_info.get(recipient_username)

        if not friend_info:  # 只有在线好友才能进行P2P直连聊天
            logger.error(f"好友 '{recipient_username}' 不在线或不在您的好友列表中，无法进行P2P聊天。")
            return False

        # 处理不同的字段名格式
        friend_ip = friend_info.get("ip_address") or friend_info.get("IPAddress") or friend_info.get("ip")
        friend_port = friend_info.get("p2p_port") or friend_info.get("P2PPort") or friend_info.get("port")
        # 使用public_key_pem字段
        friend_public_key_pem = friend_info.get("public_key_pem")
        
        # 记录调试信息
        logger.debug(f"好友 '{recipient_username}' 的连接信息:")
        logger.debug(f"IP地址: {friend_ip}")
        logger.debug(f"端口: {friend_port}")
        logger.debug(f"公钥: {'存在' if friend_public_key_pem else '不存在'}")
        if not friend_ip or not friend_port or not friend_public_key_pem:
            logger.error(f"好友 '{recipient_username}' 的连接信息不完整，无法进行P2P聊天。")
            # 记录详细的缺失信息以便调试
            logger.debug(f"连接信息详情: IP={friend_ip}, 端口={friend_port}, 公钥={'有' if friend_public_key_pem else '无'}, 原始信息={friend_info}")
            return False

        # 确保 P2P 连接存在并活跃。如果不存在，P2PManager 会尝试建立。
        conn_socket = self.p2p_manager.active_p2p_connections.get(recipient_username)
        if not conn_socket:
            logger.info(f"正在尝试与 {recipient_username} ({friend_ip}:{friend_port}) 建立P2P连接...")
            # 调用 P2PManager 建立出站连接并完成握手
            conn_socket = self.p2p_manager.connect_p2p_peer(
                recipient_username, friend_ip, friend_port,
                self.logged_in_username, self.my_public_key_pem
            )
            if not conn_socket:
                logger.error(f"无法与 {recipient_username} 建立P2P连接，消息发送失败。")
                return False
            time.sleep(0.1)  # 给线程启动和握手一点时间，避免立即发送数据失败

        try:
            # 1. 生成一次性对称密钥 (AES Key)
            aes_key = os.urandom(32)  # AES-256 需要32字节的密钥
            logger.debug(f"生成AES密钥用于与 {recipient_username} 的通信")

            # 2. 使用接收方的RSA公钥加密这个对称密钥
            encrypted_aes_key = self.rsa_util.encrypt_symmetric_key(friend_public_key_pem, aes_key)
            if encrypted_aes_key is None:
                logger.error("无法加密对称密钥，消息发送失败。")
                return False
            logger.debug(f"已使用 {recipient_username} 的公钥加密AES密钥")

            # 3. 使用对称密钥加密实际消息
            encrypted_message, nonce, tag = self.aes_util.encrypt_message(message.encode('utf-8'), aes_key)
            if encrypted_message is None:
                logger.error("无法加密消息，消息发送失败。")
                return False
            logger.info(f"===> 消息已使用AES加密，准备发送给 {recipient_username}")

            # 将所有加密后的二进制数据（密文、密钥、Nonce、Tag）转换为Base64编码，
            # 因为JSON协议通常传输文本，二进制数据需要先编码。
            encrypted_payload = {
                "type": "chat_message",  # 明确消息类型
                "encrypted_key": base64.b64encode(encrypted_aes_key).decode('utf-8'),
                "encrypted_message": base64.b64encode(encrypted_message).decode('utf-8'),
                "nonce": base64.b64encode(nonce).decode('utf-8'),
                "tag": base64.b64encode(tag).decode('utf-8')
            }

            # 调用 P2PManager 发送加密后的JSON数据（原始字节形式）
            if self.p2p_manager.send_p2p_raw_data(recipient_username,
                                                  json.dumps(encrypted_payload, ensure_ascii=False).encode('utf-8')):
                logger.info(f"✓✓✓ 成功发送加密消息给 {recipient_username}")
                return True
            else:
                logger.error(f"✗✗✗ 发送加密消息给 {recipient_username} 失败")
                return False

        except Exception as e:
            logger.error(f"加密或发送P2P聊天消息给 {recipient_username} 时出错: {e}", exc_info=True)
            return False

    def send_steg_image_message(self, recipient_username, image_file_bytes, hidden_message_text):
        """
        向指定好友发送包含隐藏消息的加密图片。
        :param recipient_username: 接收方用户名。
        :param image_file_bytes: 原始图片文件的字节数据。
        :param hidden_message_text: 要隐藏在图片中的文本。
        :return: True发送成功，False失败。
        """
        if not self.logged_in_username:
            logger.warning("请先登录。")
            return False

        # 获取好友信息，添加详细日志
        friend_info = self.online_friends_info.get(recipient_username)
        logger.info(f"发送隐写图片给 {recipient_username}, 在线好友信息: {friend_info}")
        
        # 如果好友信息不存在，尝试刷新在线好友列表
        if not friend_info:
            logger.info(f"好友 '{recipient_username}' 不在线，尝试刷新在线好友列表...")
            self.get_online_friends()
            friend_info = self.online_friends_info.get(recipient_username)
            logger.info(f"刷新后的好友信息: {friend_info}")
            
            if not friend_info:
                logger.error(f"好友 '{recipient_username}' 不在线，无法发送隐写图片。")
                return False

        # 处理不同的字段名格式，增加更多可能的字段名
        friend_ip = (friend_info.get("ip_address") or 
                    friend_info.get("IPAddress") or 
                    friend_info.get("ip") or 
                    friend_info.get("IP"))
                    
        friend_port = (friend_info.get("p2p_port") or 
                      friend_info.get("P2PPort") or 
                      friend_info.get("port") or 
                      friend_info.get("Port"))
                      
        # 使用public_key_pem字段，增加更多可能的字段名
        friend_public_key_pem = (friend_info.get("public_key_pem") or 
                                friend_info.get("publicKeyPem") or 
                                friend_info.get("public_key"))
        
        # 记录详细调试信息
        logger.info(f"好友 '{recipient_username}' 的连接信息:")
        logger.info(f"IP地址: {friend_ip}")
        logger.info(f"端口: {friend_port}")
        logger.info(f"公钥: {'存在' if friend_public_key_pem else '不存在'}")
        logger.info(f"原始好友信息: {friend_info}")
        
        if not friend_ip or not friend_port or not friend_public_key_pem:
            logger.error(f"好友 '{recipient_username}' 的连接信息不完整，无法发送隐写图片。")
            # 记录详细的缺失信息以便调试
            logger.error(f"连接信息详情: IP={friend_ip}, 端口={friend_port}, 公钥={'有' if friend_public_key_pem else '无'}")
            return False

        try:
            # 1. 将文本嵌入图片LSB中
            logger.info(f"开始将隐藏消息嵌入图片，图片大小: {len(image_file_bytes)} 字节")
            steg_image_bytes = self.steg_util.embed_text(image_file_bytes, hidden_message_text)
            if steg_image_bytes is None:
                logger.error("嵌入文本到图片失败。")
                return False
            logger.info(f"隐写成功，处理后图片大小: {len(steg_image_bytes)} 字节")

            # 2. 为隐藏消息本身生成一个一次性AES密钥，并用RSA加密这个密钥
            aes_key_for_hidden_msg = os.urandom(32)
            encrypted_aes_key_for_hidden_msg = self.rsa_util.encrypt_symmetric_key(friend_public_key_pem,
                                                                                aes_key_for_hidden_msg)
            if encrypted_aes_key_for_hidden_msg is None:
                logger.error("无法加密隐藏消息的对称密钥。")
                return False
            logger.info("成功加密隐藏消息的对称密钥")

            # 3. 使用对称密钥加密隐藏消息（这是为了确保隐藏消息在图片被解密之前也保持机密性）
            encrypted_hidden_msg, nonce_hidden_msg, tag_hidden_msg = self.aes_util.encrypt_message(
                hidden_message_text.encode('utf-8'), aes_key_for_hidden_msg
            )
            if encrypted_hidden_msg is None:
                logger.error("无法加密隐藏消息。")
                return False
            logger.info("成功加密隐藏消息")

            # 4. 使用另一个一次性AES密钥加密整个隐写图片数据
            # 修正：图片数据应该有自己独立的nonce和tag
            encrypted_image_data, image_nonce, image_tag = self.aes_util.encrypt_message(
                steg_image_bytes, aes_key_for_hidden_msg  # 这里依然复用aes_key_for_hidden_msg来加密图片，但nonce/tag独立
            )
            if encrypted_image_data is None:
                logger.error("无法加密隐写图片数据。")
                return False
            logger.info(f"成功加密隐写图片数据，加密后大小: {len(encrypted_image_data)} 字节")

            # 确保 P2P 连接存在
            logger.info(f"检查与 {recipient_username} 的P2P连接")
            conn_socket = self.p2p_manager.active_p2p_connections.get(recipient_username)
            if not conn_socket:
                logger.info(f"尝试建立与 {recipient_username} 的P2P连接")
                conn_socket = self.p2p_manager.connect_p2p_peer(
                    recipient_username, friend_ip, friend_port,
                    self.logged_in_username, self.my_public_key_pem
                )
                if not conn_socket:
                    logger.error(f"无法与 {recipient_username} 建立P2P连接，隐写图片发送失败。")
                    return False
                logger.info(f"成功建立与 {recipient_username} 的P2P连接")
                time.sleep(0.1)  # 给连接一点稳定的时间

            try:
                # 封装所有加密后的数据为JSON，并Base64编码
                encrypted_payload = {
                    "type": "steg_image",  # 明确消息类型为隐写图片
                    "encrypted_image_data": base64.b64encode(encrypted_image_data).decode('utf-8'),
                    "image_nonce_b64": base64.b64encode(image_nonce).decode('utf-8'),  # <-- 修正：图片自己的Nonce
                    "image_tag_b64": base64.b64encode(image_tag).decode('utf-8'),  # <-- 修正：图片自己的Tag
                    "hidden_message_crypto": {  # 隐藏消息的加密部分
                        "encrypted_key_b64": base64.b64encode(encrypted_aes_key_for_hidden_msg).decode('utf-8'),
                        "encrypted_hidden_msg_b64": base64.b64encode(encrypted_hidden_msg).decode('utf-8'),
                        "nonce_b64": base64.b64encode(nonce_hidden_msg).decode('utf-8'),
                        "tag_b64": base64.b64encode(tag_hidden_msg).decode('utf-8'),
                    }
                }

                # 转换为JSON字符串并编码为字节
                json_data = json.dumps(encrypted_payload, ensure_ascii=False).encode('utf-8')
                logger.info(f"准备发送隐写图片消息，JSON数据大小: {len(json_data)} 字节")
                
                # 发送数据
                if self.p2p_manager.send_p2p_raw_data(recipient_username, json_data):
                    logger.info(f"已成功发送加密隐写图片消息给 {recipient_username}.")
                    return True
                else:
                    logger.error(f"通过P2PManager发送隐写图片消息给 {recipient_username} 失败。")
                    return False

            except Exception as e:
                logger.error(f"发送隐写图片消息给 {recipient_username} 时出错: {e}", exc_info=True)
                return False
                
        except Exception as e:
            logger.error(f"处理隐写图片消息给 {recipient_username} 时出错: {e}", exc_info=True)
            return False

    def send_audio_message(self, recipient_username, audio_data_bytes):
        """
        向指定好友发送加密的语音消息。
        :param recipient_username: 接收方用户名。
        :param audio_data_bytes: 原始音频文件的字节数据。
        :return: True发送成功，False失败。
        """
        if not self.logged_in_username:
            logger.warning("请先登录。")
            return False

        # 获取好友信息
        friend_info = self.online_friends_info.get(recipient_username)
        logger.info(f"发送语音消息给 {recipient_username}, 在线好友信息: {friend_info}")
        
        # 如果好友信息不存在，尝试刷新在线好友列表
        if not friend_info:
            logger.info(f"好友 '{recipient_username}' 不在线，尝试刷新在线好友列表...")
            self.get_online_friends()
            friend_info = self.online_friends_info.get(recipient_username)
            logger.info(f"刷新后的好友信息: {friend_info}")
            
            if not friend_info:
                logger.error(f"好友 '{recipient_username}' 不在线，无法发送语音消息。")
                return False

        # 处理不同的字段名格式
        friend_ip = (friend_info.get("ip_address") or 
                    friend_info.get("IPAddress") or 
                    friend_info.get("ip") or 
                    friend_info.get("IP"))
                    
        friend_port = (friend_info.get("p2p_port") or 
                      friend_info.get("P2PPort") or 
                      friend_info.get("port") or 
                      friend_info.get("Port"))
                      
        friend_public_key_pem = (friend_info.get("public_key_pem") or 
                                friend_info.get("publicKeyPem") or 
                                friend_info.get("public_key"))
        
        # 记录详细调试信息
        logger.info(f"好友 '{recipient_username}' 的连接信息:")
        logger.info(f"IP地址: {friend_ip}")
        logger.info(f"端口: {friend_port}")
        logger.info(f"公钥: {'存在' if friend_public_key_pem else '不存在'}")
        
        if not friend_ip or not friend_port or not friend_public_key_pem:
            logger.error(f"好友 '{recipient_username}' 的连接信息不完整，无法发送语音消息。")
            return False

        # 确保 P2P 连接存在
        logger.info(f"检查与 {recipient_username} 的P2P连接")
        conn_socket = self.p2p_manager.active_p2p_connections.get(recipient_username)
        if not conn_socket:
            logger.info(f"尝试建立与 {recipient_username} 的P2P连接")
            conn_socket = self.p2p_manager.connect_p2p_peer(
                recipient_username, friend_ip, friend_port,
                self.logged_in_username, self.my_public_key_pem
            )
            if not conn_socket:
                logger.error(f"无法与 {recipient_username} 建立P2P连接，语音消息发送失败。")
                return False
            logger.info(f"成功建立与 {recipient_username} 的P2P连接")
            time.sleep(0.1)  # 给连接一点稳定的时间

        try:
            # 编码音频数据
            encoded_audio = self.audio_util.encode_audio(audio_data_bytes)
            if encoded_audio is None:
                logger.error("编码音频数据失败。")
                return False
            
            # 1. 生成一次性对称密钥 (AES Key)
            aes_key = os.urandom(32)  # AES-256 需要32字节的密钥
            logger.debug(f"生成AES密钥用于与 {recipient_username} 的语音通信")

            # 2. 使用接收方的RSA公钥加密这个对称密钥
            encrypted_aes_key = self.rsa_util.encrypt_symmetric_key(friend_public_key_pem, aes_key)
            if encrypted_aes_key is None:
                logger.error("无法加密对称密钥，语音消息发送失败。")
                return False
            
            # 3. 使用对称密钥加密音频数据
            encrypted_audio_data = self.aes_util.encrypt_message(encoded_audio.encode('utf-8'), aes_key)
            if encrypted_audio_data is None:
                logger.error("无法加密音频数据。")
                return False
                
            encrypted_message, nonce, tag = encrypted_audio_data
            logger.info(f"音频数据已加密，准备发送给 {recipient_username}")

            # 封装所有加密后的数据为JSON，并Base64编码
            encrypted_payload = {
                "type": "audio_message",  # 明确消息类型为语音消息
                "encrypted_key": base64.b64encode(encrypted_aes_key).decode('utf-8'),
                "encrypted_audio": base64.b64encode(encrypted_message).decode('utf-8'),
                "nonce": base64.b64encode(nonce).decode('utf-8'),
                "tag": base64.b64encode(tag).decode('utf-8')
            }

            # 转换为JSON字符串并编码为字节
            json_data = json.dumps(encrypted_payload, ensure_ascii=False).encode('utf-8')
            logger.info(f"准备发送语音消息，JSON数据大小: {len(json_data)} 字节")
            
            # 发送数据
            if self.p2p_manager.send_p2p_raw_data(recipient_username, json_data):
                logger.info(f"已成功发送加密语音消息给 {recipient_username}.")
                return True
            else:
                logger.error(f"通过P2PManager发送语音消息给 {recipient_username} 失败。")
                return False
                
        except Exception as e:
            logger.error(f"处理发送语音消息给 {recipient_username} 时出错: {e}", exc_info=True)
            return False
            
    def _process_audio_message(self, peer_username, audio_data_bytes, sid=None):
        """
        处理接收到的语音消息，将其保存并通过SocketIO发送到前端
        :param peer_username: 发送方用户名
        :param audio_data_bytes: 解码后的音频字节数据
        :param sid: SocketIO会话ID
        """
        try:
            # 生成持久化音频文件名，使用发送者_接收者_时间戳格式
            timestamp = int(time.time())
            receiver_id = str(self.logged_in_user_id).replace(" ", "_")
            sender_clean = peer_username.replace(" ", "_")
            temp_audio_filename = f"audio_recv_{sender_clean}_{receiver_id}_{timestamp}.wav"
            temp_audio_path_abs = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', temp_audio_filename)

            # 写入临时文件
            with open(temp_audio_path_abs, "wb") as f:
                f.write(audio_data_bytes)
            logger.info(f"语音已保存到 {temp_audio_path_abs}")

            # 使用当前SocketIO SID，如果没有提供
            if not sid:
                sid = self.current_socketio_sid
                logger.info(f"使用当前客户端SID: {sid} (未提供SID)")
                
            # 推送消息到浏览器
            if sid:
                # 生成音频URL
                audio_url = f"/static/{temp_audio_filename}"
                logger.info(f"生成音频URL: {audio_url}")
                
                # 发送消息通知
                self.socketio_instance.emit('receive_message',
                                           {'sender': peer_username,
                                            'recipient': str(self.logged_in_user_id),
                                            'message': audio_url,
                                            'type': 'audio_message'},
                                           room=sid)
                
                logger.info(f"通过SocketIO向SID {sid} 推送语音消息。")
            else:
                logger.warning(f"没有可用的SocketIO SID，语音消息无法推送到浏览器。")
                # 广播消息到所有连接，尝试确保消息能被接收
                try:
                    logger.info(f"尝试广播语音消息给所有连接")
                    
                    # 生成音频URL
                    audio_url = f"/static/{temp_audio_filename}"
                    
                    self.socketio_instance.emit('receive_message',
                                              {'sender': peer_username,
                                               'recipient': str(self.logged_in_user_id),
                                               'message': audio_url,
                                               'type': 'audio_message'},
                                              broadcast=True)
                except Exception as e:
                    logger.error(f"广播语音消息失败: {e}")
        except Exception as e:
            logger.error(f"处理语音消息时出错: {e}", exc_info=True)