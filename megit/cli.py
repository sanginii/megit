import argparse  #Imports the built-in module for parsing command-line arguments
import os #performs operations from underlying operating system 
import sys #the bridge between your Python code and the running Python process itself.
from . import base #. means same folder
from . import data 
import subprocess #Used to run external commands from within Python. eg subprocess.run(["ls", "-l"]) runs the command ls -l
import platform #Used to get information about the system your script is running on (OS, architecture, etc). #Helpful if your program needs to behave differently on Linux vs Windows
import textwrap #for indentation 

def main():
    args = parse_args() #whatever is written in terminal is passed to args
    args.func(args) #what ever is returned above eg init that function is called 

def parse_args():
    parser = argparse.ArgumentParser() #main top level like megit
    commands = parser.add_subparsers(dest='command') #parser says it will be subparsers subcommands whose name will be stored in args.command
    commands.required = True #a subcommand is necesaary

    oid = base.get_oid #(assigning function to oid) so whenever we do oid("name") it gives us the oid

    init_parser = commands.add_parser('init')
    init_parser.set_defaults(func=init) # If “init” is used, attach your init() function

    hash_object_parser = commands.add_parser("hash-object")
    hash_object_parser.set_defaults(func=hash_object)
    hash_object_parser.add_argument('file') 
    hash_object_parser.add_argument(
    '-t', '--type',
    default='blob',
    help="Object type (default: blob)"
    )

    cat_file_parser = commands.add_parser('cat-file')
    cat_file_parser.set_defaults(func=cat_file)
    cat_file_parser.add_argument('object', type=oid) 

    write_tree_parser = commands.add_parser('write-tree')
    write_tree_parser.set_defaults(func=write_tree) 
    write_tree_parser.add_argument( 
        'directory',
       nargs='?', #number of arguments
       default='.', #use current directory
       help='Root directory to write tree from (default: current directory)',
   ) 

    read_tree_parser = commands.add_parser('read-tree')
    read_tree_parser.set_defaults(func=read_tree)
    read_tree_parser.add_argument('tree',type=oid)

    commit_parser = commands.add_parser('commit')
    commit_parser.set_defaults(func=commit)
    commit_parser.add_argument('-m', '--message', required=True)

    log_parser = commands.add_parser('log')
    log_parser.set_defaults(func=log)
    log_parser.add_argument ('oid',default='@', type=oid, nargs='?')

    checkout_parser = commands.add_parser ('checkout')
    checkout_parser.set_defaults (func=checkout)
    checkout_parser.add_argument ('commit')

    tag_parser = commands.add_parser ('tag')
    tag_parser.set_defaults (func=tag)
    tag_parser.add_argument ('name')
    tag_parser.add_argument ('oid',default='@', type=oid, nargs='?') #@ means HEAD

    k_parser = commands.add_parser('k')
    k_parser.set_defaults(func=k)

    branch_parser = commands.add_parser ('branch')
    branch_parser.set_defaults (func=branch)
    branch_parser.add_argument ('name', nargs='?')
    branch_parser.add_argument ('start_point', default='@', type=oid, nargs='?') #It's the commit or ref where the new branch should begin. by default its head

    status_parser = commands.add_parser('status')
    status_parser.set_defaults (func=status)

    return parser.parse_args() #calls argparse’s method, not this function 


def init(args):
    base.init()
    print (f'Initialized empty megit repository in {os.getcwd()}/{data.GIT_DIR}') #current working directory.

def hash_object(args): #type ?
    with open (args.file, 'rb') as f: 
        print (data.hash_object(f.read(), type_=args.type)) #reads the file bytess 
        #the oid is returned and printed 

def cat_file(args):
    sys.stdout.flush () # It writes them out.
    sys.stdout.buffer.write (data.get_object(args.object, expected=None)) #writes to the termical 

def write_tree(args):
    print (base.write_tree())

def read_tree(args):
    base.read_tree(args.tree) 

def commit(args):
    print(base.commit(args.message)) 

def log(args):
    refs = {} #commit: refs/tags
    for refname, ref in data.iter_refs():
        refs.setdefault(ref.value, []).append(refname) #For the ref.value (which is usually a commit OID), if we haven't seen it yet, initialize an empty list for it. Then, add refname to that list.
    for oid in base.iter_commits_and_parents({args.oid}):
        commit = base.get_commit(oid) #we get a tuple which has message parent
        refs_str=f'({", ".join(refs[oid])})' if oid in refs else ''
        print(f'commit {oid} {refs_str}\n') 
        print(textwrap.indent(commit.message,'   ')) 
        print('')

def checkout (args):
    base.checkout (args.commit)

def tag (args):
    base.create_tag (args.name, args.oid) 

def k (args):
    dot = 'digraph commits {\n'
    oids = set ()
    for refname, ref in data.iter_refs (deref=False):
        dot+=f'"{refname}" [shape=note]\n' #A node for each ref (main, HEAD, tags)
        dot+=f'"{refname}" -> "{ref.value}"\n' #An edge from the ref to the commit it points to
        if not ref.symbolic:
            oids.add (ref.value)
    for oid in base.iter_commits_and_parents(oids):
        commit = base.get_commit(oid)
        dot+=f'"{oid}" [shape=box style=filled label="{oid[:10]}"]\n'
        if commit.parent:
            dot += f'"{oid}" -> "{commit.parent}"\n'
    dot += '}'

   # Write to dot file
    with open("graph.dot", "w") as f:
        f.write(dot)

    # Generate PNG using Graphviz
    subprocess.run(["dot", "-Tpng", "graph.dot", "-o", "graph.png"])

    # Open image in default viewer based on OS
    system = platform.system()

    try:
        if system == "Windows":
            os.startfile("graph.png")  # Windows native
        elif system == "Darwin":
            subprocess.run(["open", "graph.png"])  # macOS
        elif system == "Linux":
            subprocess.run(["xdg-open", "graph.png"])  # Linux desktop
        else:
            print("Graph generated: graph.png (please open it manually)")
    except Exception as e:
        print(f"Could not open image: {e}")

def branch (args):
    if not args.name: #no name is passed print all branches
        current = base.get_branch_name()
        for branch in base.iter_branch_names():
            prefix='*' if branch == current else ' '
            print (f'{prefix}{branch}')
    else:
        base.create_branch (args.name, args.start_point)
        print (f'Branch {args.name} created at {args.start_point[:10]}')

def status(args):
    HEAD = base.get_oid('@')
    branch = base.get_branch_name()
    if branch:
        print (f'On branch {branch}')
    else:
        print(f'HEAD detached at {HEAD[:10]}') #first 10 characters out of 40
