from random import choice
import string
import rsa
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA as rsa
# 生成随机密钥的子函数


def GenPassword(length=8,chars=string.ascii_letters+string.digits):
    return ''.join([choice(chars) for i in range(length)])
# 申请会话的一方加密随机选择的会话密钥并且发给另外一方

#返回一个16字节的会话密钥
def send_key():   # 返回字节类型
    '''
    rsa_key=RSA.load_rsa_file("public.pem")
    encrypt_key = b''
    for data in RSA.block_data(GenPassword(16), rsa_key):
        encrypt_key = encrypt_key + RSA.rsa_enc(data.encode(), rsa_key)
    return encrypt_key
    '''
    print(type(GenPassword(16)))
    return GenPassword(16)

if __name__ == '__main__':
    send_key()




