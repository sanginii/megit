#whole command line logic goes here

import argparse  #Imports the built-in module for parsing command-line arguments
import os 
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

    hash_object_parser = commands.add_parser("hash_object")
    hash_object_parser.set_defaults(func=hash_object)
    hash_object_parser.add_argument('file')

    return parser.parse_args() #calls argparse’s method, not this function 

def init(args):
    data.init()
    print (f'Initialized empty megit repository in {os.getcwd()}/{data.GIT_DIR}') #current working directory.

def hash_object(args):
    with open (args.file, 'rb') as f: 
        print (data.hash_object(f.read())) #reads the file bytess 
        #the oid is returned and printed 
