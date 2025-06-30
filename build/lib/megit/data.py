#serves as disk
import os #standard module it provides functions to interact with the underlying operating system in a portable way
import hashlib # built‑in library for cryptographic hashes.

GIT_DIR = '.megit' #the directory name which is made to store all repo data locally 

def init():
    os.makedirs (GIT_DIR) #command to make a directory 
    os.makedirs (f'{GIT_DIR}/objects')

def hash_object(data, type_='blob'):
    obj = type_.encode()+b'\x00'+data
    oid = hashlib.sha1(obj).hexdigest() #coverts to hash then to hexdecimal string
    with open(f'{GIT_DIR}/objects/{oid}','wb') as out: #binary mode open file or create file to this path (it creates the file with oid in .megit/objects)
        out.write(obj)
    return oid 
    #after opening close closed itself to prevent leaks

def get_object(oid, expected='blob'):
    with open (f'{GIT_DIR}/objects/{oid}', 'rb') as f:
        obj = f.read() 
        type_, _ , content = obj.partition(b'\x00')
        type_ = type_.decode()
        if expected:
            assert type_==expected, f'expected {expected} got {type_}'
        return content 