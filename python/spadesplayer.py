import json
import uuid
import logging

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
        self.name = ""
        self.team = 0
        self.bid  = 0

        self.logger  = logging.getLogger(BLUE+'Player'+RESET)

        self.Game = Game
        self.Game.add_player(self)

    def update_name(self, name):
        self.name = name
        self.logger  = logging.getLogger(BLUE+self.name+RESET)

    def deal_hand(self, hand):
        for card in hand:
            self.cards.append(card)
            self.played.append(False)
        # print "Received cards:", self.cards

    def update_status(self, status):
        self.logger.info("Got Status Update")

    def update_hand(self, hand):
        self.logger.info("Got Hand Update, Action = %s" % hand['action'])
        # print hand

    def place_bid(self, bid):
        self.logger.info("Bidding: " + str(bid))
        self.bid = bid
        self.Game.place_bid(self, self.bid)

    def play_card(self, card):
        self.logger.info("Playing Card: " + str(card))
        return self.Game.place_card(self, card)
        # TODO: Check for errors


class JsonPlayer(Player):
    def __init__(self, Game, txqueue):
        Player.__init__(self, Game)
        self.txqueue = txqueue

    def remove(self):
        self.Game.delete_player(self)

    def update_status(self, status):
        # Contains game status:
        #  - Players / partners
        #  - Current score
        self.txqueue.put(json.dumps(status))

    def update_hand(self, status):
        # Hand Status:
        #  - Cards in hand
        #  - Current bids
        #  - Game status (Bid round, play round)
        #  - Request? (Bid, Card)
        #  - Played cards
        print status
        pass

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
            self.txqueue.put(json.dumps(self.Game.get_status()))

    def receive_init(self, data):
        print "Received Init"
        if not self.check_for_key(data, 'id'): return
        if not self.check_for_key(data, 'team'): return
        try:
            team = int(data["team"])
        except:
            self.throw_client_error('invalid team field')
        if not team in [0, 1, 2]:
            self.throw_client_error('invalid team option. Must be 0, 1, or 2')

        # Set name and team index 
        self.name = data['id']
        self.team = team

        # Send out the status update
        self.Game.update_status()

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

