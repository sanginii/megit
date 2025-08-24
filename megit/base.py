import os
import itertools #iterating
import operator #Contains function versions of common operators (+, ==) eg operator.add(2, 3) # 5
import string #for string functions 

from collections import deque,namedtuple

from . import data
from . import diff

def init():
    data.init()
    data.update_ref('HEAD', data.RefValue(symbolic=True, value='refs/heads/main')) 

#saves as the directory in object database and returns the tree OID
def write_tree ():
    # Index is flat, we need it as a tree of dicts
    index_as_tree = {}
    with data.get_index () as index:
        for path, oid in index.items ():
            path = path.split ('/')
            dirpath, filename = path[:-1], path[-1]

            current = index_as_tree
            # Find the dict for the directory of this file
            for dirname in dirpath:
                current = current.setdefault (dirname, {})
            current[filename] = oid

    def write_tree_recursive (tree_dict):
        entries = []
        for name, value in tree_dict.items ():
            if type (value) is dict:
                type_ = 'tree'
                oid = write_tree_recursive (value)
            else:
                type_ = 'blob'
                oid = value
            entries.append ((name, oid, type_))

        tree = ''.join (f'{type_} {oid} {name}\n'
                        for name, oid, type_
                        in sorted (entries))
        return data.hash_object (tree.encode (), 'tree')

    return write_tree_recursive (index_as_tree)

#reads the content of the Tree object which is filenames in each line
def _iter_tree_entries(oid): 
    if not oid:
        return
    tree = data.get_object(oid, 'tree')
    for entry in tree.decode().splitlines():
        type_, oid, name = entry.split(' ',2)
        yield type_, oid, name #yield produces one at a time

#returns a dictionary with path->oid
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

def get_working_tree ():
    result = {}
    for root, _, filenames in os.walk ('.'):
        for filename in filenames:
            path = os.path.relpath (f'{root}/{filename}')
            if is_ignored (path) or not os.path.isfile (path):
                continue
            with open (path, 'rb') as f:
                result[path] = data.hash_object (f.read ())
    return result

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

#restores the directory or version from Tree OID passed 
def read_tree(tree_oid): 
    _empty_current_directory()
    for path, oid in get_tree(tree_oid, base_path='./').items():  #the get_tree gives a dict of path->oid mappings for each file 
        os.makedirs (os.path.dirname(path),exist_ok=True) #we are making directories by extracting the directory name from relative path, exist ok prevents from raising error when same directory name occurs
        with open(path, 'wb') as f:
            f.write(data.get_object(oid)) #creates the file from its path and writes its content

def read_tree_merged (t_base, t_HEAD, t_other):
    _empty_current_directory ()
    for path, blob in diff.merge_trees (get_tree (t_base), get_tree (t_HEAD), get_tree (t_other)).items ():
        os.makedirs (f'./{os.path.dirname (path)}', exist_ok=True)
        with open (path, 'wb') as f:
            f.write (blob) 

#makes the commit object and returns its OID
def commit(message): 
    commit = f'tree {write_tree()}\n' #key value pair
    HEAD = data.get_ref('HEAD').value
    if HEAD:
        commit += f'parent {HEAD}\n' #adding the parent key to previous head
    MERGE_HEAD = data.get_ref ('MERGE_HEAD').value
    if MERGE_HEAD:
        commit += f'parent {MERGE_HEAD}\n'
        data.delete_ref ('MERGE_HEAD', deref=False) 
    commit += '\n'
    commit +=  f'{message}\n'
    oid = data.hash_object(commit.encode(), 'commit') 
    data.update_ref('HEAD',data.RefValue (symbolic=False, value=oid)) 
    return oid

#opens another version that version is our head now
def checkout (name): 
    oid = get_oid (name)
    commit = get_commit (oid)
    read_tree (commit.tree)

    if is_branch(name):
        HEAD = data.RefValue (symbolic=True, value=f'refs/heads/{name}')#points to the branch
    else:
        HEAD = data.RefValue (symbolic=False, value=oid)

    data.update_ref ('HEAD', HEAD, deref=False) 

def reset (oid):
    data.update_ref ('HEAD', data.RefValue (symbolic=False, value=oid))

def merge (other):
    HEAD = data.get_ref ('HEAD').value
    assert HEAD
    merge_base = get_merge_base (other, HEAD)
    c_other = get_commit (other)

    # Handle fast-forward merge
    if merge_base == HEAD:
        read_tree (c_other.tree)
        data.update_ref ('HEAD',
                         data.RefValue (symbolic=False, value=other))
        print ('Fast-forward merge, no need to commit')
        return

    data.update_ref ('MERGE_HEAD', data.RefValue (symbolic=False, value=other))

    c_base = get_commit (merge_base)
    c_HEAD = get_commit (HEAD)
    read_tree_merged (c_base.tree, c_HEAD.tree, c_other.tree)
    print ('Merged in working tree\nPlease commit')

def get_merge_base (oid1, oid2):
    parents1 = set (iter_commits_and_parents ({oid1}))
    for oid in iter_commits_and_parents ({oid2}):
        if oid in parents1:
            return oid
  
def is_ancestor_of (commit, maybe_ancestor):
    return maybe_ancestor in iter_commits_and_parents ({commit}) 

#gives name to OID, creates a ref and stores in object database, in the file the content is OID
def create_tag (name, oid): 
    data.update_ref(f'refs/tags/{name}',data.RefValue(symbolic=False, value=oid))

#creates a branch by name
def create_branch(name, oid):
    data.update_ref(f'refs/heads/{name}', data.RefValue(symbolic=False, value=oid)) #tuple is passed in value

def iter_branch_names():
    for refname,_ in data.iter_refs('refs/heads/'):
        yield os.path.relpath(refname, 'refs/heads/') 

def is_branch (branch):
    return data.get_ref(f'refs/heads/{branch}').value is not None 
     
def get_branch_name():
    HEAD = data.get_ref('HEAD', deref=False)
    if not HEAD.symbolic:
        return None
    HEAD=HEAD.value
    assert HEAD.startswith('refs/heads/')
    return os.path.relpath(HEAD, 'refs/heads')   

Commit = namedtuple('Commit',['tree', 'parents', 'message']) #its like a shorter version of class

#commit object OID is passed, Commit as a tuple is returned with (message, parent, oid)
def get_commit(oid):
    parents = [] #the first commit does not have a parent so
    commit = data.get_object(oid, 'commit').decode()
    lines = iter(commit.splitlines()) #convert lines splitted into iterable
    for line in itertools.takewhile (operator.truth, lines): #iterate till empty line
        key, value = line.split(' ', 1)
        if key == 'tree':
            tree=value
        elif key == 'parent':
            parents.append(value)
        else:
            raise ValueError(f'Unknown field {key}')

    message = '\n'.join (lines) 
    return Commit (tree=tree, parents=parents, message=message) 

#for git log - walks through a commit history
#prev commit is parent
def iter_commits_and_parents(oids): #HEAD is passed as [HEAD] then refs added
    oids = deque(oids)
    visited = set()
    while oids:
        oid = oids.popleft()
        if not oid or oid in visited:
            continue
        visited.add(oid)
        yield oid
        commit = get_commit(oid)
        # Return first parent next
        oids.extendleft (commit.parents[:1])
        # Return other parents later
        oids.extend (commit.parents[1:])

def iter_objects_in_commits (oids):
    # N.B. Must yield the oid before acccessing it (to allow caller to fetch it
    # if needed)
    visited = set ()
    def iter_objects_in_tree (oid):
        visited.add (oid)
        yield oid
        for type_, oid, _ in _iter_tree_entries (oid):
            if oid not in visited:
                if type_ == 'tree':
                    yield from iter_objects_in_tree (oid)
                else:
                    visited.add (oid)
                    yield oid
    for oid in iter_commits_and_parents (oids):
        yield oid
        commit = get_commit (oid)
        if commit.tree not in visited:
            yield from iter_objects_in_tree (commit.tree)

#on passing the ref name it gives its OID
def get_oid(name): 
    if name == '@':
        name = 'HEAD'

    refs_to_try = [
        f'{name}',                      # HEAD, main
        f'refs/{name}',                # refs/main
        f'refs/tags/{name}',           # refs/tags/<name>
        f'refs/heads/{name}',          # local branches
        f'refs/remote/{name}',         # remote branches (your custom setup)
    ]

    for ref in refs_to_try:
        ref_val = data.get_ref(ref, deref=False)
        if ref_val and ref_val.value:
            return ref_val.value

    # Name is a raw SHA1
    is_hex = all(c in string.hexdigits for c in name)
    if len(name) == 40 and is_hex:
        return name

    raise ValueError(f'error: {name} is not a valid reference or object ID')


def add (filenames):

    def add_file (filename):
        # Normalize path
        filename = os.path.relpath (filename)
        with open (filename, 'rb') as f:
            oid = data.hash_object (f.read ())
        index[filename] = oid

    def add_directory (dirname):
        for root, _, filenames in os.walk (dirname):
            for filename in filenames:
                # Normalize path
                path = os.path.relpath (f'{root}/{filename}')
                if is_ignored (path) or not os.path.isfile (path):
                    continue
                add_file (path)

    with data.get_index () as index:
        for name in filenames:
            if os.path.isfile (name):
                add_file (name)
            elif os.path.isdir (name):
                add_directory (name)

def is_ignored(path):
    return os.path.normpath(path).startswith('.megit') 