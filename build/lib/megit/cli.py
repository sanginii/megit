#whole command line logic goes here

import argparse  #Imports the built-in module for parsing command-line arguments
import os 
import sys #the bridge between your Python code and the running Python process itself.
from . import base
from . import data #from same folder 

def main():
    args = parse_args() #whatever is written in terminal is passed to args
    args.func(args) #what ever is returned above eg init that function is called 
    #almost like init.funct(args)

def parse_args():
    parser = argparse.ArgumentParser() #main top level like megit
    commands = parser.add_subparsers(dest='command') #parser says it will be subparsers subcommands whose name will be stored in args.command
    commands.required = True #a subcommand is necesaary

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
    cat_file_parser.add_argument('object')

    write_tree_parser = commands.add_parser('write-tree')
    write_tree_parser.set_defaults(func=write_tree) 
    write_tree_parser.add_argument( 
        'directory',
       nargs='?',
       default='.',
       help='Root directory to write tree from (default: current directory)',
   )

    read_tree_parser = commands.add_parser('read-tree')
    read_tree_parser.set_defaults(func=read_tree)
    read_tree_parser.add_argument('tree')

    return parser.parse_args() #calls argparse’s method, not this function 

def init(args):
    data.init()
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