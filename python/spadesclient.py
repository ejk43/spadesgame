import time
import socket
import sys
import json
import readline
import cmd
import threading
import sys
# import curses
import argparse

RED   = "\033[1;31m"  
BLUE  = "\033[1;34m"
CYAN  = "\033[1;36m"
GREEN = "\033[0;32m"
RESET = "\033[0;0m"
BOLD    = "\033[;1m"
REVERSE = "\033[;7m"

HOST, PORT = "0.0.0.0", 9000

shutdown = False

def rx_loop(sock, CmdPrompt):
    global shutdown
    leftover = ''
    while not shutdown:
        try:
            rcv = leftover + sock.recv(1024)
        except socket.timeout:
            continue
        words = rcv.split('\n')
        for raw in words[:-1]:
            parsed = json.loads(raw)
            # print("\n\n"+str(parsed))
            print("\n\n"+raw)
        CmdPrompt.newprompt()
        leftover = words[-1]
        words = []
    pass

class SpadesClient(cmd.Cmd):

    def __init__(self, name, sock):
        self.intro = 'Welcome to the Spades Client, '+name+'\n\nType help or ? to list commands.\n'
        self.prompt = RED+'(%s) >> '%name+RESET
        self.sock = sock
        cmd.Cmd.__init__(self)

    def newprompt(self):
        sys.stdout.write("\n"+self.prompt)
        sys.stdout.flush()

    def do_bid(self, bid):
        "\nPlace your bid\n"
        try:
            bidint = int(bid)
        except:
            print("Error bid %s is invalid" % str(bid))
            return

        print("Bidding: "+str(bid))

        client_bid = {'type' : 'bid',
                       'bid' : int(bid)}
        self.sock.sendall(json.dumps(client_bid) + "\n")

    def do_play(self, card):
        "\nPlay a card\n"
        print("Playing: %s" % str(card))
        client_card = {'type' : 'card',
                       'card' : card}
        self.sock.sendall(json.dumps(client_card) + "\n")

    def do_add(self, arg):
        "\nAdding a new player\n"
        print("Adding Player")
        client_add = {'type' : 'add'}
        self.sock.sendall(json.dumps(client_add) + "\n")

    def do_kill(self, name):
        "\nRemove a machine player\n"
        print("Removing Player")
        client_add = {'type' : 'kill', 
                      'name': name}
        self.sock.sendall(json.dumps(client_add) + "\n")

    def do_quit(self, arg):
        "\nQuit the Game\n"
        print('\nThank you for playing\n')
        global shutdown
        shutdown = True
        return True

    def do_exit(self, arg):
        "\nQuit the Game\n"
        return self.do_quit(arg)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Spades Command-Line Client')
    parser.add_argument('port', type=int, help="Port")
    parser.add_argument("-n", "--name", type=str, default="EJ", help="Player Name [default: %s]" % "EJ")
    parser.add_argument("-t", "--team", type=int, default=1, help="Team [default: %i]" % 1)
    parser.add_argument("-i", '--ip', type=str, default=HOST, help="Host address [default: %s]" % HOST)
    (args) = parser.parse_args()
    # print "Got Args:", args

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Start the socket
        sock.connect((args.ip, args.port))

        # Initialize with player & team name
        client_init = {'type' : 'init',
                       'id'   : args.name,
                       'team' : args.team}
        sock.sendall(json.dumps(client_init) + "\n")

        # Generate command prompt
        Prompt = SpadesClient(args.name, sock)

        # Start the rx thread
        sock.settimeout(0.2)
        rxthread = threading.Thread(target=rx_loop, args=[sock, Prompt])
        rxthread.start()

        # Start the command prompt
        Prompt.cmdloop()

    finally:
        sock.close()