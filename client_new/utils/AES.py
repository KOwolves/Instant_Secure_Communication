import os
import logging
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidTag

logger = logging.getLogger(__name__)


class AESUtils:
    """
    专门处理所有 AES 对称加密相关的操作：
    - 使用 AES 对消息进行加密（GCM 模式）。
    - 使用 AES 对消息进行解密。
    """

    def __init__(self):
        pass

    def encrypt_message(self, message_bytes, symmetric_key_bytes):
        """使用AES对称密钥加密消息（GCM模式）。"""
        try:
            nonce = os.urandom(12)  # AES GCM 需要一个唯一的 nonce (IV)，长度为12字节
            cipher = Cipher(algorithms.AES(symmetric_key_bytes), modes.GCM(nonce), backend=default_backend())
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(message_bytes) + encryptor.finalize()
            tag = encryptor.tag  # 认证标签
            logger.debug("AESUtils: 消息已使用AES对称密钥加密。")
            return ciphertext, nonce, tag
        except Exception as e:
            logger.error(f"AESUtils: AES加密消息时出错: {e}", exc_info=True)
            return None, None, None

    def decrypt_message(self, ciphertext_bytes, nonce_bytes, tag_bytes, symmetric_key_bytes):
        """使用AES对称密钥解密消息（GCM模式）。"""
        try:
            cipher = Cipher(algorithms.AES(symmetric_key_bytes), modes.GCM(nonce_bytes, tag_bytes),
                            backend=default_backend())
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext_bytes) + decryptor.finalize()
            logger.debug("AESUtils: 消息已使用AES对称密钥解密。")
            return plaintext
        except InvalidTag:
            logger.error("AESUtils: AES解密失败: 认证标签无效，消息可能被篡改。")
            return None
        except Exception as e:
            logger.error(f"AESUtils: AES解密消息时出错: {e}", exc_info=True)
            return None
