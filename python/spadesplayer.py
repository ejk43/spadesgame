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
        return self.Game.place_bid(self, self.bid)

    def play_card(self, card):
        self.logger.info("Playing Card: " + str(card))
        return self.Game.place_card(self, card)
        # TODO: Check for errors

class DumbPlayer(Player):
    # Dont use DumbPlayer... It will cause silly recursion in update functions
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
        self.update_name(data['id'])
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
            bid = str(data["card"])
        except:
            self.throw_client_error('invalid card field')
        if not card in self.cards:
            self.throw_client_error("card must be in hand")
        
        # Try playing the card
        code, msg = self.play_card(bid)

        # If we get an error code, throw message
        if code < 0:
            self.throw_client_error(msg)

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

