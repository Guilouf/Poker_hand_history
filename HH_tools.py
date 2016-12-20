# -*- coding: utf-8 -*-
# from __future__ import print_function

"""
ante # int, eg 0
stacks # dict with keys = names of positions and values stacks of players, eg {'BB':100,'BTN':1200}
sequence # string with c for check/call, rX for raise/bet of X, f for a fold. Raise numbers give total raise TO level eg cc/r240c/ 
holecards # dictionary with keys = names of positions and values equal to cards or None if not present eg. {'BB':'AcAd','BTN':None}
boardcards # string with cards with different streets/rounds separated by a hash eg. 2c2d2h/3h/4h in case game reached the river
winner # string, position name eg. BTN
players # dictionary with keys = names of positions and values equal to player names eg. {'BB':'Jack', 'BTN':'John'}

BB – big blind
SB – small blind
BTN – button
CO – cut-off (the seat to the right of the button)
MP – “middle position”: the three seats to the right of the cut-off.
UTG - under the gun

"""

import sys
import re
# import firepoker
# from firepoker import *

class Hand_history:
    """
    Class called for each hand
    """
    def __init__(self, hand_file):
        # format attributes
        self.ante = 0
        self.blind = 0
        self.stacks = {}  # key: position_name value: stack_of_player chips
        self.sequence = ""
        self.holecards = {}  # in the examples, hero is the player. Holecards are dealt just after "holecard"
        self.boardcards = ""  #  board afer summary  2c2d2h/3h/4h always 3 max flop?
        self.winner = ""  # "and won summary", or show down?
        self.players = {}  # {'BB':'Jack', 'BTN':'John'}

        # utility attributes
        self.hand_file = hand_file
        self.max_seat = 0  # no used
        self.btn_seat = 0
        self.part_dict = {}
        self.player_list = []
        self.player_inv_dict = {}  # for given name, gives the position

        self.part_parse()
        self.parse_hand()
        self.parse_sequence()
        self.parse_summary()

    def part_parse(self):
        """
        Return a dict of the different division of the hand history
        Not all hands have the name number of parts, it return a dict with the part name as key and content as value
        """
        parts = []
        for part in re.split('\*\*\* ([A-Z- ]+) \*\*\*', self.hand_file):  # return [ 'part1', 'splitter1', 'part2',..
            parts.append(part)

        for i in range(0, len(parts)):
            if i == 0:
                self.part_dict['HEADER'] = parts[i].split('\n')
            if i % 2 != 0:  # number is odd
                # print(type(parts[i]))
                self.part_dict[parts[i]] = parts[i+1].split('\n')

    def parse_hand(self):
        gen_line = (yield_line for yield_line in self.hand_file.split('\n'))  # splits current hand into lines

        #####################
        # BTN and max seats #
        #####################

        for line in gen_line:
            if line[0:5] == "Poker":
                # print("header",  line)
                reg_blind = re.search("\(\$?([0-9-.]+)/\$?([0-9-.]+)( USD)?\)", line)
                self.blind = [reg_blind.group(1), reg_blind.group(2)]
            if line[0:5] == "Table":  # retrieve max number of sets and btn position

                self.btn_seat = int(re.search('#(.)', line).group(1))
                self.max_seat = int(re.search('(.)-max', line).group(1))  # regex for finding the maximum number of seat (?-max)

                break

        #####################################
        # Player names, stacks and position #
        #####################################
        stacks_temp = {}
        for line in gen_line:  # fill player dictonary and stacks dictionnary
            if line[0:4] != "Seat":
                break
            reg_player = re.search('(.): (.+) \(\$?([0-9-.]+)', line)
            player_num_seat = int(reg_player.group(1))
            player_name = reg_player.group(2)
            player_stacks = float(reg_player.group(3))

            self.player_list.append(player_name)

            # define BTN player
            if player_num_seat == self.btn_seat:
                self.players["BTN"] = player_name

            # temporary stacks dict
            stacks_temp[player_name] = player_stacks

        self.position()

        # add value of stacks by position in self.stacks
        for tuple_dict in stacks_temp.items():  # fixme python 2.7?
            self.stacks[self.player_inv_dict[tuple_dict[0]]] = tuple_dict[1]

        ##################
        # Check for ante #
        ##################

        for line in gen_line:
            try:
                self.ante = re.search('the ante ([0-9]+)', line).group(1)
            except:
                pass

    def parse_sequence(self):
        """
        Get sequence, and hole cards.
        :return:
        """
        def craft_seq(line_, previous_amount):
            if "raises" in line_:
                raised = float(re.search('to \$?([0-9-.]+)', line_).group(1))
                return "r"+"{0:.2f}".format(raised+previous_amount), raised
            if "bets" in line_:
                bet = float(re.search(' \$?([0-9-.]+)', line_).group(1))
                return "r"+"{0:.2f}".format(bet+previous_amount), bet
            if "folds" in line_:
                return "f", 0
            if "calls" in line_ or "check" in line_:
                return "c", 0
            else:
                return "", 0

        # add player hole cards
        try:
            reg_holecard = re.search("Dealt to (.+) \[(.+)\]", self.part_dict["HOLE CARDS"][1])  # group1 name, 2 card value
            self.holecards[self.player_inv_dict[reg_holecard.group(1)]] = reg_holecard.group(2).replace(' ', '')
        except:
            pass

        amount1 = 0
        amount_temp = 0
        for line in self.part_dict["HOLE CARDS"]:  # preflop (key error when files have more than 2\n between hands
            self.sequence += craft_seq(line, amount1)[0]
            amount_temp += craft_seq(line, amount1)[1]
        amount1 += amount_temp

        amount2 = 0
        amount_temp = 0
        self.sequence += "/"
        try:
            for line in self.part_dict["FLOP"]:
                self.sequence += craft_seq(line, amount1)[0]
                amount_temp += craft_seq(line, amount1)[1]
            amount2 += amount_temp
        except:
            pass

        amount3 = 0
        amount_temp = 0
        self.sequence += "/"
        try:
            for line in self.part_dict["TURN"]:
                self.sequence += craft_seq(line, amount2)[0]
                amount_temp += craft_seq(line, amount2)[1]
                amount3 += amount_temp
        except:
            pass

        self.sequence += "/"
        if self.part_dict.get("RIVER", None) is not None:
            for line in self.part_dict["RIVER"]:
                self.sequence += craft_seq(line, amount3)[0]

        # add other players holecards
        if self.part_dict.get("SHOW DOWN", None) is not None:
            for line in self.part_dict["SHOW DOWN"]:
                try:
                    reg_show = re.search("(.+): shows \[(.+)\]", line)
                    self.holecards[self.player_inv_dict[reg_show.group(1)]] = reg_show.group(2).replace(' ', '')
                except:
                    pass
        # print("Sequence: ", self.sequence)
        # print("Holecards: ", self.holecards)

    def parse_summary(self):
        """
        Get bordcards and winner name
        :return:
        """
        for line in self.part_dict["SUMMARY"]:

            if line[0:5] == "Board":
                reg_boardcards = re.search("\[(.+)\]", line).group(1).split(' ')  # board element into list

                for i, item in enumerate(reg_boardcards):  # split the list with '/', function of flop/turn/river
                    if i == 3 or i == 4:  # assuming there is a max of 3 flop
                        self.boardcards += '/' + item
                    else:
                        self.boardcards += item

            if "and won" in line or "collected" in line:  # fixme sometime things between player and showed, get other win cases
                self.winner = re.search('Seat [0-9]: (\w+) ', line).group(1)  # assuming there is always "showed" when "won"
                # print("Winner: ", self.winner)

    def position(self):
        """
        Uses self.player_list, and player btn already defined in self.players
        BB blind always the last ?

        from itertools import cycle
        cycle(laliste)

        list of list with position name; if player list match the same len, select the sublist

        :return:
        """
        pos_name_lst = [
            ["BTN", "BB"],
            ["BTN", "SB", "BB"],
            ["BTN", "SB", "BB", "CO"],
            ["BTN", "SB", "BB", "UTG", "CO"],
            ["BTN", "SB", "BB", "UTG", "MP1", "CO"],
            ["BTN", "SB", "BB", "UTG", "MP1", "MP2", "CO"],
            ["BTN", "SB", "BB", "UTG", "MP1", "MP2", "MP3", "CO"],
            ["BTN", "SB", "BB", "UTG", "UTG+1", "MP1", "MP2", "MP3", "CO"],
            ["BTN", "SB", "BB", "UTG", "UTG+1", "UTG+2", "MP1", "MP2", "MP3", "CO"],
        ]

        def shift(list_p, btn_player):
            """
            Shift the list of player for starting with the buttun player
            :param list_p:
            :param btn_player:
            :return:
            """
            flag = True
            x = 0
            while flag:
                if list_p[0] == btn_player:
                    return list_p
                x += 1
                list_p = list_p[-x:] + list_p[:-x]


        for sublist in pos_name_lst:
            if len(sublist) == len(self.player_list):
                player_lst_cy = shift(self.player_list, self.players['BTN'])
                for player, pos in zip(player_lst_cy, sublist):

                    self.players[pos] = player

        # Build a reverse dict
        for tuple_dict in self.players.items():  # fixme python 2.7?
            self.player_inv_dict[tuple_dict[1]] = tuple_dict[0]
        # print(self.players)
        # print(self.player_inv_dict)

def PS2acpc(ps_text):
    instance = Hand_history(ps_text)
    ante = instance.ante
    blind = instance.blind
    stacks = instance.stacks
    sequence = instance.sequence
    holecards = instance.holecards
    boardcards = instance.boardcards
    winner = instance.winner
    players = instance.players
    return ante, blind, stacks, sequence, holecards,  boardcards, winner, players


def acpc2PS(stacks, sequence, holecards,  boardcards, winner, players=None, ante=10, blind=[10, 20]):
    """
    Write default args, payers=None

    Need to:
    - order players by position, as a list
    - reverse dict of players

    """
    #####################
    # "Processing" part #
    #####################
    pos_name_lst = [
        ["BTN", "BB"],
        ["BTN", "SB", "BB"],
        ["CO", "BTN", "SB", "BB"],
        ["UTG", "CO", "BTN", "SB", "BB"],
        ["UTG", "MP", "CO", "BTN", "SB", "BB"],
        ["UTG", "MP1", "MP2", "CO", "BTN", "SB", "BB"],
        ["UTG", "MP1", "MP2", "MP3", "CO", "BTN", "SB", "BB"],
        ["UTG", "UTG+1", "MP1", "MP2", "MP3", "CO", "BTN", "SB", "BB"],
        ["UTG", "UTG+1", "UTG+2", "MP1", "MP2", "MP3", "CO", "BTN", "SB", "BB"],
    ]

    # append players in an ordered list, and a reverse dict for players
    order_players = []
    inv_dict_player = {}
    sublist_ = []
    for sublist in pos_name_lst:
        if len(sublist) == len(players):
            sublist_ = sublist
            for pos in sublist:
                order_players.append(players[pos])
                inv_dict_player[players[pos]] = pos
    # print(order_players)
    # print(inv_dict_player)

    split_sequence = sequence.split("/")
    def sequence_parser(splt_seq):
        return re.findall("([a-z][0-9-.]*)", splt_seq, re.DOTALL)

    split_bordcard = boardcards.split("/")
    def write_board(splitboard, str_part, j):
        """
        Craft the different section names with correspondant boardcards
        """
        try:
            board_str = "\n*** {} ***".format(str_part)
            for k in range(0, j + 1):
                list_cards = [splitboard[k][i:i + 2] for i in
                              range(0, len(splitboard[k]), 2)]  # split every 2 char, to seperate cards
                # return "\n*** {} *** [{}]".format(str_part, ' '.join(list_cards))
                board_str += " [{}]".format(' '.join(list_cards))
            return board_str
        except:
            return ""

    def default_player():
        return "Hero"
    game_player = default_player()

    def is_allin():
        return ""

    def pot():
        return "POT!!!!!"

    def rake():
        return "RAKE!!!!"

    def player_actions(ord_play, seq_part, holecards, boardcard, player):
        """
        With the given informations, maybe more, returns a nested list, for each parts (preflop, flop..)
        [[["player_name","raises", int_from, int_to],["player_name","bet",int_bet]..],
        [..]]
        :param ord_play: 
        :param seq_part: 
        :return: 
        """
        # example for the third hand, on holecards
        players_actions = [[["mazi61", "folds"],
                            ["Hero", "raises", 0.2, 0.3],
                            ["..."]],
                           ["..."]]
        return players_actions
        # """
        # For a given part (pre flop..), and the correspunding parsed sequence, and player order,
        # Returns:
        # 
        # """
        # try:
        # 
        #     def calls():
        #         return "CALLS!!!!!!"
        # 
        #     def min_raise(sequence):
        #         return "MINRAISE_NUMBER"
        # 
        # 
        #     return_str = ""
        #     flag_bet = False if flag_preflop else True  # flagpreflop tell that raise is first
        #     # TODO raise/bet
        #     for player, action in zip(ord_play, seq_part):
        #         if action == 'f':
        #             return_str += "\n{}: folds".format(player)
        #         if action == 'c':
        #             return_str += "\n{}: calls {}".format(player, calls())
        #         if action[0] == 'r' and not flag_bet:
        #             return_str += "\n{}: raises {} to {}".format(player, min_raise("seq"), action[1:])
        #             flag_bet_temp = True  # then it is bet for the preflop round?
        #             # bet always first, exept first round
        #         if action[0] == 'r' and flag_bet:
        #             return_str += "\n{}: bets {}".format(player, action[1:])
        #             flag_bet_temp = False  # the its raise
        #         flag_bet = flag_bet_temp
        # 
        #     return return_str
        # except:
        #     return ""


    def write_actions(actions):
        """
        Read from recorded actions of a part from the nested list
        """
        ret_str = ""
        for action in actions:
            if action[1] == 'folds':
                ret_str += "\n{}: folds".format(action[0])
            if action[1] == 'calls':
                ret_str += "\n{}: calls {}".format(action[0], action[2])
            if action[1] == 'checks':
                ret_str += "\n{}: checks".format(action[0])
            if action[1] == 'raises':
                ret_str += "\n{}: raises {} to {}".format(action[0], action[2], action[3])
            if action[1] == 'bet':
                ret_str += "\n{}: bet {} ".format(action[0], action[2])
            if action[1] == 'collected':
                ret_str += "\n{}: collected {} from pot ".format(action[0], action[2])
                
    def write_action_summary(action_list):
        """
        Take the output of player_actions(), and make a summary of theyre actions, in a dict with play_name as key
        """
        summary_dict = {}
        #preflop
        for action in action_list[0]:
            if action[1] == 'folds':
                summary_dict[action[0]] = "folded before Flop"
            if action[1] == 'collected':
                summary_dict[action[0]] = " collected ({}) ".format(action[2])

        #flop
        for action in action_list[0]:
            if action[1] == 'folds':
                summary_dict[action[0]] = "folded on Flop"
            if action[1] == 'collected':
                summary_dict[action[0]] = " collected ({}) ".format(action[2])


        #turn
        for action in action_list[2]:
            if action[1] == 'folds':
                summary_dict[action[0]] = "folded on the Turn"
            if action[1] == 'collected':
                summary_dict[action[0]] = " collected ({}) ".format(action[2])

    ###################
    # "Writting" part #
    ###################

    ret_string = ""
    play_stack_str = ""
    btn_num = 0

    # build header
    header = "PokerStars Hand #XXX: Tournament #XXX, $2.00+$2.00+$0.40 USD Hold'em No" \
             "Limit - Level XVIII ({}/{})  - 2016/07/29 23:25:05 MSK [2016/07/29 16:25:05 ET]\n" \
             "Table '1618015625 40' 9-max Seat #{} is the button".format(blind[0], blind[1], btn_num)

    #build player_stack_str
    for i, player in enumerate(order_players):
        # ret_string += "Seat "+i+" "+str(players[player_pos] if players[player_pos] is not None else "Player"+i)
        play_stack_str += "\nSeat {} {} ({} in chips)".format(i, player, stacks[sublist_[i]])  # todo i+1?
        if player == players['BTN']:
            btn_num = i

    # TODO ants..
    # small/big lbind posts
    try:
        blind_str = "\n{}: posts small bling {}".format(players['SB'], blind[0])
    except:
        blind_str = "\n{}: posts small bling {}".format(players['BTN'], blind[0])  # when 2 players, BTN is also SB
    blind_str += "\n{}: posts small bling {}".format(players['BB'], blind[1])

    # holecards str
    holecards_str = "\n*** HOLE CARDS ***"


    # the "dealt" part
    holecards_str += "\nDealt to {} [{}]".format(game_player, holecards[inv_dict_player[game_player]])




    # actions for holecards [0], True because preflop
    # holecards_str += player_actions(order_players, sequence_parser(split_sequence[0]))

    # write the pending boardcards
    flop_str = write_board(split_bordcard, "FLOP", 0)
    # todo actions for flop
    turn_str = write_board(split_bordcard, "TURN", 1)
    river_str = write_board(split_bordcard, "RIVER", 2)
    
    #############
    # Show down #
    #############

    ###########
    # SUMMARY #
    ###########

    summary_str = "\n*** SUMMARY ***\n" \
                  "Total pot {} | Rake {}\n".format(pot(), rake())

    # make the boardcard summary todo
    final_board = boardcards.replace("/", "")
    list_board = [final_board[i:i + 2] for i in range(0, len(final_board), 2)]
    summary_str += "Board [{}]".format(' '.join(list_board))

    string_pos_dict = {'BTN': 'button', 'SB': 'small blind', 'BB': 'big blind'}
    for i, player in enumerate(order_players):
        summary_str += "\nSeat {}: {} {}".format(i, player,  '('+string_pos_dict[sublist_[i]]+')'
        if sublist_[i] in ['BTN', 'SB', 'BB'] else "")
        if player == winner:
            summary_str += " won"

    # craft return string
    ret_string += header
    ret_string += play_stack_str
    ret_string += blind_str
    ret_string += holecards_str
    ret_string += flop_str
    ret_string += turn_str
    ret_string += river_str
    ret_string += summary_str

    return ret_string


if __name__ == '__main__':
    hands = open('hands_example.txt').read().split('\n\n')

    # help(firepoker)

    for hand in hands:
        # Hand_history(hand)
        ante, blind, stacks, sequence, holecards, boardcards, winner, players = PS2acpc(hand)
        print("\n\n\nHand results:")
        print("Ante: ", ante, "Stacks: ", stacks, "Sequence: ", sequence)
        print("Holecards: ", holecards, "Boardcards: ", boardcards)
        print("Winner: ", winner, "Players: ", players)

        hand_conv = acpc2PS(stacks, sequence, holecards,  boardcards, winner, players, ante, blind)
        print(hand_conv)

        break