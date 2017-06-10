from spadesplayer import Player, JsonPlayer
import itertools
import random
import math
import threading
from enum import Enum
import logging
import time

RED   = "\033[1;31m"  
BLUE  = "\033[1;34m"
CYAN  = "\033[1;36m"
GREEN = "\033[0;32m"
RESET = "\033[0;0m"
BOLD    = "\033[;1m"
REVERSE = "\033[;7m"

suites = ['D','H','C','S']
values = [2, 3, 4, 5, 6, 7, 8, 9, 10, 'J', 'Q', 'K', 'A']
cards = [str(c[0])+str(c[1]) for c in itertools.product(suites, values)]

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
        self.logger  = logging.getLogger(RED+'Game'+RESET)
        self.state   = Game.State.WAIT
        self.deck    = Deck()
        self.players = []
        self.playerorder = []
        self.score1  = 0
        self.score2  = 0
        self.turn    = 0
        self.bids    = []
        self.tricks  = []

        # Start game loop
        self.halt = False
        self.gamethread = threading.Thread(target=self.gameloop)
        self.gamethread.daemon = True
        self.gamethread.start()

    def update_status(self):
        self.lock.acquire()
        status = self.get_status()
        for player in self.players:
            player.update_status(status)
        self.lock.release()

    def update_hand(self):
        for (ii, player) in enumerate(self.playerorder):
            print ii
            print player
            print player.name
            action = "wait"
            if ii == self.turn:
                if self.state == Game.State.BID:
                    action = "bid"
                elif self.state == Game.State.PLAY:
                    action = "card"
            handinfo = self.get_hand(player.cards, action)
            player.update_hand(handinfo)
            pass

    def add_player(self, newplayer):
        self.lock.acquire()
        if len(self.players) < 4:
            self.logger.info("added: %s" % str(newplayer.name))
            self.players.append(newplayer)
        self.lock.release()

        # Send status to all players
        self.update_status()

    def delete_player(self, player):
        self.lock.acquire()
        self.logger.info("Trying to delete player: %s" % str(player.name))
        for p in self.players:
            if player.uuid == p.uuid:
                self.logger.info("Deleted: %s" % str(player.name))
                self.players.remove(p)
        self.lock.release()
        
        # Send status to all players
        self.update_status()

    def get_player_list(self):
        return list(map(lambda p: p.name, self.players))

    def get_team(self, idx):
        return [p for p in self.players if (p.team == idx)]

    def get_names(self, playerlist):
        return list(map(lambda p: p.name, playerlist))

    def get_status(self):
        status = {'type'    : 'status',
                  'players' : self.get_player_list(),
                  'team1'   : self.get_names(self.get_team(1)),
                  'team2'   : self.get_names(self.get_team(2)),
                  'score1'  : self.score1,
                  'score2'  : self.score2}
        return status

    def get_hand(self, cards, action):
        hand = {'type'   : 'hand',
                'cards'  : cards,
                'bids'   : self.bids,
                'trick'  : self.tricks,
                'turn'   : self.playerorder[self.turn].name,
                'action' : action}
        return hand

    def start_bidding(self):
        self.lock.acquire()
        self.state = Game.State.BID

        self.logger.info("Shuffling")
        self.deck.shuffle()

        for (player, hand) in zip(self.players, self.deck.deal()):
            print player.name, hand
            player.deal_hand(hand)

        team1 = self.get_team(1)
        team2 = self.get_team(2)
        self.playerorder = [team1[0], team2[0], team1[1], team2[1]]

        self.lock.release()
        return

    def start_play(self):
        return

    def gameloop(self):
        while True:
            if self.halt:
                return

            self.logger.info(self.state)
            if self.state == Game.State.WAIT:
                self.logger.info("Num Players = %i" % len(self.players))

                # Check if we can move on to the game
                if len(self.players) == 4:
                    if len(self.get_team(1)) == 2 and len(self.get_team(2)) == 2:
                        # If we have four players and each team has 2 players
                        self.logger.info("READY TO START")
                        self.start_bidding()
                        self.update_hand()

            elif self.state == Game.State.BID:
                self.logger.info("bidding")

            elif self.state == Game.State.PLAY:
                self.logger.info("playing")

            time.sleep(1)

    def shutdown(self):
        self.halt = True
        self.gamethread.join()


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

    myGame = Game()

    player1 = Player()
    player1.name = "EJ"
    player1.team = 1
    myGame.add_player(player1)
    player2 = Player()
    player2.name = "Michael"
    player2.team = 1
    myGame.add_player(player2)

    time.sleep(5)

    player1 = Player()
    player1.name = "David"
    player1.team = 2
    myGame.add_player(player1)
    player2 = Player()
    player2.name = "Paige"
    player2.team = 2
    myGame.add_player(player2)

    time.sleep(5)

    myGame.shutdown()
