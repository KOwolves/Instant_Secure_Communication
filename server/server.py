import socket
import threading
import json
import logging


from db import DatabaseManager
from config import SERVER_HOST, SERVER_PORT, BUFFER_SIZE

logger = logging.getLogger(__name__)

class SecureChatServer:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.online_sessions = {}  # {user_id: client_socket}
        self.session_lock = threading.Lock()  # 用于保护 online_sessions
        logger.info("SecureChatServer: 服务器初始化完成。")

    def start(self):
        try:
            self.server_socket.bind((SERVER_HOST, SERVER_PORT))
            self.server_socket.listen(5)  # 最多5个待处理连接
            logger.info(f"SecureChatServer: 服务器正在监听 {SERVER_HOST}:{SERVER_PORT}")

            while True:
                client_socket, client_address = self.server_socket.accept()
                logger.info(f"SecureChatServer: 收到来自 {client_address} 的新连接。")
                client_thread = threading.Thread(target=self._handle_client, args=(client_socket, client_address))
                client_thread.daemon = True  # 允许主程序在线程仍在运行时退出
                client_thread.start()

        except Exception as e:
            logger.critical(f"SecureChatServer: 服务器启动错误: {e}", exc_info=True)
        finally:
            if self.server_socket:
                try:
                    self.server_socket.close()
                    logger.info("SecureChatServer: 服务器socket已关闭。")
                except socket.error as e:
                    logger.error(f"SecureChatServer: 关闭服务器socket时出错: {e}", exc_info=True)
            logger.info("SecureChatServer: 服务器已关闭。")

    def _send_response(self, client_socket, status, message, data=None):
        """向客户端发送标准化的JSON响应。"""
        response = {"status": status, "message": message}
        if data:
            response["data"] = data
        try:
            client_socket.sendall(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            logger.debug(f"SecureChatServer: 已向客户端发送响应: status={status}, message={message}, data={data}")
        except socket.error as e:
            logger.error(f"SecureChatServer: 向客户端发送响应时出错: {e}", exc_info=True)

    def _handle_client(self, client_socket, client_address):
        logger.info(f"SecureChatServer: 客户端处理线程为 {client_address} 启动。")
        logged_in_user_id = None
        logged_in_username = None

        try:
            while True:
                data = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if not data:
                    # 客户端断开连接，但只有在用户已登录时才清除在线状态
                    if logged_in_user_id is not None:
                        self.db_manager.clear_online_status(logged_in_user_id)
                        logger.info(f"SecureChatServer: 客户端 {client_address} 断开连接，已清除用户 {logged_in_username} (ID: {logged_in_user_id}) 的在线状态。")
                    else:
                        logger.info(f"SecureChatServer: 客户端 {client_address} 断开连接，用户未登录。")
                    break

                try:
                    request = json.loads(data)
                    command = request.get("command")
                    payload = request.get("payload", {})
                    logger.info(f"SecureChatServer: 收到来自 {client_address} 的命令: {command}")
                    logger.debug(f"SecureChatServer: 收到命令Payload: {payload}")

                    if command == "REGISTER":
                        username = payload.get("username")
                        password = payload.get("password")
                        public_key = payload.get("public_key")

                        if not (username and password and public_key):
                            self._send_response(client_socket, "error", "缺少用户名、密码或公钥。")
                            logger.warning(f"SecureChatServer: 注册请求缺少必要参数来自 {client_address}")
                            continue

                        if self.db_manager.register_user(username, password, public_key):
                            self._send_response(client_socket, "success", "注册成功。")
                            logger.info(f"SecureChatServer: 用户 {username} 已注册。")
                        else:
                            self._send_response(client_socket, "error", "注册失败，用户名可能已存在。")
                            logger.warning(f"SecureChatServer: 用户 {username} 注册失败，可能已存在。")

                    elif command == "LOGIN":
                        username = payload.get("username")
                        password = payload.get("password")
                        client_p2p_ip = payload.get("p2p_ip", client_address[0])
                        client_p2p_port = payload.get("p2p_port")

                        if not (username and password and client_p2p_port is not None):
                            self._send_response(client_socket, "error", "缺少用户名、密码或P2P端口。")
                            logger.warning(f"SecureChatServer: 登录请求缺少必要参数来自 {client_address}")
                            continue

                        user_id, public_key = self.db_manager.authenticate_user(username, password)
                        if user_id:
                            with self.session_lock:
                                if user_id in self.online_sessions:
                                    self._send_response(client_socket, "error", "用户已登录。")
                                    logger.warning(f"SecureChatServer: 用户 {username} 尝试重复登录。")
                                    continue

                                self.online_sessions[user_id] = client_socket  # 存储控制连接的socket

                            self.db_manager.set_online_status(user_id, client_p2p_ip, client_p2p_port)
                            logged_in_user_id = user_id
                            logged_in_username = username
                            self._send_response(client_socket, "success", "登录成功。",
                                                data={"username": username, "user_id": user_id,
                                                      "public_key": public_key})
                            logger.info(f"SecureChatServer: 用户 {username} (ID: {user_id}) 从 {client_address} 登录。")
                        else:
                            self._send_response(client_socket, "error", "用户名或密码无效。")
                            logger.warning(f"SecureChatServer: 用户 {username} 登录失败，凭据无效。")

                    elif command == "LOGOUT":
                        if logged_in_user_id:
                            # 先记录用户信息，再清除
                            user_id_to_logout = logged_in_user_id
                            username_to_logout = logged_in_username
                            
                            self.db_manager.clear_online_status(logged_in_user_id)
                            with self.session_lock:
                                if logged_in_user_id in self.online_sessions:
                                    del self.online_sessions[logged_in_user_id]
                            self._send_response(client_socket, "success", "登出成功。")
                            logger.info(f"SecureChatServer: 用户 {username_to_logout} (ID: {user_id_to_logout}) 已登出。")
                            
                            # 清除登录状态
                            logged_in_user_id = None
                            logged_in_username = None
                        else:
                            self._send_response(client_socket, "error", "未登录。")
                            logger.warning(f"SecureChatServer: 未登录用户尝试登出，来自 {client_address}。")

                    elif command == "GET_ONLINE_FRIENDS":
                        if not logged_in_user_id:
                            self._send_response(client_socket, "error", "请先登录。")
                            logger.warning(f"SecureChatServer: 未登录用户尝试获取在线好友列表，来自 {client_address}。")
                            continue

                        online_friends_list = self.db_manager.get_online_friends_info(logged_in_user_id)
                        self._send_response(client_socket, "success", "在线好友已检索。",
                                            data={"friends": online_friends_list})
                        logger.info(f"SecureChatServer: 向 {logged_in_username} 提供了 {len(online_friends_list)} 个在线好友列表。")

                    elif command == "GET_ALL_FRIENDS":
                        if not logged_in_user_id:
                            self._send_response(client_socket, "error", "请先登录。")
                            logger.warning(f"SecureChatServer: 未登录用户尝试获取所有好友列表，来自 {client_address}。")
                            continue

                        all_friends_list = self.db_manager.get_all_friends_info(logged_in_user_id)
                        self._send_response(client_socket, "success", "所有好友已检索。",
                                            data={"friends": all_friends_list})
                        logger.info(
                            f"SecureChatServer: 向 {logged_in_username} 提供了 {len(all_friends_list)} 个所有好友列表。")


                    elif command == "ADD_FRIEND":
                        if not logged_in_user_id:
                            self._send_response(client_socket, "error", "请先登录。")
                            logger.warning(f"SecureChatServer: 未登录用户尝试添加好友，来自 {client_address}。")
                            continue

                        friend_username_to_add = payload.get("friend_username")
                        if not friend_username_to_add:
                            self._send_response(client_socket, "error", "缺少好友用户名。")
                            logger.warning(f"SecureChatServer: 添加好友请求缺少用户名来自 {logged_in_username}。")
                            continue

                        friend_id_to_add = self.db_manager.get_user_id(friend_username_to_add)
                        if not friend_id_to_add:
                            self._send_response(client_socket, "error", f"用户 '{friend_username_to_add}' 不存在。")
                            logger.warning(f"SecureChatServer: 用户 {logged_in_username} 尝试添加不存在的用户 {friend_username_to_add}。")
                        elif friend_id_to_add == logged_in_user_id:
                            self._send_response(client_socket, "error", "不能添加自己为好友。")
                            logger.warning(f"SecureChatServer: 用户 {logged_in_username} 尝试添加自己为好友。")
                        elif self.db_manager.add_friendship(logged_in_user_id, friend_id_to_add):
                            self._send_response(client_socket, "success",
                                                f"'{friend_username_to_add}' 已添加到您的好友列表。")
                            logger.info(f"SecureChatServer: 用户 {logged_in_username} 添加 {friend_username_to_add} (ID: {friend_id_to_add}) 为好友成功。")
                        else:
                            self._send_response(client_socket, "error",
                                                f"无法添加 '{friend_username_to_add}' 为好友 (可能已经是好友)。")
                            logger.warning(f"SecureChatServer: 用户 {logged_in_username} 无法添加 {friend_username_to_add} 为好友，可能已是好友。")

                    elif command == "REMOVE_FRIEND":
                        if not logged_in_user_id:
                            self._send_response(client_socket, "error", "请先登录。")
                            logger.warning(f"SecureChatServer: 未登录用户尝试删除好友，来自 {client_address}。")
                            continue

                        friend_username_to_remove = payload.get("friend_username")
                        if not friend_username_to_remove:
                            self._send_response(client_socket, "error", "缺少要删除的好友用户名。")
                            logger.warning(f"SecureChatServer: 删除好友请求缺少用户名来自 {logged_in_username}。")
                            continue

                        friend_id_to_remove = self.db_manager.get_user_id(friend_username_to_remove)
                        if not friend_id_to_remove:
                            self._send_response(client_socket, "error", f"用户 '{friend_username_to_remove}' 不存在。")
                            logger.warning(f"SecureChatServer: 用户 {logged_in_username} 尝试删除不存在的用户 {friend_username_to_remove}。")
                        elif self.db_manager.remove_friendship(logged_in_user_id, friend_id_to_remove):
                            self._send_response(client_socket, "success",
                                                f"'{friend_username_to_remove}' 已从您的好友列表中移除。")
                            logger.info(f"SecureChatServer: 用户 {logged_in_username} 成功移除了 {friend_username_to_remove} (ID: {friend_id_to_remove})。")
                        else:
                            self._send_response(client_socket, "error",
                                                f"无法移除 '{friend_username_to_remove}' (可能不是好友)。")
                            logger.warning(f"SecureChatServer: 用户 {logged_in_username} 无法移除 {friend_username_to_remove}，可能不是好友。")

                    elif command == "GET_PUBLIC_KEY":
                        if not logged_in_user_id:
                            self._send_response(client_socket, "error", "请先登录。")
                            logger.warning(f"SecureChatServer: 未登录用户尝试获取公钥，来自 {client_address}。")
                            continue

                        target_username = payload.get("username")
                        if not target_username:
                            self._send_response(client_socket, "error", "缺少目标用户名。")
                            logger.warning(f"SecureChatServer: 获取公钥请求缺少用户名来自 {logged_in_username}。")
                            continue

                        public_key = self.db_manager.get_public_key(target_username)
                        if public_key:
                            self._send_response(client_socket, "success", f"已检索到 {target_username} 的公钥。",
                                                data={"public_key": public_key})
                            logger.info(f"SecureChatServer: 向 {logged_in_username} 提供了 {target_username} 的公钥。")
                        else:
                            self._send_response(client_socket, "error", f"未找到 {target_username} 的公钥。")
                            logger.warning(f"SecureChatServer: 未找到用户 {target_username} 的公钥，请求来自 {logged_in_username}。")

                    elif command == "UPDATE_P2P_INFO":  # 客户端更新其P2P监听信息
                        if not logged_in_user_id:
                            self._send_response(client_socket, "error", "请先登录。")
                            logger.warning(f"SecureChatServer: 未登录用户尝试更新P2P信息，来自 {client_address}。")
                            continue

                        new_p2p_ip = payload.get("p2p_ip", client_address[0])
                        new_p2p_port = payload.get("p2p_port")

                        if new_p2p_port is None:
                            self._send_response(client_socket, "error", "缺少新的P2P端口。")
                            logger.warning(f"SecureChatServer: 更新P2P信息请求缺少P2P端口来自 {logged_in_username}。")
                            continue

                        if self.db_manager.set_online_status(logged_in_user_id, new_p2p_ip, new_p2p_port):
                            self._send_response(client_socket, "success", "P2P信息更新成功。")
                            logger.info(f"SecureChatServer: 用户 {logged_in_username}'s P2P信息已更新为 {new_p2p_ip}:{new_p2p_port}。")
                        else:
                            self._send_response(client_socket, "error", "更新P2P信息失败。")
                            logger.error(f"SecureChatServer: 用户 {logged_in_username} 更新P2P信息失败。")

                    elif command == "GET_ALL_USERS":  # 额外功能：获取所有用户，方便查找好友
                        if not logged_in_user_id:
                            self._send_response(client_socket, "error", "请先登录。")
                            logger.warning(f"SecureChatServer: 未登录用户尝试获取所有用户列表，来自 {client_address}。")
                            continue
                        all_users = self.db_manager.get_all_users_info()
                        self._send_response(client_socket, "success", "所有用户已检索。", data={"users": all_users})
                        logger.info(f"SecureChatServer: 向 {logged_in_username} 提供了所有注册用户列表。")

                    else:
                        self._send_response(client_socket, "error", "未知命令。")
                        logger.warning(f"SecureChatServer: 收到来自 {client_address} 的未知命令: {command}")

                except json.JSONDecodeError:
                    self._send_response(client_socket, "error", "无效的JSON格式。")
                    logger.error(f"SecureChatServer: 收到来自 {client_address} 的无效JSON格式数据: {data}", exc_info=True)
                except Exception as e:
                    logger.error(f"SecureChatServer: 处理来自 {client_address} 的客户端请求时出错: {e}", exc_info=True)
                    self._send_response(client_socket, "error", f"服务器内部错误: {str(e)}")

        except Exception as e:
            logger.error(f"SecureChatServer: 客户端 {client_address} 处理程序发生错误: {e}", exc_info=True)
        finally:
            # 只有在用户ID不为None时才清除在线状态（避免重复清除）
            if logged_in_user_id is not None:
                # 客户端断开连接时清除在线状态
                self.db_manager.clear_online_status(logged_in_user_id)
                with self.session_lock:
                    if logged_in_user_id in self.online_sessions:
                        del self.online_sessions[logged_in_user_id]
                logger.info(f"SecureChatServer: 已清理用户 {logged_in_username} (ID: {logged_in_user_id}) 的会话并更新离线状态。")
            else:
                logger.debug(f"SecureChatServer: 客户端 {client_address} 断开连接，但用户已登出，无需清理在线状态。")
            try:
                client_socket.close()
            except socket.error as e:
                logger.warning(f"SecureChatServer: 关闭客户端socket {client_address} 时出错: {e}", exc_info=True)
            logger.info(f"SecureChatServer: 与 {client_address} 的连接已关闭。")