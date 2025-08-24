#serves as disk
import os #standard module it provides functions to interact with the underlying operating system in a portable way
import hashlib # built‑in library for cryptographic hashes.
import shutil
import json 

from collections import namedtuple
from contextlib import contextmanager

GIT_DIR = None #the directory name which is made to store all repo data locally 

@contextmanager
def change_git_dir (new_dir):
    global GIT_DIR
    old_dir = GIT_DIR
    GIT_DIR = f'{new_dir}/.megit'
    yield
    GIT_DIR = old_dir #restoring

def init(): #makes our .megit and objects directory for storage the object database
    os.makedirs (GIT_DIR) #command to make a directory 
    os.makedirs (f'{GIT_DIR}/objects')
    
RefValue = namedtuple('RefValue', ['symbolic', 'value'])
    
#Updates or creates a reference file with the given OID (or symbolic value).
def update_ref (ref, value, deref=True): #ref:name value:named tuple
    ref = _get_ref_internal(ref, deref)[0] #eturns (ref_path, RefValue) — we only want ref_path.
    assert value.value
    if value.symbolic:
        value = f'ref: {value.value}'
    else:
        value = value.value

    ref_path = f'{GIT_DIR}/{ref}'
    os.makedirs (os.path.dirname(ref_path), exist_ok = True)
    with open (ref_path, 'w') as f:
        f.write (value) 

def get_ref (ref, deref=True):  #returns the oid to the reference name passed
    return _get_ref_internal (ref, deref)[1] #value

def delete_ref (ref, deref=True):
    ref = _get_ref_internal (ref, deref)[0]
    os.remove (f'{GIT_DIR}/{ref}')

#Returns the actual reference path and a RefValue namedtuple
def _get_ref_internal (ref,deref):
    ref_path = f'{GIT_DIR}/{ref}'
    value = None
    if os.path.isfile(ref_path):
        with open (ref_path) as f:
            value =  f.read().strip() #either oid or symbolic ref which points to another ref: refs/heads/main
    symbolic = bool (value) and value.startswith ('ref:')
    if symbolic:
        value = value.split (':', 1)[1].strip ()
        if deref:
            return _get_ref_internal (value, deref=True)
    return ref, RefValue (symbolic=symbolic, value=value)
        
#Iterates over all refs in the repository, yielding each one with its value.
def iter_refs (prefix='', deref=True): 
    refs = ['HEAD', 'MERGE_HEAD']
    for root, _, filenames in os.walk(f'{GIT_DIR}/refs/'):
        root = os.path.relpath(root, GIT_DIR) #os.path.relpath('/a/b/c/d', '/a/b')  →  'c/d'
        refs.extend(f'{root}/{name}' for name in filenames)
    for refname in refs:
        if not refname.startswith(prefix):#skip all refs which not match the prefix(filter)
            continue
        ref = get_ref (refname, deref=deref)
        if ref.value:
            yield refname, ref

@contextmanager
def get_index ():
    index = {}
    if os.path.isfile (f'{GIT_DIR}/index'):
        with open (f'{GIT_DIR}/index') as f:
            index = json.load (f)

    yield index

    with open (f'{GIT_DIR}/index', 'w') as f:
        json.dump (index, f)

def hash_object(data, type_='blob'): #hashes the file name or dir it uses the sha1 hash this is the name by which we store so that it is unique
    obj = type_.encode()+b'\x00'+data
    oid = hashlib.sha1(obj).hexdigest() #coverts to hash then to hexdecimal string
    with open(f'{GIT_DIR}/objects/{oid}','wb') as out: #binary mode open file or create file to this path (it creates the file with oid in .megit/objects)
        out.write(obj)
    return oid 
    #after opening close closed itself to prevent leaks

def get_object(oid, expected='blob'): #gives the file contents by passing its oid
    with open (f'{GIT_DIR}/objects/{oid}', 'rb') as f:
        obj = f.read() 
        type_, _ , content = obj.partition(b'\x00')
        type_ = type_.decode()
        if expected is not None:
            assert type_==expected, f'expected {expected} got {type_}'
        return content 

def object_exists (oid):
    return os.path.isfile (f'{GIT_DIR}/objects/{oid}')

def fetch_object_if_missing (oid, remote_git_dir):
    if object_exists (oid):
        return
    remote_git_dir += '/.megit'
    shutil.copy (f'{remote_git_dir}/objects/{oid}',
                 f'{GIT_DIR}/objects/{oid}')
    
def push_object (oid, remote_git_dir):
    remote_git_dir += '/.megit'
    shutil.copy (f'{GIT_DIR}/objects/{oid}',
                 f'{remote_git_dir}/objects/{oid}')