import socket
import threading
import json
import time
import logging
import base64  # P2P Manager 转发 Base64 编码的加密数据

# from flask_socketio import SocketIO # 不能直接导入，否则会循环依赖

logger = logging.getLogger(__name__)


class P2PManager:
    """
    P2PManager 负责点对点连接的建立、监听和数据的发送/接收。
    它不处理加密/解密逻辑，只处理原始的字节数据传输。
    当接收到数据时，它通过回调函数通知 ChatClient 进行解密。
    """

    def __init__(self, p2p_listen_host, p2p_listen_port, buffer_size, socketio_instance, sid_getter_callback,
                 decrypt_and_process_callback, identity_info):
        """
        P2P管理器初始化。
        :param p2p_listen_host: P2P监听的IP地址。
        :param p2p_listen_port: P2P监听的端口，0表示随机分配。
        :param buffer_size: 接收缓冲区大小。
        :param socketio_instance: Flask-SocketIO 实例，用于向客户端浏览器发送实时消息。
        :param sid_getter_callback: 一个回调函数，用于获取当前用户的 SocketIO 会话ID (sid)。
        :param decrypt_and_process_callback: 当接收到P2P消息时调用的回调函数 (peer_username, peer_public_key_pem, raw_data_bytes)。
                                             这个回调函数将原始数据传回给ChatClient进行解密。
        :param identity_info: 包含当前用户用户名和公钥PEM字符串的字典，用于P2P握手时发送自己的身份。
        """
        self._p2p_listen_host = p2p_listen_host
        self._p2p_listen_port = p2p_listen_port
        self._buffer_size = buffer_size
        self._socketio = socketio_instance  # Flask-SocketIO 实例
        self._get_sid_callback = sid_getter_callback  # 用于获取当前用户的sid
        self._decrypt_and_process_callback = decrypt_and_process_callback  # 收到加密消息后回调 ChatClient 解密
        self._identity_info = identity_info  # 当前客户端的身份信息，用于P2P握手

        self.p2p_listen_socket = None  # P2P监听socket
        self.p2p_actual_port = None  # P2P实际监听的端口号（由操作系统分配）
        self.p2p_listener_thread = None  # P2P监听线程对象
        self.stop_p2p_listener_event = threading.Event()  # 用于控制监听线程停止的事件

        # 存储活跃的P2P连接 {对等体用户名: socket对象}
        self.active_p2p_connections = {}
        self.p2p_connections_lock = threading.Lock()  # 用于保护 active_p2p_connections 字典的线程锁，防止多线程访问冲突

    def update_identity_info(self, username, public_key_pem):
        """更新P2P管理器中的身份信息，主要在登录成功后调用。"""
        self._identity_info["username"] = username
        self._identity_info["public_key_pem"] = public_key_pem
        logger.debug(f"P2PManager: 身份信息更新为 {username}.")

    def start_p2p_listener(self):
        """启动一个线程来监听P2P连接。"""
        if self.p2p_listener_thread and self.p2p_listener_thread.is_alive():
            logger.info("P2PManager: P2P监听器已在运行。")
            return True

        self.stop_p2p_listener_event.clear()  # 清除停止事件，准备启动新监听
        self.p2p_listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 创建TCP socket
        self.p2p_listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 允许端口重用，避免重启时端口被占用
        try:
            self.p2p_listen_socket.bind((self._p2p_listen_host, self._p2p_listen_port))  # 绑定地址和端口
            self.p2p_actual_port = self.p2p_listen_socket.getsockname()[1]  # 获取操作系统实际分配的端口
            self.p2p_listen_socket.listen(5)  # 开始监听，最多5个挂起连接
            logger.info(f"P2PManager: P2P监听器已在 {self._p2p_listen_host}:{self.p2p_actual_port} 启动。")

            # 创建并启动监听线程
            self.p2p_listener_thread = threading.Thread(target=self._p2p_listener_loop)
            self.p2p_listener_thread.daemon = True  # 设置为守护线程，主程序退出时它也会退出
            self.p2p_listener_thread.start()
            return True
        except socket.error as e:
            logger.error(f"P2PManager: 启动P2P监听器失败: {e}", exc_info=True)
            if self.p2p_listen_socket:
                try:
                    if self.p2p_listen_socket.fileno() != -1:
                self.p2p_listen_socket.close()  # 失败时关闭socket
                except socket.error as close_error:
                    logger.debug(f"P2PManager: 关闭失败的监听socket时出错: {close_error}")
                except Exception as close_error:
                    logger.debug(f"P2PManager: 关闭失败的监听socket时发生未知错误: {close_error}")
            self.p2p_listen_socket = None
            self.p2p_actual_port = None
            return False

    def _p2p_listener_loop(self):
        """P2P监听线程的主循环，负责接受传入连接。"""
        while not self.stop_p2p_listener_event.is_set():  # 循环直到收到停止事件
            try:
                # 检查监听socket是否有效
                if not self.p2p_listen_socket or self.p2p_listen_socket.fileno() == -1:
                    logger.warning("P2PManager: 监听socket无效，退出监听循环")
                    break
                    
                self.p2p_listen_socket.settimeout(1.0)  # 设置accept超时，以便每隔1秒检查停止事件
                conn, addr = self.p2p_listen_socket.accept()  # 接受新的连接，此方法会阻塞直到有连接或超时
                logger.info(f"P2PManager: 接收到来自 {addr} 的P2P连接。")

                # P2P连接建立后的初步握手：接收对方的身份信息和公钥
                initial_data_raw = conn.recv(self._buffer_size)
                if not initial_data_raw:
                    try:
                        if conn.fileno() != -1:
                    conn.close()
                    except socket.error as e:
                        logger.debug(f"P2PManager: 关闭无效连接时出错: {e}")
                    except Exception as e:
                        logger.debug(f"P2PManager: 关闭无效连接时发生未知错误: {e}")
                    logger.warning(f"P2PManager: P2P连接从 {addr} 接收到空初始化数据。")
                    continue

                try:
                    initial_payload = json.loads(initial_data_raw.decode('utf-8'))
                    peer_username = initial_payload.get("username")
                    peer_public_key_pem = initial_payload.get("public_key")

                    if peer_username and peer_public_key_pem:
                        logger.info(f"P2PManager: P2P连接握手成功，对方是: {peer_username}")

                        # 立即发送自己的身份信息，完成双向握手（确认身份）
                        my_initial_payload = {
                            "username": self._identity_info["username"],
                            "public_key": self._identity_info["public_key_pem"]
                        }
                        conn.sendall(json.dumps(my_initial_payload, ensure_ascii=False).encode('utf-8'))

                        # 将新连接添加到活跃P2P连接列表
                        with self.p2p_connections_lock:
                            # 避免重复添加，如果已存在同名用户的连接，则关闭旧的
                            if peer_username in self.active_p2p_connections:
                                old_sock = self.active_p2p_connections[peer_username]
                                try:
                                    # 检查socket是否有效
                                    if old_sock and old_sock.fileno() != -1:
                                    old_sock.close()  # 尝试关闭旧连接
                                except socket.error as e:
                                    logger.debug(f"P2PManager: 关闭与 {peer_username} 的旧连接时出错: {e}")
                                except Exception as e:
                                    logger.debug(f"P2PManager: 关闭与 {peer_username} 的旧连接时发生未知错误: {e}")
                            self.active_p2p_connections[peer_username] = conn

                        # 启动一个新线程来处理该P2P连接的消息接收
                        p2p_handler_thread = threading.Thread(target=self._handle_p2p_connection,
                                                              args=(conn, peer_username, peer_public_key_pem))
                        p2p_handler_thread.daemon = True
                        p2p_handler_thread.start()
                    else:
                        logger.warning(f"P2PManager: 接收到无效的P2P连接初始化数据 from {addr}: {initial_payload}")
                        try:
                            if conn.fileno() != -1:
                        conn.close()  # 关闭无效连接
                        except socket.error as e:
                            logger.debug(f"P2PManager: 关闭无效连接时出错: {e}")
                        except Exception as e:
                            logger.debug(f"P2PManager: 关闭无效连接时发生未知错误: {e}")

                except json.JSONDecodeError:
                    logger.error(
                        f"P2PManager: 收到来自 {addr} 的无效P2P连接初始化JSON: {initial_data_raw.decode(errors='ignore')}",
                        exc_info=True)
                    try:
                        if conn.fileno() != -1:
                    conn.close()
                    except socket.error as e:
                        logger.debug(f"P2PManager: 关闭无效JSON连接时出错: {e}")
                    except Exception as e:
                        logger.debug(f"P2PManager: 关闭无效JSON连接时发生未知错误: {e}")
            except socket.timeout:
                continue  # 超时是正常的，循环继续检查停止事件
            except socket.error as e:
                # 检查是否是由于监听器停止而导致的错误
                if self.stop_p2p_listener_event.is_set():
                    break  # 正常关闭，退出循环
                logger.error(f"P2PManager: P2P监听器出错: {e}", exc_info=True)
                break  # 出现其他错误则退出监听循环
            except Exception as e:
                logger.error(f"P2PManager: P2P监听循环中发生未知错误: {e}", exc_info=True)
                break
        logger.info("P2PManager: P2P监听器已停止。")
        if self.p2p_listen_socket:
            try:
                # 检查socket是否有效
                if self.p2p_listen_socket.fileno() != -1:
                self.p2p_listen_socket.close()  # 关闭监听socket
            except socket.error as e:
                logger.warning(f"P2PManager: 关闭P2P监听socket时出错: {e}")
            except Exception as e:
                logger.warning(f"P2PManager: 关闭P2P监听socket时发生未知错误: {e}")
        self.p2p_listen_socket = None
        self.p2p_actual_port = None

    def _handle_p2p_connection(self, conn_socket, peer_username, peer_public_key_pem):
        """
        处理来自单个P2P连接的消息接收。
        此线程持续接收数据，并将接收到的原始数据通过回调函数传递给ChatClient处理。
        :param conn_socket: 与对等体建立的socket连接。
        :param peer_username: 对等体的用户名。
        :param peer_public_key_pem: 对等体的公钥PEM格式字符串。
        """
        logger.info(f"P2PManager: P2P消息处理器为 {peer_username} 启动。")

        try:
            while True:
                raw_data = conn_socket.recv(self._buffer_size)  # 接收原始字节数据
                if not raw_data:  # 如果收到空数据，表示连接已关闭
                    logger.info(f"P2PManager: P2P连接与 {peer_username} 断开。")
                    break

                # 收到数据后，调用回调函数将数据传递给 ChatClient 进行解密和处理
                if self._decrypt_and_process_callback:
                    # 将收到的数据（可能是加密的JSON）、对等体用户名和其公钥（用于解密）传递给回调函数
                    # 注意：这里还会通过 SocketIO 将消息推送到浏览器
                    current_sid = self._get_sid_callback()  # 获取当前用户的 SocketIO SID
                    if current_sid:
                        self._decrypt_and_process_callback(peer_username, peer_public_key_pem, raw_data, current_sid)
                    else:
                        logger.warning(
                            f"P2PManager: 无法获取用户 {self._identity_info['username']} 的SID，无法推送消息。")
                        # 即使无法推送，也要尝试解密和记录
                        self._decrypt_and_process_callback(peer_username, peer_public_key_pem, raw_data, None)  # 传递None

        except socket.error as e:
            logger.error(f"P2PManager: P2P连接与 {peer_username} 发生错误: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"P2PManager: 处理 {peer_username} 的P2P消息时发生未知错误: {e}", exc_info=True)
        finally:
            try:
                # 检查socket是否有效
                if conn_socket and conn_socket.fileno() != -1:
            conn_socket.close()  # 关闭此P2P连接的socket
            except socket.error as e:
                logger.warning(f"P2PManager: 关闭与 {peer_username} 的P2P连接socket时出错: {e}")
            except Exception as e:
                logger.warning(f"P2PManager: 关闭与 {peer_username} 的P2P连接socket时发生未知错误: {e}")
            
            with self.p2p_connections_lock:
                if peer_username in self.active_p2p_connections:
                    del self.active_p2p_connections[peer_username]  # 从活跃连接列表中移除
            logger.info(f"P2PManager: P2P消息处理器为 {peer_username} 停止。")

    def stop_p2p_listener(self):
        """停止P2P监听器线程。"""
        if self.p2p_listener_thread and self.p2p_listener_thread.is_alive():
            logger.info("P2PManager: 正在停止P2P监听器...")
            self.stop_p2p_listener_event.set()  # 设置停止事件，通知监听线程退出循环
            
            # 优雅地关闭监听socket
            if self.p2p_listen_socket:
                try:
                    # 在Windows上，如果socket没有连接，shutdown会抛出错误
                    # 先检查socket是否有效，再尝试shutdown
                    if self.p2p_listen_socket.fileno() != -1:
                try:
                    self.p2p_listen_socket.shutdown(socket.SHUT_RDWR)  # 关闭socket，解除accept()的阻塞
                        except socket.error as e:
                            # Windows上常见的错误，socket没有连接时shutdown会失败
                            if e.winerror == 10057:  # [WinError 10057] 由于套接字没有连接
                                logger.debug("P2PManager: 监听socket未连接，跳过shutdown操作")
                            else:
                                logger.warning(f"P2PManager: shutdown监听socket时出错: {e}")
                        finally:
                    self.p2p_listen_socket.close()
                except socket.error as e:
                    logger.warning(f"P2PManager: 关闭P2P监听socket时出错: {e}")
                except Exception as e:
                    logger.warning(f"P2PManager: 关闭P2P监听socket时发生未知错误: {e}")
            
            self.p2p_listener_thread.join(timeout=2)  # 等待监听线程结束，设置超时防止卡死
            if self.p2p_listener_thread.is_alive():
                logger.warning("P2PManager: P2P监听线程未能优雅关闭。")
            self.p2p_listener_thread = None

    def close_all_p2p_connections(self):
        """关闭所有活跃的P2P连接。"""
        with self.p2p_connections_lock:  # 使用锁保护字典操作
            # 遍历字典的副本，因为在循环中会修改字典
            for username, sock in list(self.active_p2p_connections.items()):
                try:
                    # 检查socket是否有效
                    if sock and sock.fileno() != -1:
                try:
                    sock.shutdown(socket.SHUT_RDWR)  # 关闭读写
                        except socket.error as e:
                            # Windows上常见的错误，socket没有连接时shutdown会失败
                            if hasattr(e, 'winerror') and e.winerror == 10057:  # [WinError 10057] 由于套接字没有连接
                                logger.debug(f"P2PManager: 与 {username} 的连接未建立，跳过shutdown操作")
                            else:
                                logger.warning(f"P2PManager: shutdown与 {username} 的连接时出错: {e}")
                        finally:
                    sock.close()  # 关闭socket
                    logger.info(f"P2PManager: 已关闭与 {username} 的P2P连接。")
                    else:
                        logger.debug(f"P2PManager: 与 {username} 的连接已无效，跳过关闭操作")
                except socket.error as e:
                    logger.warning(f"P2PManager: 关闭与 {username} 的P2P连接时出错: {e}")
                except Exception as e:
                    logger.warning(f"P2PManager: 关闭与 {username} 的P2P连接时发生未知错误: {e}")
                finally:
                del self.active_p2p_connections[username]  # 从字典中移除

    def connect_p2p_peer(self, recipient_username, friend_ip, friend_port, my_username, my_public_key_pem):
        """
        尝试与一个P2P对等体建立连接。
        这是一个出站连接，会发送自己的身份信息，并等待对方响应完成握手。
        :param recipient_username: 目标对等体的用户名。
        :param friend_ip: 目标对等体的IP地址。
        :param friend_port: 目标对等体的P2P监听端口。
        :param my_username: 当前用户的用户名（用于握手）。
        :param my_public_key_pem: 当前用户的公钥PEM字符串（用于握手）。
        :return: 建立的socket对象，如果连接成功并完成握手；否则返回None。
        """
        logger.info(f"P2PManager: 正在尝试与 {recipient_username} ({friend_ip}:{friend_port}) 建立P2P连接...")
        try:
            conn_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 创建TCP socket
            conn_socket.connect((friend_ip, friend_port))  # 连接到目标P2P地址

            # 首次连接时发送自己的身份和公钥，作为简单的握手请求
            initial_payload = {"username": my_username, "public_key": my_public_key_pem}
            conn_socket.sendall(json.dumps(initial_payload, ensure_ascii=False).encode('utf-8'))

            # 等待对方也发送身份信息，完成简单的双向握手（确认对方身份）
            response_data_raw = conn_socket.recv(self._buffer_size)
            if not response_data_raw:
                try:
                    if conn_socket.fileno() != -1:
                conn_socket.close()
                except socket.error as e:
                    logger.debug(f"P2PManager: 关闭空响应连接时出错: {e}")
                except Exception as e:
                    logger.debug(f"P2PManager: 关闭空响应连接时发生未知错误: {e}")
                logger.warning(f"P2PManager: 从 {recipient_username} 接收到空握手响应。")
                return None

            try:
                response_payload = json.loads(response_data_raw.decode('utf-8'))
                # 简单验证：检查对方返回的用户名是否与预期匹配
                if response_payload.get("username") == recipient_username:
                    logger.info(f"P2PManager: 成功与 {recipient_username} 建立P2P连接并完成握手。")
                    # 将新连接添加到活跃P2P连接列表
                    with self.p2p_connections_lock:
                        # 如果已存在同名用户的连接，则关闭旧的并替换
                        if recipient_username in self.active_p2p_connections:
                            old_sock = self.active_p2p_connections[recipient_username]
                            try:
                                # 检查socket是否有效
                                if old_sock and old_sock.fileno() != -1:
                                old_sock.close()  # 关闭旧连接
                            except socket.error as e:
                                logger.debug(f"P2PManager: 关闭与 {recipient_username} 的旧连接时出错: {e}")
                            except Exception as e:
                                logger.debug(f"P2PManager: 关闭与 {recipient_username} 的旧连接时发生未知错误: {e}")
                        self.active_p2p_connections[recipient_username] = conn_socket

                    # 启动一个新线程来处理这个出站连接的消息接收
                    # 传入从对方握手响应中获取的公钥，以便后续解密来自此对等体的消息
                    peer_public_key_from_response = response_payload.get("public_key")
                    threading.Thread(target=self._handle_p2p_connection,
                                     args=(conn_socket, recipient_username, peer_public_key_from_response)).start()
                    return conn_socket
                else:
                    logger.warning(
                        f"P2PManager: 握手失败，对等体身份不匹配: 预期'{recipient_username}', 实际'{response_payload.get('username')}'")
                    try:
                        if conn_socket.fileno() != -1:
                    conn_socket.close()
                    except socket.error as e:
                        logger.debug(f"P2PManager: 关闭身份不匹配连接时出错: {e}")
                    except Exception as e:
                        logger.debug(f"P2PManager: 关闭身份不匹配连接时发生未知错误: {e}")
                    return None
            except json.JSONDecodeError:
                logger.error(f"P2PManager: 从 {recipient_username} 收到无效的握手响应JSON。", exc_info=True)
                try:
                    if conn_socket.fileno() != -1:
                conn_socket.close()
                except socket.error as e:
                    logger.debug(f"P2PManager: 关闭无效JSON响应连接时出错: {e}")
                except Exception as e:
                    logger.debug(f"P2PManager: 关闭无效JSON响应连接时发生未知错误: {e}")
                return None

        except socket.error as e:
            logger.error(f"P2PManager: 建立与 {recipient_username} 的P2P连接失败: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"P2PManager: 连接P2P对等体 {recipient_username} 时发生未知错误: {e}", exc_info=True)
            return None

    def send_p2p_raw_data(self, recipient_username, data_bytes):
        """
        向指定的活跃P2P连接发送原始字节数据（通常是加密后的消息载荷）。
        :param recipient_username: 接收方的用户名。
        :param data_bytes: 要发送的原始字节数据。
        :return: True如果发送成功，False失败。
        """
        conn_socket = self.active_p2p_connections.get(recipient_username)
        if not conn_socket:
            logger.error(f"P2PManager: 未找到与 {recipient_username} 的活跃P2P连接。")
            return False

        try:
            conn_socket.sendall(data_bytes)  # 发送数据
            logger.debug(f"P2PManager: 已向 {recipient_username} 发送原始数据 ({len(data_bytes)} 字节)。")
            return True
        except socket.error as e:
            logger.error(f"P2PManager: 向 {recipient_username} 发送数据失败: {e}", exc_info=True)
            # 发送失败通常意味着连接断开，进行清理
            with self.p2p_connections_lock:
                if recipient_username in self.active_p2p_connections:
                    try:
                        sock = self.active_p2p_connections[recipient_username]
                        if sock and sock.fileno() != -1:
                            sock.close()
                    except socket.error as e:
                        logger.debug(f"P2PManager: 清理与 {recipient_username} 的连接时出错: {e}")
                    except Exception as e:
                        logger.debug(f"P2PManager: 清理与 {recipient_username} 的连接时发生未知错误: {e}")
                    finally:
                    del self.active_p2p_connections[recipient_username]
            logger.info(f"P2PManager: 与 {recipient_username} 的P2P连接已断开。")
            return False
        except Exception as e:
            logger.error(f"P2PManager: 发送P2P原始数据时发生未知错误: {e}", exc_info=True)
            return False