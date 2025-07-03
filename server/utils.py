import hashlib


def hash_password(password):
    """
    hash格式存储密码。
    :param password: 密码明文
    :return: hash值
    """
    return hashlib.sha256(password.encode()).hexdigest()
