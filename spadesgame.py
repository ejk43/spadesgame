from spadesplayer import Player
import itertools
import random
import math
import threading
from enum import Enum
import logging

suites = ['D','H','C','S']
values = [1,2,3,4,5,6,7,8,9,10,'J','Q','K']
cards = [c for c in itertools.product(suites, values)]

class Deck():
    def __init__(self):
        self.cards = cards

    def shuffle(self):
        random.shuffle(cards)

    def deal(self, nHands=4, nCards=None):
        if nCards==None:
            # Auto-determine number of cards if not specified
            nCards = int(math.floor(len(self.cards)/nHands))
        hands = []
        for ii in range(nHands):
            hands.append(self.cards[ii:nHands*nCards+ii:nHands])
        return hands

class Game():
    class State(Enum):
        WAIT = 1
        BID  = 2
        PLAY = 3

    def __init__(self):
        self.lock    = threading.Lock()
        self.logger  = logging.getLogger('Game')
        self.state   = Game.State.WAIT
        self.deck    = Deck()
        self.players = []
        self.team1   = []
        self.team2   = []
        self.score1  = 0
        self.score2  = 0

    def update_status(self):
        self.lock.acquire()
        status = {'type'    : 'status',
                  'players' : self.get_player_names(),
                  'team1'   : self.team1,
                  'team2'   : self.team2,
                  'score1'  : self.score1,
                  'score2'  : self.score2}
        for player in self.players:
            player.update_status(status)
        self.lock.release()

    def add_player(self, newplayer):
        self.lock.acquire()
        if len(self.players) < 4:
            self.logger.info("Adding player: %s" % str(newplayer.name))
            self.players.append(newplayer)
        self.lock.release()

        # Send status to all players
        self.update_status()

    def delete_player(self, player):
        self.lock.acquire()
        for p in self.players:
            if player.uuid == p.uuid:
                self.players.remove(p)
        self.lock.release()
        
        # Send status to all players
        self.update_status()

    def get_player_names(self):
        return list(map(lambda p: p.name, self.players))

    def get_status(self):
        self.lock.acquire()
        status = {'type'    : 'status',
                  'players' : self.get_player_names(),
                  'team1'   : self.team1,
                  'team2'   : self.team2,
                  'score1'  : self.score1,
                  'score2'  : self.score2}
        self.lock.release()
        return status

    def loop(self):
        self.logger.info(self.state)
        if self.state == Game.State.WAIT:
            self.logger.info("Num Players = %i" % len(self.players))

        elif self.state == Game.State.BID:
            self.logger.info("bidding")

        elif self.state == Game.State.PLAY:
            self.logger.info("playing")


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

    myDeck = Deck()
    print myDeck.cards
    print myDeck.deal()
    myDeck.shuffle()
    print myDeck.cards
    print myDeck.deal()

    print
    myGame = Game()
    myGame.loop()

    myPlayer = Player("EJ")
    myGame.add_player(myPlayer)

    myGame.loop()