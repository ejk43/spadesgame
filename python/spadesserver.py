import SocketServer
import socket
import time
import threading
import logging
from Queue import Queue
from spadesgame import Game
from spadesplayer import Player, JsonPlayer, DumbPlayer
import json
import argparse

RED   = "\033[1;31m"  
BLUE  = "\033[1;34m"
CYAN  = "\033[1;36m"
GREEN = "\033[0;32m"
RESET = "\033[0;0m"
BOLD    = "\033[;1m"
REVERSE = "\033[;7m"

logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

# Temporary magic numbers
HOST, PORT = "0.0.0.0", 9000

class SpadesServer(SocketServer.ThreadingTCPServer):
    # Override to count number of connections: 
    # https://stackoverflow.com/questions/5370778/how-to-count-connected-clients-in-tcpserver

    def __init__(self, Game, *args, **kws):
        self._num_client = 0
        self.Game = Game
        SocketServer.ThreadingTCPServer.__init__(self, *args, **kws)

    def process_request(self, *args, **kws):
        # NOTE: If we want to limit connections, use this?...
        # if self._num_client < 1:
        self._num_client += 1
        SocketServer.ThreadingTCPServer.process_request(self, *args, **kws)

    def process_request_thread(self, *args, **kws):
        SocketServer.ThreadingTCPServer.process_request_thread(self, *args, **kws)
        self._num_client -= 1

    def get_client_number(self):
        return self._num_client
 
class SpadesRequestHandler(SocketServer.StreamRequestHandler):
    """
    Handles one connection to the client.
    Provides queues as data interfaces
    """
    def __init__(self, *args, **kws):
        print "New Handler"
        server = args[2]

        # Initialize
        self.txqueue = Queue()
        self.txthread = threading.Thread(target=self.txloop)
        self.txthread.start()
        self.Player = JsonPlayer(server.Game, self.txqueue)
        SocketServer.StreamRequestHandler.__init__(self, *args, **kws)

    def txloop(self):
        while True:
            msg = self.txqueue.get()
            if not msg: break
            if msg[-1] != "\n": msg = msg + "\n"
            # print "Writing: " + msg
            self.wfile.write(msg)
        pass

    def handle(self):
        print "connection from %s" % self.client_address[0]
        while True:
            try:
                msg = self.rfile.readline()
            except:
                print "Read Error"
                break
            if not msg: break
            self.Player.receive(msg)
        print "%s disconnected" % self.client_address[0]

    def finish(self):
        self.txqueue.put(None)
        self.txthread.join()
        self.Player.remove()
        return SocketServer.StreamRequestHandler.finish(self)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Spades Server')
    parser.add_argument('port', type=int, default=PORT, help="Port")
    parser.add_argument("-i", '--ip', type=str, default=HOST, help="Host address, default: %s" % HOST)
    parser.add_argument("-d", '--dummy', action="store_true", default=False, help="Set to initiate with 3x dummy players")
    (args) = parser.parse_args()

    # Initialize game
    Spades = Game()

    # TODO: Parameterize the "Dumb" players
    if args.dummy:
        player1 = DumbPlayer(Spades)
        player1.set_name("Sully")
        player1.team = 1
        player2 = DumbPlayer(Spades)
        player2.set_name("Wazowski")
        player2.team = 2
        player3 = DumbPlayer(Spades)
        player3.set_name("Boo")
        player3.team = 1

    # Create the server, binding to localhost on port 9999
    server = SpadesServer(Spades, (args.ip, args.port), SpadesRequestHandler)
    server.Game = Spades

    # # Activate the server; this will keep running until you
    # # interrupt the program with Ctrl-C
    # server.serve_forever()

    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    server_thread = threading.Thread(target=server.serve_forever)
    # Exit the server thread when the main thread terminates
    server_thread.daemon = True
    server_thread.start()
    print "Server loop running in thread:", server_thread.name

    print "Press any key to STOP"
    raw_input()

    # while True:
    #     print server.get_client_number()
    #     time.sleep(1)

    Spades.shutdown()
    server.shutdown()