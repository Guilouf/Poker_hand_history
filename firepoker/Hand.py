import random
import firepoker

_BB = 120


suits = 'cshd'
values = '23456789TJQKA'

_pos_name_lst = [
        ["BB", "BTN"],
        ["SB", "BB", "BTN"],
        # ["CO", "BTN", "SB", "BB"],
        # ["UTG", "CO", "BTN", "SB", "BB"],
        # ["UTG", "MP", "CO", "BTN", "SB", "BB"],
        # ["UTG", "MP1", "MP2", "CO", "BTN", "SB", "BB"],
        # ["UTG", "MP1", "MP2", "MP3", "CO", "BTN", "SB", "BB"],
        # ["UTG", "UTG+1", "MP1", "MP2", "MP3", "CO", "BTN", "SB", "BB"],
        # ["UTG", "UTG+1", "UTG+2", "MP1", "MP2", "MP3", "CO", "BTN", "SB", "BB"],
    ]

def MakeTempGamefile(stacks, ante=0, bb=_BB):
    temp_filename = 'temp.game'
    n_players = len(stacks)

    print(n_players)
    stacks_str = ' '
    for pos in _pos_name_lst[n_players-2]:
        stacks_str += '{} '.format(int(stacks[pos]))

    if n_players == 2:
        blinds = [bb, bb/2]
    else:
        blinds = [bb / 2, bb] + [0] * (n_players-2)
    blinds = ' '.join( map(str, blinds))

    fh = open(temp_filename, 'w')
    fh.write('''GAMEDEF
nolimit
numPlayers = {}
numRounds = 4
stack = {}
ante = {}
winnerBonus = 60
blind = {}
firstPlayer = {} 1 1 1
numSuits = 4
numRanks = 13
numHoleCards = 2
numBoardCards = 0 3 1 1
END GAMEDEF'''.format( n_players, stacks_str, ante, blinds, n_players )
    )
    fh.close()   
    return temp_filename

def Card2Str(card):
    return values[int(card) // len(suits)] + suits[card % len(suits)]

class Hand:   
    def __init__(self,  rng_seed, stacks=None, gamefilename=None, hand_id=0, bb=_BB, ante=0):        
        self._rng = firepoker.RngState.init(rng_seed)
        if gamefilename is not None:
            self._game = firepoker.readGame(gamefilename)        
        else:
            assert stacks is not None
            tempgamefile = MakeTempGamefile(stacks=stacks, ante=ante, bb=bb)            
            self._game = firepoker.readGame(tempgamefile) 
            
        self._state = firepoker.initState(self._game, hand_id)
        firepoker.dealCards(self._game, self._rng, self._state)
        
    def evaluate(self, position):
        assert self._state.finished
        return firepoker.valueOfState(self._game, self._state, position)

    def get_acting_player(self):
        return _pos_name_lst[self._game.numPlayers-2][firepoker.currentPlayer(self._game, self._state)]              

    def get_holecards(self, position):      
        cards = self._state.holeCards[position]
        cards = cards[:self._game.numHoleCards]             
        cards = map(Card2Str, cards)
        return ''.join(cards)

    def get_boardcards(self):
        n_visible = firepoker.sumBoardCards(self._game, self._state.round)
        cards = self._state.boardCards[:n_visible]      
        cards = map(Card2Str, cards)
        assert self._game.numBoardCards[0] == 0 \
               and self._game.numBoardCards[1] == 3 \
               and self._game.numBoardCards[2] == 1 \
               and self._game.numBoardCards[3] == 1 
        cards = [''.join(cards[:3]), ''.join(cards[3:4]), ''.join(cards[4:5])]             
        return '/'.join(cards).strip('/ ')
        
    def finished(self):
        return self._state.finished     
    
    def doAction(self, action):
        assert firepoker.isValidAction(self._game, self._state, False, action)
        firepoker.doAction(self._game, action, self._state)
        
    def get_num_players(self):
        return self._game.numPlayers
        
    def get_state_str(self):
        state = ''
        for r in xrange(self._state.round+1):
            for a in xrange(self._state.numActions[r]):
                state += self._state.action[r][a]
            if r != self._state.round:
                state += '/'
        return state

    def get_minraise(self):
        return firepoker.raiseIsValid(self._game, self._state)[0]

    def get_pot(self):
        pot = 0
        for p in xrange(self._game.numPlayers):
            pot += self._state.spent[p]
        return pot

    def get_num_raises(self):
        return firepoker.numRaises(self._state)

    def get_round(self):
        return self._state.round

    def get_investment(self, pos):
        if pos.lower() == 'max':
            return self._state.maxSpent
        else:
            return self._state.spent[_pos_name_lst[self._game.numPlayers-2].index(pos)]


if __name__ == '__main__':
    
    # # print help(type(firepoker.Game))

    print('\nUsing constructor from file')
    hand = Hand(gamefilename='holdem.nolimit.2p.3000.ante-0.reverse_blinds.game', rng_seed=random.randint(0,100))
    
    for action in 'c,c,r240,c,r360,c,c,c'.split(','):
        print(hand.get_state_str(), hand.get_acting_player())
        hand.doAction(action)
    print(hand.evaluate(0), hand.evaluate(1))
    
    # for action in 'c,c,r240,c,r360,c'.split(','):
    #     hand.doAction(action)

    print(hand.finished())
    print(hand.get_holecards(0), hand.get_holecards(1), hand.get_boardcards())
    print(hand.get_num_players())
    print(hand.get_state_str())

    print('\nUsing constructor from stacks')

    hand = Hand(stacks={'BTN':3000,'BB':3000}, rng_seed=random.randint(0,100))
    for action in 'c,c,r240'.split(','):
        hand.doAction(action)

    print(hand.finished())
    print(hand.get_holecards(0), hand.get_holecards(1), hand.get_boardcards())
    print(hand.get_num_players())
    print(hand.get_state_str())
    print(hand.get_minraise())
    print(hand.get_pot())
    print(hand.get_num_raises())
    print(hand.get_round())
    print(hand.get_investment('max'))

    #print help(firepoker)