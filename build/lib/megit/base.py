from . import data
import os

def write_tree(directory='.'):
    entries = [] 
    with os.scandir(directory) as it:
        for entry in it: #entry is my file
            full = os.path.join(directory, entry.name) #file path 
            if is_ignored(full): 
                continue
            if entry.is_file(follow_symlinks=False):
                #saves all the files in .megit/objects directory
                type_='blob'
                with open(full,'rb') as f: #full is already path no need to f'' this is done when file path create
                    oid = data.hash_object(f.read())
            elif entry.is_dir(follow_symlinks=False):
                type_='tree'
                oid = write_tree(full) 
            entries.append((entry.name,oid,type_)) #appending all files
    tree = ''.join(f'{type_} {oid} {name}\n' for name, oid, type_ in sorted (entries)) 
    return data.hash_object(tree.encode(),'tree') 

def _iter_tree_entries(oid):
    if not oid:
        return
    tree = data.get_object(oid, 'tree')
    for entry in tree.decode().splitlines():
        type_, oid, name = entry.split(' ',2)
        yield type_, oid, name #yield produces one at a time

def get_tree(oid, base_path=''):
    result = {}
    for type_, oid, name in _iter_tree_entries(oid):
        #security checks
        assert '/' not in name #file name should not have /
        assert name not in ('..', '.') #the name is not the parent or the current working directory 
        path = base_path+name #full relative path incase of recurssion base_path will be directorys name
        if type_=='blob':
            result[path]=oid
        elif type_=='tree':
            result.update (get_tree(oid, f'{path}/'))
        else:
            assert False, f'Unknown Tree entry {type_}'
    return result

def read_tree(tree_oid):
    for path, oid in get_tree(tree_oid, base_path='./').items():  #the get_tree gives a dict of path->oid mappings for each file 
        os.makedirs (os.path.dirname(path),exist_ok=True) #we are making directories by extracting the directory name from relative path, exist ok prevents from raising error when same directory name occurs
        with open(path, 'wb') as f:
            f.write(data.get_object(oid)) #creates the file from its path and writes its content


def is_ignored(path):
    return os.path.normpath(path).startswith('.megit')