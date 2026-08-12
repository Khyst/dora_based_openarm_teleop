from os import remove, removexattr
import subprocess as sp
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("remote_jpg")
parser.add_argument("local_jpg")
args = parser.parse_args()

sp.Popen(['feh', '--auto-reload', '--auto-zoom','--scale-down', args.local_jpg])
while True:
    sp.run(['scp', '-q', args.remote_jpg, args.local_jpg])
