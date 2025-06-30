import os
import Crypto
import rsa

# 下面一个函数生成数字证书
def cert_create(userId):
        global signature
        result = os.path.exists(userId + '_private.pem')
        if result == False:
            # 生成密钥
            (pubkey, privkey) = rsa.newkeys(1024)
            # 保存密钥
            #with open(userId + '_public.pem', 'w+') as f:
            #    f.write(pubkey.save_pkcs1().decode())
            with open(userId + '_private.pem', 'w+') as f:
                f.write(privkey.save_pkcs1().decode())
            return pubkey.save_pkcs1()
        '''else:
            # 导入密钥
            with open('private.pem', 'r') as f:
                privkey = rsa.PrivateKey.load_pkcs1(f.read().encode())
            # 私钥签名
            # print(type())
            signature = rsa.sign((cPubKey + Identity.encode()), privkey, 'SHA-1')'''
if __name__ == '__main__':
    key = cert_create('lyd')
    print(key)
    key = key.decode()
    #key = str(key)
    #print(type(key))
    #key = key.encode()
    #print(type(key))
    #key = key.save_pkcs1()
    print(type(key))
    print(key)
    #key = rsa.PublicKey.load_pkcs1(key.decode())
    #print(type(key))
    #print(key)