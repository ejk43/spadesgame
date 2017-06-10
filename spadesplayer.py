import json
import uuid

# Defines player behavior for spadesgame
#  - Base class defines update functions

# Derived classes provide JSON interactions between updates

class Player():
    def __init__(self, name, txqueue):
        self.uuid = uuid.uuid1()
        self.hand = []
        self.name = name
        self.txqueue = txqueue

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
