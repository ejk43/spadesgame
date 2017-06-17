import json
import uuid
import logging
from queue import Queue
import threading
import random

names = ["Sulley", "Mike", "Boo", "Happy", "Dopey", "Sleepy", "Sneezy", "Bashful", "Grumpy", "Doc", "Tarzan", "Jane", "Woody", "Buzz", "Slinky", "Rex", "Hamm", "Aladdin", "Jasmine", "Jafar", "Iago", "Belle", "Gaston", "Beast", "Mater", "Dumbo", "Nemo", "Marlin", "Dory", "Bruce", "Elsa", "Anna", "Olaf", "Sven", "Phil"]

RED   = "\033[1;31m"  
BLUE  = "\033[1;34m"
CYAN  = "\033[1;36m"
GREEN = "\033[0;32m"
RESET = "\033[0;0m"
BOLD    = "\033[;1m"
REVERSE = "\033[;7m"

# Defines player behavior for spadesgame
#  - Base class defines update functions

# Derived classes provide JSON interactions between updates

# logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

class Player():
    def __init__(self,  Game):
        self.uuid = uuid.uuid1()
        self.cards = []
        self.played = []
        self.team = 0
        self.bid  = 0
        self.name = ""

        self.logger  = logging.getLogger(BLUE+'Player'+RESET)

        # Provide thread + Queue to receive updates
        self.upqueue = Queue()
        self.upthread = threading.Thread(target=self.update_loop)
        self.upthread.daemon = True
        self.upthread.start()

        self.Game = Game
        self.Game.add_player(self)

    def remove(self):
        print("killing %s" % self.name)
        self.upqueue.put(None)
        self.upthread.join()

    # "PUBLIC" Functions
    def update(self, data):
        self.upqueue.put(data)

    def deal_hand(self, hand):
        self.cards = []
        for card in hand:
            self.cards.append(card)
            self.played.append(False)

    # "Protected" Functions
    def place_bid(self, bid):
        self.logger.info("Bidding: " + str(bid))
        self.bid = bid
        return self.Game.place_bid(self, self.bid)

    def play_card(self, card):
        self.logger.info("Playing Card: " + str(card))
        return self.Game.place_card(self, card)

    def update_loop(self):        
        while True:
            data = self.upqueue.get()
            if not data: break
            if data['type'] == "status":
                self.update_status(data)
            elif data['type'] == "hand":
                self.update_hand(data)
            else:
                self.logger.info("Received incorrect update message type: %s" % data['type'])
        pass

    # "Overloadable"
    def update_status(self, status):
        self.logger.info("Got Status Update")
        self.logger.info("Players: %s" % status['players'])

    def update_hand(self, hand):
        self.logger.info("Got Hand Update, Action = %s" % hand['action'])

    def set_name(self, name):
        if type(name) == 'list':
            name = name[0]
        self.name = name
        self.logger  = logging.getLogger(BLUE+self.name+RESET)
        # TODO: Check for errors

class DumbPlayer(Player):
    # Dont use DumbPlayer... It will cause silly recursion in update function
    def update_hand(self, hand):
        self.logger.info("Got Hand Update, Action = %s" % hand['action'])
        if hand['action'] == "bid":
            self.logger.info("Making a dumb bid")
            self.place_bid(3)
        elif hand['action'] == "card":
            self.play_first_card()
        else:
            self.logger.info("Waiting!")

    def play_first_card(self):
        idx = 0
        while self.play_card(self.cards[idx])[0] < 0:
            idx = idx + 1

class JsonPlayer(Player):
    def __init__(self, Game, txqueue):
        # Set up txqueue FIRST
        self.txqueue = txqueue

        # Initialize player class
        Player.__init__(self, Game)

    def remove(self):
        self.Game.delete_player(self)
        Player.remove(self)

    def update_status(self, status):
        # Contains game status:
        #  - Players / partners
        #  - Current score
        self.logger.info("Got Status Update")
        self.txqueue.put(json.dumps(status))

    def update_hand(self, status):
        # Hand Status:
        #  - Cards in hand
        #  - Current bids
        #  - Game status (Bid round, play round)
        #  - Request? (Bid, Card)
        #  - Played cards
        self.logger.info("Got Hand Update, Action = %s" % status['action'])
        self.txqueue.put(json.dumps(status))

    def receive(self, msg):
        # Try to load the JSON
        self.logger.info("Got message: %s" % msg.rstrip())
        try:
            data = json.loads(msg)
        except ValueError:
            self.throw_client_error('json failed to parse')
            return

        # Check for missing type field
        if not self.check_for_key(data, 'type'): return

        # Switch on type
        if data['type'] == 'request':
            self.receive_request(data)
        elif data['type'] == 'init':
            self.receive_init(data)
        elif data['type'] == 'bid':
            self.receive_bid(data)
        elif data['type'] == 'card':
            self.receive_card(data)
        elif data['type'] == 'add':
            self.create_new_player(data)
        elif data['type'] == 'kill':
            self.remove_dummy_player(data)
        else:
            self.throw_client_error('unknown type')

        # print "Parsed to: %s" % str(data)

    def receive_request(self, data):
        self.logger.info("Received Request")
        if not self.check_for_key(data, 'request'): return

        if data['request'] == 'status':
            self.txqueue.put(json.dumps(self.Game.get_status()))

    def receive_init(self, data):
        self.logger.info("Received Init")
        if not self.check_for_key(data, 'id'): return
        if not self.check_for_key(data, 'team'): return
        try:
            team = int(data["team"])
        except:
            self.throw_client_error('invalid team field')
        if not team in [0, 1, 2]:
            self.throw_client_error('invalid team option. Must be 0, 1, or 2')

        # Set name and team index
        self.set_name(data['id'])
        self.team = team

        # Send out the status update
        self.Game.update_status()

    def receive_bid(self, data):
        self.logger.info("Received Bid")
        if not self.check_for_key(data, 'bid'): return
        try:
            bid = int(data["bid"])
        except:
            self.throw_client_error('invalid bid field')
        if bid < 0 or bid > 13:
            self.throw_client_error("invalid bid. Must be 0 <= bid <= 13")
        
        # Try bidding
        code, msg = self.place_bid(bid)

        # If we get an error code, throw message
        if code < 0:
            self.throw_client_error(msg)

    def receive_card(self, data):
        self.logger.info("Received Card")
        if not self.check_for_key(data, 'card'): return
        try:
            card = str(data["card"])
        except:
            self.throw_client_error('invalid card field')
            return
        
        # Try playing the card
        code, msg = self.play_card(card)

        # If we get an error code, throw message
        if code < 0:
            self.throw_client_error(msg)

    def create_new_player(self, data):
        self.logger.info("Adding a dummy player")

        if not "name" in data.keys():
            print names
            newname = random.choice(names)
            while newname in self.Game.get_player_list():
                newname = random.choice(names)
            print newname
        else:
            try:
                newname = str(data["name"])
            except:
                self.throw_client_error('invalid name field')
                return

        if not "team" in data.keys():
            team1 = self.Game.get_team_names(1)
            team2 = self.Game.get_team_names(2)
            print team1, team2
            print len(team1)
            if len(team1) < 2:
                team = 1
            elif len(team2) < 2:
                team = 2
            else:
                self.throw_client_error('no extra players needed')
                return
        else:
            try:
                team = int(data["team"])
            except:
                self.throw_client_error('invalid team field')
                return

        player = DumbPlayer(self.Game)
        player.set_name(newname)
        player.team = team

        self.Game.update_status()

    def remove_dummy_player(self, data):
        self.logger.info("Removing a dummy player")
        if not self.check_for_key(data, 'name'): return
        try:
            name = str(data["name"])
        except:
            self.throw_client_error('invalid name field')
            return
        
        curr_players = self.Game.get_player_list()
        
        if not name in curr_players:
            self.throw_client_error('player %s not currently playing' % name)
            return
        
        for (ii, play) in enumerate(curr_players):
            if play == name:
                playerobj = self.Game.players[ii]
                if playerobj == self:
                    self.throw_client_error('you cannot remove yourself, silly')
                    return
                if not isinstance(playerobj, DumbPlayer):
                    self.throw_client_error('cannot remove human players. Be nice')
                    return
                self.Game.delete_player(self.Game.players[ii])

        self.Game.update_status()

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

