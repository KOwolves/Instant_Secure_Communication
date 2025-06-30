import logging
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class RSAUtils:
    """
    专门处理所有 RSA 非对称加密相关的操作：
    - RSA 密钥对的生成、加载和保存。
    - 使用 RSA 公钥加密对称密钥（用于密钥交换）。
    - 使用 RSA 私钥解密对称密钥。
    - 获取密钥的 PEM 格式字符串。
    """

    def __init__(self, private_key=None, public_key=None):
        self._private_key = private_key
        self._public_key = public_key

    def set_keys(self, private_key, public_key):
        """设置当前实例将使用的RSA私钥和公钥对象。"""
        self._private_key = private_key
        self._public_key = public_key
        logger.debug("RSAUtils: 已设置RSA密钥对象。")

    def generate_key_pair(self):
        """生成RSA密钥对。"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        logger.debug("RSAUtils: RSA密钥对已生成。")
        return private_key, public_key

    def save_key_pair(self, private_key, public_key, private_file, public_file):
        """保存RSA密钥对到PEM文件。"""
        try:
            with open(private_file, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            with open(public_file, "wb") as f:
                f.write(public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))
            logger.info(f"RSAUtils: RSA密钥对已保存到 {private_file} 和 {public_file}。")
            return True
        except Exception as e:
            logger.error(f"RSAUtils: 保存密钥对时出错: {e}", exc_info=True)
            return False

    def load_key_pair(self, private_file, public_file):
        """从PEM文件加载RSA密钥对。"""
        try:
            with open(private_file, "rb") as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            with open(public_file, "rb") as f:
                public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
            logger.info(f"RSAUtils: 已从文件 {private_file} 和 {public_file} 加载RSA密钥对。")
            self.set_keys(private_key, public_key)
            return private_key, public_key
        except FileNotFoundError:
            logger.warning("RSAUtils: 密钥文件未找到。")
            return None, None
        except Exception as e:
            logger.error(f"RSAUtils: 加载密钥对时出错: {e}", exc_info=True)
            return None, None

    def encrypt_symmetric_key(self, recipient_public_key_pem, symmetric_key_bytes):
        """使用接收方的RSA公钥加密对称密钥。"""
        try:
            recipient_public_key = serialization.load_pem_public_key(
                recipient_public_key_pem.encode('utf-8'),
                backend=default_backend()
            )
            encrypted_key = recipient_public_key.encrypt(
                symmetric_key_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            logger.debug("RSAUtils: 对称密钥已使用RSA公钥加密。")
            return encrypted_key
        except Exception as e:
            logger.error(f"RSAUtils: RSA加密对称密钥时出错: {e}", exc_info=True)
            return None

    def decrypt_symmetric_key(self, encrypted_symmetric_key_bytes):
        """使用自己的RSA私钥解密对称密钥。"""
        if not self._private_key:
            logger.error("RSAUtils: 私钥未加载，无法解密对称密钥。")
            return None
        try:
            symmetric_key = self._private_key.decrypt(
                encrypted_symmetric_key_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            logger.debug("RSAUtils: 对称密钥已使用RSA私钥解密。")
            return symmetric_key
        except Exception as e:
            logger.error(f"RSAUtils: RSA解密对称密钥时出错: {e}", exc_info=True)
            return None

    def get_public_key_pem(self, public_key_object):
        """将公钥对象转换为PEM格式字符串。"""
        if public_key_object:
            return public_key_object.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')
        return None

    def get_private_key_pem(self, private_key_object):
        """将私钥对象转换为PEM格式字符串 (慎用)。"""
        if private_key_object:
            return private_key_object.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')
        return None
