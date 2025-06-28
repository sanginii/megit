import os #standard module it provides functions to interact with the underlying operating system in a portable way
import hashlib # built‑in library for cryptographic hashes.

GIT_DIR = '.megit' #the directory name which is made to store all repo data locally 
def init():
    os.makedirs (GIT_DIR) #command to make a directory 
    os.makedirs (f'{GIT_DIR}/objects')

def hash_object(data):
    oid = hashlib.sha1(data).hexdigest() #coverts to hash then to hexdecimal string
    with open(f'{GIT_DIR}/objects/{oid}','wb') as out: #binary mode open file or create file to this path
        out.write(data)
    return oid 
    #after opening close closed itself to prevent leaks