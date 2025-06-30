import socket
import threading
import json
import os
import time
import base64  # 用于 Base64 编码解码

from config import SERVER_HOST, SERVER_PORT, P2P_LISTEN_HOST, P2P_LISTEN_PORT, BUFFER_SIZE, PRIVATE_KEY_FILE, \
    PUBLIC_KEY_FILE
from utils.RSA import RSAUtils  # 导入 RSA 工具类
from utils.AES import AESUtils  # 导入 AES 工具类
from p2p_manager import P2PManager  # 导入P2P管理器

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
        # RSAUtils 实例将持有当前用户的 RSA 私钥和公钥
        self.rsa_util = RSAUtils()
        # 初始化 AESUtils 实例，负责所有 AES 对称加密相关操作
        self.aes_util = AESUtils()

        self._load_or_generate_key_pair()  # 在客户端启动时加载或生成密钥对

        # 初始化 P2PManager 实例，负责所有P2P连接的建立、监听和原始数据收发。
        # _handle_p2p_received_raw_data 是一个回调函数，当 P2PManager 收到原始数据时会调用它，
        # 并由 ChatClient 负责解密和处理。
        self.p2p_manager = P2PManager(
            p2p_listen_host=P2P_LISTEN_HOST,
            p2p_listen_port=P2P_LISTEN_PORT,
            buffer_size=BUFFER_SIZE,
            socketio_instance=self.socketio_instance,  # 传递 SocketIO 实例给 P2PManager
            sid_getter_callback=self._get_current_socketio_sid,  # 传递获取 SID 的回调
            decrypt_and_process_callback=self._handle_p2p_received_raw_data,  # 收到加密数据后的解密处理回调
            # 初始身份信息，在登录成功后会更新 P2PManager 中的用户名
            identity_info={"username": "初始化用户", "public_key_pem": self.my_public_key_pem}
        )

        # 存储在线好友的信息 {username: {user_id, ip, port, public_key_pem}}
        # 这里的 public_key_pem 是从服务器获取的好友的公钥，用于加密发给该好友的消息。
        self.online_friends_info = {}

    def _get_current_socketio_sid(self):
        """回调函数，用于 P2PManager 获取当前活跃的 SocketIO SID。"""
        return self.current_socketio_sid

    def _load_or_generate_key_pair(self):
        """
        加载或生成RSA密钥对。
        这个方法在客户端启动时被调用，确保每个客户端都有自己的密钥对。
        公钥的PEM格式字符串 (self.my_public_key_pem) 会在注册和登录时发送给服务器，
        作为用户身份的一部分被服务器数据库存储，从而与用户ID关联。
        """
        # 尝试从文件加载现有密钥
        private_key, public_key = self.rsa_util.load_key_pair(PRIVATE_KEY_FILE, PUBLIC_KEY_FILE)
        if private_key is None or public_key is None:
            logger.info("未找到密钥文件，正在生成新的RSA密钥对并保存...")
            private_key, public_key = self.rsa_util.generate_key_pair()  # 生成新密钥
            self.rsa_util.save_key_pair(private_key, public_key, PRIVATE_KEY_FILE, PUBLIC_KEY_FILE)  # 保存新密钥

        # 将密钥对象设置到 RSAUtils 实例，确保它能进行后续的加解密操作
        self.rsa_util.set_keys(private_key, public_key)
        # 同时在 ChatClient 实例中保存公钥对象和PEM格式字符串，方便在通信中使用
        self.my_public_key = public_key
        self.my_public_key_pem = self.rsa_util.get_public_key_pem(public_key)

    def _send_request(self, command, payload={}):
        """向中心服务器发送JSON请求。"""
        if not self.server_socket:
            logger.error("未连接到服务器。")
            return None

        request = {"command": command, "payload": payload}
        try:
            # 将JSON请求（Python字典）转换为UTF-8编码的字节串并发送
            self.server_socket.sendall(json.dumps(request, ensure_ascii=False).encode('utf-8'))
            logger.debug(f"已发送请求: {command} {payload}")
            return True
        except socket.error as e:
            logger.error(f"发送请求到服务器失败: {e}")
            self.disconnect_server()  # 发送失败，认为服务器连接有问题，断开并清理
            return False

    def _receive_response(self):
        """从中心服务器接收JSON响应。"""
        if not self.server_socket:
            return None

        try:
            # 接收字节数据并解码为UTF-8字符串
            data = self.server_socket.recv(BUFFER_SIZE).decode('utf-8')
            if not data:  # 如果收到空数据，表示服务器连接已断开
                logger.warning("服务器连接断开。")
                self.disconnect_server()
                return None
            response = json.loads(data)  # 将JSON字符串解析为Python字典
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
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 创建TCP socket
            self.server_socket.connect((SERVER_HOST, SERVER_PORT))  # 连接到服务器地址和端口
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
                self.server_socket.shutdown(socket.SHUT_RDWR)  # 关闭socket的读写
                self.server_socket.close()  # 关闭socket
                logger.info("已断开与服务器的连接。")
            except socket.error as e:
                logger.warning(f"关闭服务器连接时出错: {e}")
            finally:
                self.server_socket = None
                self.logged_in_user_id = None
                self.logged_in_username = None
                self.p2p_manager.stop_p2p_listener()  # 停止P2P监听器线程
                self.p2p_manager.close_all_p2p_connections()  # 关闭所有活跃的P2P连接

    def register(self, username, password):
        """
        用户注册功能。
        在此过程中，客户端将自己生成的公钥发送给服务器，
        服务器将此公钥与新注册的用户名和哈希密码一起存储到数据库中。
        这样，用户的公钥就与他们的用户ID/用户名建立了关联。
        """
        if not self.connect_server():  # 确保已连接到服务器
            return False

        # 将用户的公钥（PEM格式字符串）包含在注册请求的 payload 中发送给服务器。
        # 服务器会负责将其存储到数据库，与此用户名关联。
        payload = {"username": username, "password": password, "public_key": self.my_public_key_pem}
        if self._send_request("REGISTER", payload):  # 发送注册请求
            response = self._receive_response()  # 接收服务器响应
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

        if not self.connect_server():  # 确保已连接到服务器
            return False

        # 启动P2P监听器，客户端需要监听端口才能接收P2P消息
        if not self.p2p_manager.start_p2p_listener():
            logger.error("P2P监听器未成功启动，无法登录。")
            return False

        # 获取P2P监听器实际绑定的端口和本地IP地址，告知服务器
        self.p2p_manager.p2p_listen_socket.settimeout(None)
        self.p2p_manager.p2p_actual_port = self.p2p_manager.p2p_listen_socket.getsockname()[1]

        local_ip = '127.0.0.1'  # 默认本地回环地址
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))  # 尝试连接外部地址以获取本地IP，不发送数据
            local_ip = s.getsockname()[0]  # 获取本地IP地址
            s.close()
        except Exception:
            logger.warning("无法确定外部可访问的本地IP，使用127.0.0.1。")

        # 在登录前，更新 P2PManager 的身份信息。
        # 这里的用户名是登录凭据，将在登录成功后成为当前用户的实际用户名。
        # 这确保 P2PManager 在发起或接受P2P握手时能发送正确的用户名和公钥。
        self.p2p_manager.update_identity_info(username, self.my_public_key_pem)

        payload = {
            "username": username,
            "password": password,
            "p2p_ip": local_ip,
            "p2p_port": self.p2p_manager.p2p_actual_port
        }
        if self._send_request("LOGIN", payload):  # 发送登录请求
            response = self._receive_response()  # 接收服务器响应
            if response and response.get("status") == "success":
                self.logged_in_username = response["data"]["username"]
                self.logged_in_user_id = response["data"]["user_id"]  # 服务器会返回 user_id
                logger.info(f"登录成功: {self.logged_in_username}")
                # 登录成功后，立即获取在线好友列表，更新本地缓存
                self.get_online_friends()
                return True
            else:
                logger.error(f"登录失败: {response.get('message', '未知错误')}")
        return False

    def logout(self):
        """用户登出功能。"""
        if not self.logged_in_username:
            logger.warning("您尚未登录。")
            return False

        if self._send_request("LOGOUT"):  # 发送登出请求
            response = self._receive_response()  # 接收服务器响应
            if response and response.get("status") == "success":
                logger.info(f"登出成功: {response.get('message')}")
                self.logged_in_username = None
                self.logged_in_user_id = None
                self.disconnect_server()  # 登出后断开服务器连接并清理P2P资源
                return True
            else:
                logger.error(f"登出失败: {response.get('message', '未知错误')}")
        return False

    def add_friend(self, friend_username):
        """添加好友功能。"""
        if not self.logged_in_username:
            logger.warning("请先登录。")
            return False
        payload = {"friend_username": friend_username}
        if self._send_request("ADD_FRIEND", payload):  # 发送添加好友请求
            response = self._receive_response()
            if response and response.get("status") == "success":
                logger.info(f"添加好友成功: {response.get('message')}")
                self.get_online_friends()  # 刷新在线好友列表，以便更新P2P信息
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
        if self._send_request("REMOVE_FRIEND", payload):  # 发送删除好友请求
            response = self._receive_response()
            if response and response.get("status") == "success":
                logger.info(f"删除好友成功: {response.get('message')}")
                self.get_online_friends()  # 刷新在线好友列表
                return True
            else:
                logger.error(f"删除好友失败: {response.get('message', '未知错误')}")
        return False

    def get_online_friends(self):
        """从服务器获取在线好友列表，并更新本地缓存。"""
        if not self.logged_in_username:
            logger.warning("请先登录。")
            return False

        if self._send_request("GET_ONLINE_FRIENDS"):  # 发送获取在线好友请求
            response = self._receive_response()
            if response and response.get("status") == "success":
                friends_list = response["data"]["friends"]
                self.online_friends_info.clear()  # 清空旧的在线好友信息
                for friend in friends_list:
                    self.online_friends_info[friend["username"]] = friend  # 更新缓存
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

        if self._send_request("GET_ALL_FRIENDS"):  # 发送获取所有好友请求
            response = self._receive_response()
            if response and response.get("status") == "success":
                friends_list = response["data"]["friends"]
                logger.info(f"已获取所有好友列表。共 {len(friends_list)} 位好友。")
                return friends_list  # 直接返回列表，不存入 online_friends_info
            else:
                logger.error(f"获取所有好友失败: {response.get('message', '未知错误')}")
        return None

    def get_public_key_from_server(self, username):
        """
        从服务器获取指定用户的公钥。
        优先从本地缓存的在线好友信息中获取，若无则向服务器请求。
        这个公钥通常用于加密发送给该用户的消息。
        """
        if not self.logged_in_username:
            logger.warning("请先登录。")
            return None

        if username in self.online_friends_info:
            return self.online_friends_info[username]["public_key"]  # 从缓存中获取

        payload = {"username": username}
        if self._send_request("GET_PUBLIC_KEY", payload):  # 向服务器请求
            response = self._receive_response()
            if response and response.get("status") == "success":
                logger.info(f"成功从服务器获取 {username} 的公钥。")
                return response["data"]["public_key"]
            else:
                logger.error(f"从服务器获取 {username} 公钥失败: {response.get('message', '未知错误')}")
        return None

    def _handle_p2p_received_raw_data(self, peer_username, peer_public_key_pem, raw_data_bytes, sid=None):
        """
        P2PManager回调此函数，处理从P2P连接收到的原始（加密）数据。
        在此处进行解密操作，并将解密后的消息通过SocketIO推送到浏览器。
        :param peer_username: 发送方的用户名。
        :param peer_public_key_pem: 发送方的公钥PEM格式字符串。
        :param raw_data_bytes: 从P2P连接收到的原始字节数据（加密的JSON）。
        :param sid: 接收到消息的Web客户端的SocketIO会话ID，用于精确推送。
        """
        try:
            # 假定接收到的数据是JSON格式的加密消息载荷
            received_payload = json.loads(raw_data_bytes.decode('utf-8'))

            # 从JSON载荷中提取Base64编码的加密部分
            encrypted_key_b64 = received_payload.get("encrypted_key")
            encrypted_message_b64 = received_payload.get("encrypted_message")
            nonce_b64 = received_payload.get("nonce")
            tag_b64 = received_payload.get("tag")

            if not all([encrypted_key_b64, encrypted_message_b64, nonce_b64, tag_b64]):
                logger.warning(f"收到来自 {peer_username} 的不完整的加密P2P消息。")
                return

            # Base64解码回原始字节数据
            encrypted_key = base64.b64decode(encrypted_key_b64)
            encrypted_message = base64.b64decode(encrypted_message_b64)
            nonce = base64.b64decode(nonce_b64)
            tag = base64.b64decode(tag_b64)

            # 1. 使用自己的RSA私钥解密出一次性对称密钥 (AES Key)
            symmetric_key = self.rsa_util.decrypt_symmetric_key(encrypted_key)
            if not symmetric_key:
                logger.error(f"无法解密来自 {peer_username} 的对称密钥。")
                return

            # 2. 使用解密出的对称密钥解密实际消息
            decrypted_message_bytes = self.aes_util.decrypt_message(encrypted_message, nonce, tag, symmetric_key)
            if decrypted_message_bytes is None:  # 解密失败（例如，认证标签无效表示消息被篡改）
                logger.error(f"无法解密来自 {peer_username} 的消息，可能被篡改或密钥错误。")
                return

            decrypted_message = decrypted_message_bytes.decode('utf-8')  # 将解密后的字节数据解码为字符串
            logger.info(f"解密成功！[P2P消息 from {peer_username}]: {decrypted_message}")

            # 将解密后的消息通过 SocketIO 推送到浏览器
            if sid:  # 检查是否有有效的 SID 可以推送
                self.socketio_instance.emit('receive_message',
                                            {'sender': peer_username, 'message': decrypted_message},
                                            room=sid)
                logger.debug(f"通过SocketIO向SID {sid} 推送消息。")
            else:
                logger.warning(f"没有可用的SocketIO SID，消息无法推送到浏览器。")

        except json.JSONDecodeError:
            logger.error(f"收到来自 {peer_username} 的无效P2P消息JSON格式。")
        except Exception as ex:
            logger.error(f"处理或解密来自 {peer_username} 的P2P消息时出错: {ex}", exc_info=True)

    def send_p2p_message(self, recipient_username, message):
        """
        向指定好友发送加密的P2P消息。
        此函数协调 P2P 连接的建立（如果尚未建立）和消息的加密发送。
        :param recipient_username: 接收方的用户名。
        :param message: 要发送的文本消息。
        """
        if not self.logged_in_username:
            logger.warning("请先登录。")
            return False

        friend_info = self.online_friends_info.get(recipient_username)

        if not friend_info:  # 只有在线好友才能进行P2P直连聊天
            logger.error(f"好友 '{recipient_username}' 不在线或不在您的好友列表中，无法进行P2P聊天。")
            return False

        friend_ip = friend_info["ip"]
        friend_port = friend_info["port"]
        friend_public_key_pem = friend_info["public_key"]  # 接收方的公钥，用于加密对称密钥

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
            # 每次发送消息都生成一个新的对称密钥，增加安全性（前向保密性）。
            aes_key = os.urandom(32)  # AES-256 需要32字节的密钥

            # 2. 使用接收方的RSA公钥加密这个对称密钥
            # 只有接收方（拥有对应私钥）才能解密出这个AES密钥。
            encrypted_aes_key = self.rsa_util.encrypt_symmetric_key(friend_public_key_pem, aes_key)
            if encrypted_aes_key is None:
                logger.error("无法加密对称密钥，消息发送失败。")
                return False

            # 3. 使用对称密钥加密实际消息
            # GCM模式会返回密文、Nonce和认证标签，这些都是解密所必需的。
            encrypted_message, nonce, tag = self.aes_util.encrypt_message(message.encode('utf-8'), aes_key)
            if encrypted_message is None:
                logger.error("无法加密消息，消息发送失败。")
                return False

            # 将所有加密后的二进制数据（密文、密钥、Nonce、Tag）转换为Base64编码，
            # 因为JSON协议通常传输文本，二进制数据需要先编码。
            encrypted_payload = {
                "encrypted_key": base64.b64encode(encrypted_aes_key).decode('utf-8'),
                "encrypted_message": base64.b64encode(encrypted_message).decode('utf-8'),
                "nonce": base64.b64encode(nonce).decode('utf-8'),
                "tag": base64.b64encode(tag).decode('utf-8')
            }

            # 调用 P2PManager 发送加密后的JSON数据（原始字节形式）
            # P2PManager 只负责传输，不关心数据内容是否加密。
            if self.p2p_manager.send_p2p_raw_data(recipient_username,
                                                  json.dumps(encrypted_payload, ensure_ascii=False).encode('utf-8')):
                logger.info(f"已发送加密P2P消息给 {recipient_username}.")
                return True
            else:
                logger.error(f"通过P2PManager发送消息给 {recipient_username} 失败。")
                return False

        except Exception as e:
            logger.error(f"加密或发送P2P消息给 {recipient_username} 时出错: {e}", exc_info=True)
            return False
