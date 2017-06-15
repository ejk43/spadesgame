import time
import socket
import sys
import json

import argparse


HOST, PORT = "0.0.0.0", 9000

parser = argparse.ArgumentParser(description='Test Spades Client')
parser.add_argument('port', type=int, help="Port")
parser.add_argument("-n", "--name", type=str, default="EJ", help="Player Name")
parser.add_argument("-t", "--team", type=int, default=1, help="Team")
parser.add_argument("-i", '--ip', type=str, default=HOST, help="Host address, default: %s" % HOST)
(args) = parser.parse_args()
print "Got Args:", args

# Create a socket (SOCK_STREAM means a TCP socket)
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    # Connect to server and send data
    sock.connect((args.ip, args.port))
    # sock.sendall(data + "\n")

    # received = sock.recv(1024)
    # print "Received: {}".format(received)

    # time.sleep(2)


    # client_request = {'type' : 'request',
    #                  'request' : 'status'}
    # sock.sendall(json.dumps(client_request) + "\n")
    # received = sock.recv(1024)
    # print "Received: {}".format(received)


    # time.sleep(5)


    # sock.sendall("{hithisshouldfail" + "\n")
    # received = sock.recv(1024)
    # print "Received: {}".format(received)

    # time.sleep(5)

    client_init = {'type' : 'init', 
                   'id'   : args.name,
                   'team' : args.team}
    sock.sendall(json.dumps(client_init) + "\n")
    received = sock.recv(1024)
    print "Received: {}".format(received)

    raw_input()

    client_bid = {'type' : 'bid', 
                   'bid'   : 3}
    sock.sendall(json.dumps(client_bid) + "\n")
    received = sock.recv(1024)
    print "Received: {}".format(received)

    raw_input()

    # received = sock.recv(1024)
    # print "Received: {}".format(received)

finally:
    sock.close()

