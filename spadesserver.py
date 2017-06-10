import SocketServer
import time
import threading
from Queue import Queue
from spadesgame import Game
from spadesplayer import Player
import json

# Temporary magic numbers
HOST, PORT = "localhost", 9000

# Initialize game
Spades = Game()

class JsonParser():
    def __init__(self, txqueue):
        global Spades
        self.txqueue = txqueue
        self.Spades = Spades
        self.Player = None

    def __del__(self):
        if self.Player:
            self.Spades.delete_player(self.Player)

    def receive(self, msg):
        # Try to load the JSON
        print "Got message: %s" % msg.rstrip()
        try:
            data = json.loads(msg)
        except ValueError:
            self.throw_client_error('json failed to parse')
            return

        # Check for missing type field
        if not self.check_for_key(data, 'type'): return
        print data['type']

        # Switch on type
        if data['type'] == 'request':
            self.receive_request(data)
        elif data['type'] == 'init':
            self.receive_init(data)
        elif data['type'] == 'bid':
            self.receive_bid(data)
        elif data['type'] == 'card':
            self.receive_card(data)
        else:
            self.throw_client_error('unknown type')

        print "Parsed to: %s" % str(data)

    def receive_request(self, data):
        print "Received Request"
        if not self.check_for_key(data, 'request'): return

        if data['request'] == 'status':
            self.txqueue.put(json.dumps(self.Spades.get_status()))

    def receive_init(self, data):
        print "Received Init"
        if not self.check_for_key(data, 'id'): return
        name = data['id']
        if not self.Player:
            self.Player = Player(name, self.txqueue)
            self.Spades.add_player(self.Player)
        else:
            self.Player.name = name

    def receive_bid(self, data):
        print "Received Bid"

    def receive_card(self, data):
        print "Received Card"

    def check_for_key(self, data, key):
        if not key in data.keys():
            self.throw_client_error('%s field missing' % key)
            return False
        return True

    def check_for_player(self):
        if not self.player:
            self.throw_client_error('player not initialized')
            return False
        return True

    def throw_client_error(self, text):
        error = {'type'  : 'error',
                 'error' : text}
        self.txqueue.put(json.dumps(error))



class SpadesServer(SocketServer.ThreadingTCPServer):
    # Override to count number of connections: 
    # https://stackoverflow.com/questions/5370778/how-to-count-connected-clients-in-tcpserver

    def __init__(self, *args, **kws):
        self._num_client = 0
        SocketServer.ThreadingTCPServer.__init__(self, *args, **kws)

    def process_request(self, *args, **kws):
        # NOTE: If we want to limit connections, use this?...
        #if self._num_client < 1:
        self._num_client += 1
        SocketServer.ThreadingTCPServer.process_request(self, *args, **kws)

    def process_request_thread(self, *args, **kws):
        SocketServer.ThreadingTCPServer.process_request_thread(self, *args, **kws)
        self._num_client -= 1

    def get_client_number(self):
        return self._num_client
    pass
 
class SpadesRequestHandler(SocketServer.StreamRequestHandler):
    """
    Handles one connection to the client.
    Provides queues as data interfaces
    """
    def __init__(self, *args, **kws):
        print "New Handler"
        self.txqueue = Queue()
        self.txthread = threading.Thread(target=self.txloop)
        # self.txthread.start()
        self.parser = JsonParser(self.txqueue)
        SocketServer.StreamRequestHandler.__init__(self, *args, **kws)

    def txloop(self):
        while True:
            msg = self.txqueue.get()
            if not msg: break
            if msg[-1] != "\n": msg = msg + "\n"
            print "Writing: " + msg
            self.wfile.write(msg)
            print "Wrote msg"
        pass

    def handle(self):
        global Spades

        print "connection from %s" % self.client_address[0]

        # Send first info
        # self.txqueue.put(json.dumps(Spades.get_status()))

        self.wfile.write(json.dumps(Spades.get_status()))

        while True:
            try:
                msg = self.rfile.readline()
            except:
                print "Read Error"
                break
            if not msg: break
            self.txqueue.put(msg)
            self.parser.receive(msg)
        print "%s disconnected" % self.client_address[0]

    def finish(self):
        self.txqueue.put(None)
        # self.txthread.join()
        return SocketServer.StreamRequestHandler.finish(self)


if __name__ == "__main__":

    # Create the server, binding to localhost on port 9999
    server = SpadesServer((HOST, PORT), SpadesRequestHandler)

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

    while True:
        print server.get_client_number()
        time.sleep(1)

    server.shutdown()