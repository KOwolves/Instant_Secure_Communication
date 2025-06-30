import hashlib

def hash_test(sstr):
	h = hashlib.md5()
	h.update(sstr.encode("utf-8"))
	sstr_MD5 = h.hexdigest()

	return sstr_MD5
