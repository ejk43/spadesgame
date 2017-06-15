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
values = ["2", "3", "4", "5", "6", "7", "8", "9", "10", 'J', 'Q', 'K', 'A']
cards  = [str(c[0])+str(c[1]) for c in itertools.product(suites, values)]
trump  = 'S'
valdict = dict(zip(values, range(len(values))))

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

# TODO: 
# - Thread the update process, add queue
# - Use recursive lock

class Game():
    class State(Enum):
        WAIT = 1
        BID  = 2
        PLAY = 3
        END  = 4

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
        self.trick   = []
        self.trickidx = 0
        self.spadesbroke = False
        self.rejectcards = True

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
            # print ii, self.turn
            # print player
            # print player.name
            # print self.state
            action = "wait"
            if ii == self.turn:
                if self.state == Game.State.BID:
                    action = "bid"
                elif self.state == Game.State.PLAY:
                    action = "card"
            handinfo = self.get_hand(player.cards, action)
            player.update_hand(handinfo)

    def add_player(self, newplayer):
        self.lock.acquire()
        if len(self.players) < 4:
            self.logger.info("added: %s" % str(BLUE+newplayer.name+RESET))
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
        self.state = Game.State.WAIT
        self.lock.release()
        
        # Send status to all players
        self.update_status()

    def place_bid(self, player, bid):
        # Error Checking
        if self.state != Game.State.BID:
            self.logger.info("Error: Not correct time to bid")
            return -1, "Not correct time to bid"
        if player != self.playerorder[self.turn]:
            self.logger.info("Error: %s bidding out of turn" % player.name)
            return -2, "Bid out of turn"

        # Place the bid
        self.lock.acquire()
        self.logger.info("Received BID from %s: %i" % (player.name, bid))
        self.bids.append([player.name, bid, 0])
        if self.turn < 4:
            self.turn = self.turn + 1
        self.lock.release()

        # Check for end of Bid State
        if self.turn == 4:
            self.end_bidding()

        self.update_hand()
        return True, ""

    def place_card(self, player, card):
        # Error Checking
        if self.state != Game.State.PLAY:
            self.logger.info("Error: Not correct time to play a card")
            return -1, "Not correct time to play a card"
        if player != self.playerorder[self.turn]:
            self.logger.info("Error: %s playing out of turn" % player.name)
            return -2, "Playing out of turn"
        if not card in player.cards:
            self.logger.info("Error: %s does not have %s in hand" % (player.name, card))
            return -3, "Card not in hand"

        # Check that player follows suit
        if len(self.trick) > 0:
            # Player must follow lead suit if possible
            leadsuit = self.trick[0][1][0]
            if card[0] != leadsuit:
                handsuits = [c[0] for c in player.cards]
                if leadsuit in handsuits and self.rejectcards:
                    # Player has the leadsuit available
                    self.logger.info("Error: %s must follow suit" % player.name)
                    return -4, "Must follow suit"
                elif card[0] == trump and not self.spadesbroke:
                    self.logger.info("SPADES BROKEN")
                    self.spadesbroke = True
        elif (card[0] == trump) and (not self.spadesbroke) and (self.rejectcards):
            self.logger.info("Error: %s played spades before broken" % player.name)
            return -5, "Played spades before broken"


        # Place the Card
        self.lock.acquire()
        self.logger.info("Received CARD from %s: %s" % (player.name, card))
        
        self.trick.append((player.name, card))
        player.cards.remove(card)
        player.played.append(card)

        # Advance turn if needed
        if self.turn < 4:
            self.turn = self.turn + 1
        self.lock.release()

        if self.turn == 4:
            self.end_trick()

            if self.trickidx < 13:
                self.start_trick()
            else:
                self.end_hand()

                if self.score1 > 500 or self.score2 > 500:
                    self.end_game()
                else:
                    self.start_hand()

        self.update_hand()

        return True, ""

    def deal_cards(self):
        self.lock.acquire()
        self.deck.shuffle()
        self.logger.info("Dealing! Dealer is %s" % self.dealerorder[0].name)
        for (player, hand) in zip(self.playerorder, self.deck.deal()):
            self.logger.info("Dealing to %s: %s" % (player.name, str(hand)))
            player.deal_hand(hand)
        self.lock.release()

    def score_trick(self, trick):
        # Pull out cards, suits, values
        cards = [t[1] for t in trick]
        suits = [c[0] for c in cards]
        vals  = [c[1:] for c in cards]

        # Look for a trump card
        leadsuit = suits[0] if not trump in suits else trump

        # Find the winning card
        maxval = -1
        winner = trick[0]
        for (suit, value, currtrick) in zip(suits, vals, trick):
            # Only look through cards from the leading suit
            if suit == leadsuit:
                # Replace winner if value is higher
                if valdict[value] >= maxval:
                    maxval = valdict[value]
                    winner = currtrick

        return winner

    def score_hand(self, score, team, bids):
        # Save off info
        total_bid = bids[0][1] + bids[1][1]
        total_got = bids[0][2] + bids[1][2]
        overtricks = score % 10

        # Check and score nils
        if bids[0][1] == 0:
            score += 100 if bids[0][2] == 0 else -100
        if bids[1][1] == 0:
            score += 100 if bids[1][2] == 0 else -100

        # Score rest of hand
        if total_got >= total_bid:
            score += 10*total_bid
            score += total_got - total_bid
            # If we hit 10 overtricks, subtract 100
            overtricks += total_got - total_bid
            if overtricks >= 10:
                score -= 100
        else:
            # Subtract bid if we did not get all the tricks
            score -= 10*total_bid
        return score

    def start_game(self):
        self.lock.acquire()
        self.logger.info("Starting Game")
        self.bids     = []
        self.trick    = []
        self.turn     = 0
        self.trickidx = 0
        self.spadesbroke = False
        self.state    = Game.State.BID

        team1 = self.get_team(1)
        team2 = self.get_team(2)
        self.dealerorder = [team1[0], team2[0], team1[1], team2[1]]
        self.playerorder = self.dealerorder[1:] + self.dealerorder[0:1]
        self.lock.release()

        self.deal_cards()

    def start_hand(self):
        self.lock.acquire()
        self.logger.info("Starting new Hand")
        self.bids     = []
        self.trick    = []
        self.turn     = 0
        self.trickidx = 0
        self.spadesbroke = False
        self.state    = Game.State.BID
        
        self.dealerorder = self.dealerorder[1:] + self.dealerorder[0:1]
        self.playerorder = self.dealerorder[1:] + self.dealerorder[0:1]
        self.lock.release()

        self.deal_cards()
        return

    def start_trick(self):
        # NOT called for the first trick
        self.lock.acquire()
        self.turn    = 0
        self.trick   = []
        self.playerorder = self.playerorder[1:] + self.playerorder[0:1]
        self.logger.info("Starting trick %i. First player: %s" % (self.trickidx+1, self.get_turn()))
        self.lock.release()

    def end_bidding(self):
        self.lock.acquire()
        self.logger.info("Ending Bidding")
        self.logger.info("Starting First Trick")
        self.turn = 0
        self.state = Game.State.PLAY
        self.lock.release()

    def end_trick(self):
        # Send update for the final player
        self.update_hand()

        # Score the trick
        # Reset info
        self.lock.acquire()
        self.trickidx = self.trickidx + 1
        self.logger.info("Scoring trick %i: %s" % (self.trickidx, str(self.trick)))
        winner = self.score_trick(self.trick)
        self.logger.info("Winner: %s, Card: %s" % (winner[0], winner[1]))
        for bid in self.bids:
            if bid[0] == winner[0]:
                break
        bid[2] = bid[2] + 1

        self.lock.release()

    def end_hand(self):
        # Score the hand
        self.lock.acquire()
        self.logger.info("Hand Results: %s" % (str(self.bids)))
        
        # Score team 1
        team1 = self.get_names(self.get_team(1))
        bids1 = [bid for bid in self.bids if bid[0] in team1]
        score1 = self.score_hand(self.score1, team1,  bids1)
        self.logger.info("Team 1 Score: %i --> %i" % (self.score1, score1))
        self.score1 = score1

        # Score team 2
        team2 = self.get_names(self.get_team(2))
        bids2 = [bid for bid in self.bids if bid[0] in team2]
        score2 = self.score_hand(self.score2, team2,  bids2)
        self.logger.info("Team 2 Score: %i --> %i" % (self.score2, score2))
        self.score2 = score2

        # TODO: Score
        self.lock.release()

        # Send the new game update
        self.update_status()

    def end_game(self):
        self.logger.info("GAME OVER!!!")
        self.state = Game.State.END

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

    def get_turn(self):
        if self.turn >= 0 and self.turn < 4:
            return self.playerorder[self.turn].name
        else:
            return "none"

    def get_hand(self, cards, action):
        hand = {'type'   : 'hand',
                'cards'  : cards,
                'bids'   : self.bids,
                'trick'  : self.trick,
                'turn'   : self.get_turn(),
                'action' : action}
        return hand

    def all_unique_names(self):
        names = self.get_player_list()
        seen = []
        for name in names:
            if name in seen:
                return False
            else:
                seen.append(name)
        return True

    def gameloop(self):
        while True:
            if self.halt:
                return

            self.logger.info(self.state)
            if self.state == Game.State.WAIT:
                self.logger.info("Num Players = %i" % len(self.players))

                # Check if we can move on to the game
                if len(self.players) == 4 and self.all_unique_names():
                    if len(self.get_team(1)) == 2 and len(self.get_team(2)) == 2:
                        # If we have four players and each team has 2 players
                        self.logger.info("READY TO START")
                        self.start_game()
                        self.update_hand()

            elif self.state == Game.State.BID:
                # self.logger.info("bidding")
                pass

            elif self.state == Game.State.PLAY:
                # self.logger.info("playing")
                pass

            elif self.state == Game.State.END:
                if len(self.players) < 4:
                    self.state = Game.State.WAIT

            time.sleep(1)

    def shutdown(self):
        self.halt = True
        self.gamethread.join()


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

    myGame = Game()

    player1 = Player(myGame)
    player1.update_name("EJ")
    player1.team = 1
    player2 = Player(myGame)
    player2.update_name("Michael")
    player2.team = 2
    player3 = Player(myGame)
    player3.update_name("David")
    player3.team = 1
    player4 = Player(myGame)
    player4.update_name("Paige")
    player4.team = 2

    time.sleep(2)

    player2.place_bid(5)
    player3.place_bid(4)
    player4.place_bid(2)
    player1.place_bid(2)

    time.sleep(3)

    playerlist = [player2, player3, player4, player1]
    for ii in range(13):
        print list(map(lambda p: p.name, playerlist))
        for pl in playerlist:
            idx = 0
            while pl.play_card(pl.cards[idx])[0] < 0:
                idx = idx + 1
                # time.sleep(1)
        time.sleep(1)
        playerlist = playerlist[1:] + playerlist[0:1]


    player3.place_bid(4)
    player4.place_bid(2)
    player1.place_bid(2)
    player2.place_bid(5)

    time.sleep(3)

    playerlist = [player3, player4, player1, player2]
    for ii in range(13):
        print list(map(lambda p: p.name, playerlist))
        for pl in playerlist:
            idx = 0
            while pl.play_card(pl.cards[idx])[0] < 0:
                idx = idx + 1
                # time.sleep(1)
        time.sleep(1)
        playerlist = playerlist[1:] + playerlist[0:1]


    # trick = [('EJ', 'HQ'), ('Michael', 'H2'), ('David', 'H4'), ('Paige', 'HJ')]
    # winner = myGame.score_trick(trick)
    # print trick
    # print winner

    # trick = [('EJ', 'HQ'), ('Michael', 'H2'), ('David', 'H4'), ('Paige', 'S2')]
    # winner = myGame.score_trick(trick)
    # print trick
    # print winner

    # trick = [('EJ', 'H2'), ('Michael', 'CK'), ('David', 'CQ'), ('Paige', 'CA')]
    # winner = myGame.score_trick(trick)
    # print trick
    # print winner

    myGame.shutdown()
