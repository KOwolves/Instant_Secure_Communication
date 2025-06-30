from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import rsa
data = b'hellohowru' #转为bytes
# 读取标准的rsa公私钥pem文件
print(data)
'''
def load_rsa_file(fn):
    key = None
    try:
        key = RSA.importKey(open(fn).read())
    except Exception as err:
        print('导入rsa的KEY文件出错', fn, err)
    return key
# 标准字符串密钥转rsa格式密钥
def rsa_key_str2std(skey):
    ret = None
    try:
        ret = RSA.importKey(skey)
    except Exception as err:
        print('字符串密钥转rsa格式密钥错误', skey, err)
    return ret
def exp_mode(base, exponent, n):
  bin_array = bin(exponent)[2:][::-1]
  r = len(bin_array)
  base_array = []
  pre_base = base
  base_array.append(pre_base)
  for _ in range(r - 1):
    next_base = (pre_base * pre_base) % n
    base_array.append(next_base)
    pre_base = next_base
  a_w_b = __multi(base_array, bin_array)
  return a_w_b % n
def __multi(array, bin_array):
  result = 1
  for index in range(len(array)):
    a = array[index]
    if not int(bin_array[index]):
      continue
    result *= a
  return result
def encrypt(m, pubkey):
  n = pubkey[0]
  e = pubkey[1]
  c = exp_mode(m, e, n)
  return c
def decrypt(c, selfkey):
  n = selfkey[0]
  d = selfkey[1]
  m = exp_mode(c, d, n)
  return m
if __name__ == '__main__':
    file = open("private.pem")
    line = file.readline()
    private
    while 1:
        line = file.readline()
        if line = "-----END RSA PRIVATE KEY-----":
            break
        if not line:
            break
        pass  # do something
    file.close()
'''


def encrypt(chatkey,itspublic_key):  # 用公钥加密
    pubkey = rsa.PublicKey.load_pkcs1(itspublic_key)
    original_text = chatkey.encode('utf-8')
    crypt_text = rsa.encrypt(original_text, pubkey)
    print(crypt_text)
    return crypt_text  # 加密后的密文


def decrypt(myId,crypt_text):  # 用私钥解密
    with open(myId + '_private.pem', 'rb') as privatefile:
        p = privatefile.read()
    print(type(p))
    privkey = rsa.PrivateKey.load_pkcs1(p)
    print(type(privkey))
    print(type(crypt_text))
    if type(crypt_text) == 'bytes':
        lase_text = rsa.decrypt(crypt_text, privkey).decode()  # 注意，这里如果结果是bytes类型，就需要进行decode()转化为str
    else:
        lase_text = rsa.decrypt(crypt_text, privkey)
    #print(lase_text)
    return lase_text


if __name__ == '__main__':
    pass
    #crypt_text = encrypt()
    #lase_text = decrypt(crypt_text)
    #decrypt(lase_text)
