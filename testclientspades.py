import time
import socket
import sys
import json

HOST, PORT = "localhost", 9000
data = " ".join(sys.argv[1:])

# Create a socket (SOCK_STREAM means a TCP socket)
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    # Connect to server and send data
    sock.connect((HOST, PORT))
    # sock.sendall(data + "\n")

    # received = sock.recv(1024)
    # print "Received: {}".format(received)

    time.sleep(5)


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

    # client_init = {'type' : 'init', 
    #                'id'   : 'EJ',
    #                'partner' : ''}
    # sock.sendall(json.dumps(client_init) + "\n")
    # received = sock.recv(1024)
    # print "Received: {}".format(received)

    # time.sleep(5)

    # received = sock.recv(1024)
    # print "Received: {}".format(received)

finally:
    sock.close()

