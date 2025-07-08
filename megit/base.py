from . import data
import os
from collections import deque,namedtuple
import itertools
import operator
import string

def write_tree(directory='.'): #saves as the directory in object database and returns the tree OID
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

def is_ignored(path):
    return os.path.normpath(path).startswith('.megit') 

def _empty_current_directory(): #as name suggests empties the current directory
#follows bottoms up - inner files first 
    for root, dirnames, filenames in os.walk('.', topdown=False):
        for filename in filenames:
            path = os.path.relpath(f'{root}/{filename}') 
            if is_ignored(path) or not os.path.isfile(path):
                continue
            os.remove(path) #delete the path
        for dirname in dirnames:
            path = os.path.relpath(f'{root}/{dirname}')
            if is_ignored(path):
                continue
            try:
                os.rmdir(path) #tries to delete the directory only works when directory empty
            except (FileNotFoundError, OSError):
                pass #except these errors we allow to pass caused by all files not deleted like .megit

def _iter_tree_entries(oid): #reads the content of the Tree object which is filenames in each line
    if not oid:
        return
    tree = data.get_object(oid, 'tree')
    for entry in tree.decode().splitlines():
        type_, oid, name = entry.split(' ',2)
        yield type_, oid, name #yield produces one at a time

def get_tree(oid, base_path=''): #returns a dictionary with path->oid
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

def read_tree(tree_oid): #restores the directory or version from Tree OID passed 
    _empty_current_directory()
    for path, oid in get_tree(tree_oid, base_path='./').items():  #the get_tree gives a dict of path->oid mappings for each file 
        os.makedirs (os.path.dirname(path),exist_ok=True) #we are making directories by extracting the directory name from relative path, exist ok prevents from raising error when same directory name occurs
        with open(path, 'wb') as f:
            f.write(data.get_object(oid)) #creates the file from its path and writes its content

def commit(message): #makes the commit object and returns its OID
    commit = f'tree {write_tree()}\n' #key value pair
    HEAD = data.get_ref('HEAD').value
    if HEAD:
        commit += f'parent {HEAD}\n' #adding the parent key to previous head
    commit += '\n'
    commit +=  f'{message}\n'
    oid = data.hash_object(commit.encode(), 'commit') 
    data.update_ref('HEAD',data.RefValue (symbolic=False, value=oid)) 
    return oid

Commit = namedtuple('Commit',['tree', 'parent', 'message']) #its like a shorter version of class

def get_commit(oid): #commit object OID is passed, Commit as a tuple is returned with message parent oid
    parent = None #the first commit does not have a parent so
    commit = data.get_object(oid, 'commit').decode()
    lines = iter(commit.splitlines()) #convert lines splitted into iterable
    for line in itertools.takewhile (operator.truth, lines): #iterate till empty line
        key, value = line.split(' ', 1)
        if key == 'tree':
            tree=value
        elif key == 'parent':
            parent = value
        else:
            raise ValueError(f'Unknown field {key}')

    message = '\n'.join (lines) 
    return Commit (tree=tree, parent=parent, message=message) 

def checkout (oid): #opens another version that version is our head now
    commit = get_commit (oid)
    read_tree (commit.tree)
    data.update_ref('HEAD',data.RefValue (symbolic=False, value=oid))

def create_tag (name, oid): #gives name to OID, creates a ref and stores in object database in the file the content is OID
    data.update_ref(f'refs/tags/{name}',data.RefValue (symbolic=False, value=oid))

def get_oid(name): #on passing the ref name it gives its OID
    if name == '@': name = 'HEAD'
    # Name is ref
    refs_to_try = [
        f'{name}',
        f'refs/{name}',
        f'refs/tags/{name}',
        f'refs/heads/{name}',
    ]
    for ref in refs_to_try:
        if data.get_ref (ref):
            return data.get_ref (ref).value
    # Name is SHA1
    is_hex = all (c in string.hexdigits for c in name)
    if len (name) == 40 and is_hex:
        return name
    raise ValueError(f'error: {name} is not a valid reference or object ID')

#
def iter_commits_and_parents(oids): #a set of oids is passed which refs points to
    oids = deque(oids)
    visited = set()
    while oids:
        oid = oids.popleft()
        if not oid or oid in visited:
            continue
        visited.add(oid)
        yield oid
        commit = get_commit(oid)
        oids.appendleft(commit.parent)

def create_branch (name, oid):
    data.update_ref (f'refs/heads/{name}', data.RefValue (symbolic=False, value=oid))

