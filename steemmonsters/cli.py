from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import bytes, int, str
from cmd import Cmd
from steemmonsters.api import Api
from steemmonsters.constants import xp_level, max_level_rarity
from steemmonsters.utils import generate_key, generate_team_hash, get_summoner_level, convert_team_id_to_string, get_cards_collection, convert_team_string_to_id, expand_short_form
from beem.blockchain import Blockchain
from beem.nodelist import NodeList
from beem import Steem
from beem.account import Account
from beembase import memo as BtsMemo
from beemgraphenebase.account import PrivateKey, PublicKey
import argparse
import json
import getpass
import random
import hashlib
from collections import OrderedDict
from datetime import date, datetime, timedelta
import requests
import logging
import os
from os.path import exists
from os.path import expanduser
import math
from prettytable import PrettyTable
import six
from time import sleep
import urllib

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig()

timeFormat = '%Y-%m-%dT%H:%M:%S.%fZ'

try:
    import colorama
    colorama.init()
except ImportError:
    colorama = None

try:
    from termcolor import colored
except ImportError:
    def colored(text, color):
        return text


def log(string, color, font="slant"):
    six.print_(colored(string, color))


def read_config_json(config_json, verbose=True):
    if not exists(config_json):
        if verbose:
            print("Could not find config json: %s" % config_json)
        sm_config = {}
    else:
        sm_config = json.loads(open(config_json).read())
    return sm_config


class SMPrompt(Cmd):
    prompt = 'sm> '
    intro = "Welcome to steemmonsters! Type ? to list commands"
    account = ""
    wallet_pass = ""
    api = Api()
    settings = api.settings()
    max_batch_size = 50
    threading = False
    wss = False
    https = True
    normal = False
    appbase = True
    config_file_name = "config.json"
    sm_config = read_config_json(config_file_name, verbose=False)
    if "account" in sm_config:
        account = sm_config["account"]
    if "wallet_password" in sm_config:
        wallet_pass = sm_config["wallet_password"]
    else:
        wallet_pass = getpass.getpass(prompt='Enter the beem wallet password.')
    if "match_type" in sm_config:
        match_type = sm_config["match_type"]
    else:
        match_type = "Ranked"
    nodes = NodeList()
    nodes.update_nodes()
    nodelist = nodes.get_nodes(normal=normal, appbase=appbase, wss=wss, https=https)
    stm = Steem(node=nodelist, num_retries=5, call_num_retries=3, timeout=15)
    stm.wallet.unlock(wallet_pass)
    b = Blockchain(mode='head', steem_instance=stm)
    cards = {}
    cards_by_name = {}
    for r in api.get_card_details():
        cards[r["id"]] = r
        cards_by_name[r["name"]] = r

    def do_exit(self, inp):
        print("Bye")
        return True

    def do_quit(self, inp):
        print("Bye")
        return True

    def help_exit(self):
        print('exit the application. Shorthand: x q Ctrl-D.')

    def do_setaccount(self, inp):
        self.account = inp
        print("setting '{}'".format(inp))

    def help_setaccount(self):
        print("changes the account name")

    def do_set_account(self, inp):
        self.account = inp
        print("setting '{}'".format(inp))

    def help_set_account(self):
        print("changes the account name")

    def do_reload_config(self, inp):
        if inp == "":
            inp = self.config_file_name
        else:
            self.config_file_name = inp
        self.sm_config = read_config_json(inp)
        if "account" in self.sm_config:
            self.account = self.sm_config["account"]
        if "match_type" in self.sm_config:
            self.match_type = self.sm_config["match_type"]

    def help_reload_config(self):
        print("Reloads the config, a new config files can be given as parameter")

    def do_show_config(self, inp):
        tx = json.dumps(self.sm_config, indent=4)
        print(tx)

    def help_show_config(self):
        print("Shows the loaded config file")

    def do_collection(self, inp):
        if inp == "":
            if self.account == "":
                print("No account set... aborting...")
                return
            cards = self.api.get_collection(self.account)
        else:
            cards = self.api.get_collection(inp)
        t = PrettyTable(["uid", "card", "xp", "gold", "edition"])
        t.align = "l"
        for c in cards["cards"]:
            t.add_row([c["uid"], self.cards[c["card_detail_id"]]["name"], c["xp"], c["gold"], c["edition"]])        
        print(t)

    def help_collection(self):
        print("Shows the owned cards, an account name can be given as parameter")

    def do_conflict(self, inp):
        self.settings = self.api.settings()
        ranked_settings = self.settings["ranked_settings"]
        tx = json.dumps(ranked_settings, indent=4)
        print(tx)

    def help_conflict(self):
        print("Show current conflict")

    def do_packs(self, inp):
        if self.account == "":
            print("No account set... aborting...")
            return        
        if inp == "":
            account = self.account
        else:
            account = inp
        response = self.api.get_player_login(account)
        acc = Account(account, steem_instance=self.stm)
        wif = self.stm.wallet.getPrivateKeyForPublicKey(acc["posting"]["key_auths"][0][0])
        token = BtsMemo.decode_memo(PrivateKey(wif), response["token"]).replace('\n', '')
        response = self.api.get_cards_packs(account, token)
        if len(response["packs"]) == 0:
            print("No pack available")
            return        
        t = PrettyTable(["index", "uid", "edition"])
        t.align = "l"
        index = 0
        for p in response["packs"]:
            t.add_row(["%d" % index, p["uid"], p["edition"]])
            index += 1        
        print(t)

    def help_packs(self):
        print("Show packs")

    def do_openpack(self, inp):
        if self.account == "":
            print("No account set... aborting...")
            return

        account = self.account
        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        response = self.api.get_player_login(account)
        acc = Account(account, steem_instance=self.stm)        
        wif = self.stm.wallet.getPrivateKeyForPublicKey(acc["posting"]["key_auths"][0][0])
        token = BtsMemo.decode_memo(PrivateKey(wif), response["token"]).replace('\n', '')
        response = self.api.get_cards_packs(account, token)
        if len(response["packs"]) == 0:
            print("No pack available")
            return
        t = PrettyTable(["index", "uid", "edition"])
        t.align = "l"
        index = 0
        for p in response["packs"]:
            t.add_row(["%d" % index, p["uid"], p["edition"]])
            index += 1
        print(t)
        if six.PY3:
            index = int(input("Please enter pack index to open: "))
        else:
            index = int(raw_input("Please enter pack index to open: "))
        edition = response["packs"][index]["edition"]
        response = self.api.get_open_packs(response["packs"][index]["uid"], account, response["packs"][index]["edition"], token)
        cards = response["cards"]
        t = PrettyTable(["card", "gold", "market value"])
        all_cards = self.api.get_market_for_sale_grouped()
        t.align = "l"
        for c in cards:
            for ac in all_cards:
                if ac["gold"] == c["gold"] and c["card_detail_id"] == ac["card_detail_id"] and ac["edition"] == edition:
                    card_value = ac["low_price"]
                    break
            t.add_row([self.cards[c["card_detail_id"]]["name"], c["gold"], "%.2f $" % card_value])
        print(t)

    def help_openpack(self):
        print("openpack - Open a pack")


    def do_giftpacks(self, inp):
        if self.account == "":
            print("No account set... aborting...")
            return
        try:
            to_account = Account(inp, steem_instance=self.stm)
        except:
            print("%s is not a valid account" % inp)
            return
        response = self.api.get_player_details(to_account["name"])
        if "error" in response:
            print("%s is not a valid steemmonsters account" % inp)
            return
        account = self.account
        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        response = self.api.get_player_login(account)
        acc = Account(account, steem_instance=self.stm)        
        wif = self.stm.wallet.getPrivateKeyForPublicKey(acc["posting"]["key_auths"][0][0])
        token = BtsMemo.decode_memo(PrivateKey(wif), response["token"]).replace('\n', '')
        response = self.api.get_cards_packs(account, token)
        if len(response["packs"]) == 0:
            print("No pack available")
            return
        print(json.dumps(response, indent=4))
        if six.PY3:
            qty = int(input("Please enter quantity to gift to %s: " % to_account["name"]))
            edition = int(input("Please enter packs edition (0 - alpha, 1 - beta) to gift to %s: " % to_account["name"]))
        else:
            qty = int(raw_input("Please enter quantity to gift to %s: " % to_account["name"]))
            edition = int(raw_input("Please enter packs edition (0 - alpha, 1 - beta) to gift to %s: " % to_account["name"]))
        json_dict = {"to": to_account["name"], "qty": qty, "edition": edition}
        self.stm.custom_json('sm_gift_packs', json_dict, required_posting_auths=[acc["name"]])
        print("sm_gift_packs broadcasted!")
        sleep(3)

    def help_giftpacks(self):
        print("giftpacks <player> - Gift a packs to a different player")

    def do_team(self, inp):
        if inp not in self.sm_config["decks"]:
            account = self.account
            mana_cap = self.settings["ranked_settings"]["mana_cap"]
            response = self.api.get_player_login(account)
            acc = Account(account, steem_instance=self.stm)
            wif = self.stm.wallet.getPrivateKeyForPublicKey(acc["posting"]["key_auths"][0][0])
            token = BtsMemo.decode_memo(PrivateKey(wif), response["token"]).replace('\n', '')
            response = self.api.get_player_saved_teams(account, token, mana_cap)
            decks = convert_team_id_to_string(response, self.cards)
            if inp in decks:
                deck_ids = decks[inp]
            else:
                print("Could not find %s in saved decks" % inp)
                return
        else:
            deck_ids = self.sm_config["decks"][inp]
        tx = json.dumps(deck_ids, indent=4)
        print(tx)

    def help_team(self):
        print("Shows defined team for given identifier")

    def do_ranking(self, inp):
        if inp == "":
            if self.account == "":
                print("No account set... aborting...")
                return
            account = self.account
        else:
            account = inp
        response = self.api.get_player_details(account)
        tx = json.dumps(response, indent=4)
        print(tx)

    def help_ranking(self):
        print("Shows ranking, a account name can also be given.")

    def do_quest(self, inp):
        if inp == "":
            if self.account == "":
                print("No account set... aborting...")
                return
            account = self.account
        else:
            account = inp
        response = self.api.get_player_quests(account)
        if isinstance(response, list) and len(response) == 1:
            response = response[0]
        print("Current quest: %s" % response["name"])
        if response["claim_trx_id"] is None:
            print("Current quest is not completed (%d / %d)" % (response["completed_items"], response["total_items"]))
        else:
            print("Current quest is completed (%d / %d)" % (response["completed_items"], response["total_items"]))
        if (datetime.utcnow() - datetime.strptime(response["created_date"], timeFormat)).total_seconds() / 60 / 60 < 24:
            print("Please wait %.2f h" % (24 - (datetime.utcnow() - datetime.strptime(response["created_date"], timeFormat)).total_seconds() / 60 / 60))
        # tx = json.dumps(response, indent=4)
        # print(tx)

    def help_quest(self):
        print("Shows quest, a account name can also be given.")

    def do_player(self, inp):
        if inp == "":
            if self.account == "":
                print("No account set... aborting...")
                return
            account = self.account
        else:
            account = inp
        response = self.api.get_player_details(account)
        tx = json.dumps(response, indent=4)
        print(tx)

    def help_player(self):
        print("Shows player, a account name can also be given.")

    def do_lastteam(self, inp):
        if inp == "":
            if self.account == "":
                print("No account set... aborting...")
                return
            account = self.account
        else:
            account = inp
        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        response = self.api.get_player_teams_last_used(account, mana_cap)
        if len(response) == 0:
            print("Error in loading last team...")
            return
        summoner = response["summoner"]
        monsters = response["monsters"]
        monsters_list = []
        for m in monsters:
            monsters_list.append(self.cards[m["id"]]["name"])
        deck = ", ".join([self.cards[summoner["id"]]["name"]] + monsters_list)
        print(deck)

    def help_lastteam(self):
        print("Shows quest, a account name can also be given.")

    def do_lasttopteam(self, inp):
        if inp == "":
            print("Give a number between 1 and 100")
            return
        elif int(inp) < 1 or int(inp) > 100:
            print("Give a number between 1 and 100")
            return
        leaderboard = self.api.players_leaderboard()
        account = leaderboard[int(inp) - 1]["player"]
        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        response = self.api.get_player_teams_last_used(account, mana_cap)
        if len(response) == 0:
            print("Error in loading last team...")
            return
        summoner = response["summoner"]
        monsters = response["monsters"]
        monsters_list = []
        for m in monsters:
            monsters_list.append(self.cards[m["id"]]["name"])
        deck = ", ".join([self.cards[summoner["id"]]["name"]] + monsters_list)
        print(deck)

    def help_lasttopteam(self):
        print("Shows last played team from the top, a account name can also be given.")

    def do_copytopteam(self, inp):
        if inp == "":
            print("Give a number between 1 and 100")
            return
        account_number = inp.split(' ')[0]
        if int(account_number) < 1 or int(account_number) > 100:
            print("Give a number between 1 and 100")
            return
        leaderboard = self.api.players_leaderboard()
        account = leaderboard[int(account_number) - 1]["player"]
        deck_name = inp[len(account_number) + 1:]
        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        response = self.api.get_player_teams_last_used(account, mana_cap)
        if len(response) == 0:
            print("Error in loading last team...")
            return
        summoner = response["summoner"]
        monsters = response["monsters"]
        team = OrderedDict({"summoner": summoner, "monsters": monsters})
        if six.PY2:
            team_enc = urllib.quote_plus(json.dumps(team))
        else:
            team_enc = urllib.parse.quote_plus(json.dumps(team))
        account = self.account
        response = self.api.get_player_login(account)
        acc = Account(account, steem_instance=self.stm)
        wif = self.stm.wallet.getPrivateKeyForPublicKey(acc["posting"]["key_auths"][0][0])
        token = BtsMemo.decode_memo(PrivateKey(wif), response["token"]).replace('\n', '')
        print(self.api.player_save_team(deck_name, team_enc, account, token, mana_cap))

    def help_copytopteam(self):
        print("copytopteam <number> <deckname>")

    def do_copyteam(self, inp):
        if inp == "":
            print("No player name and deckname given.")
            return            
        if self.account == "":
            print("No account set... aborting...")
            return
        account = inp.split(' ')[0]
        deck_name = inp[len(account) + 1:]
        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        response = self.api.get_player_teams_last_used(account, mana_cap)
        if len(response) == 0:
            print("Error in loading last team...")
            return
        summoner = response["summoner"]
        monsters = response["monsters"]
        team = OrderedDict({"summoner": summoner, "monsters": monsters})
        if six.PY2:
            team_enc = urllib.quote_plus(json.dumps(team))
        else:
            team_enc = urllib.parse.quote_plus(json.dumps(team))
        account = self.account
        response = self.api.get_player_login(account)
        acc = Account(account, steem_instance=self.stm)
        wif = self.stm.wallet.getPrivateKeyForPublicKey(acc["posting"]["key_auths"][0][0])
        token = BtsMemo.decode_memo(PrivateKey(wif), response["token"]).replace('\n', '')
        print(self.api.player_save_team(deck_name, team_enc, account, token, mana_cap))

    def help_copyteam(self):
        print("copyteam <player> <deckname>")

    def do_addteam(self, inp):
        if inp == "":
            print("No deckname given...")
            return            
        if self.account == "":
            print("No account set... aborting...")
            return
        account = self.account
        acc = Account(account, steem_instance=self.stm)
        response = self.api.get_collection(acc["name"])
        mycards = get_cards_collection(response, self.cards)

        deck_name = inp.split(' ')[0]
        cards = inp[len(deck_name) + 1:]
        if cards[0] in ["\t", "\n"]:
            cards = cards[1:]
        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        
        [summoner, monsters] = convert_team_string_to_id(cards, self.cards_by_name)
        if summoner["id"] not in mycards:
            print("%s is not in collection" % (self.cards[summoner["id"]]["name"]))
            return
        for m in monsters:
            if m["id"] not in mycards:
                print("%s is not in collection" % (self.cards[m["id"]]["name"]))
                return

        team = OrderedDict({"summoner": summoner, "monsters": monsters})
        if six.PY2:
            team_enc = urllib.quote_plus(json.dumps(team))
        else:
            team_enc = urllib.parse.quote_plus(json.dumps(team))

        response = self.api.get_player_login(account)

        wif = self.stm.wallet.getPrivateKeyForPublicKey(acc["posting"]["key_auths"][0][0])
        token = BtsMemo.decode_memo(PrivateKey(wif), response["token"]).replace('\n', '')
        print(self.api.player_save_team(deck_name, team_enc, account, token, mana_cap))

    def help_addteam(self):
        print("addteam <deckname> <cards>")

    def do_deleteteam(self, inp):
        if inp == "":
            print("no team name given")
            return
        if self.account == "":
            print("No account name set... aborting ...")
            return
        account = self.account
        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        response = self.api.get_player_login(account)
        acc = Account(account, steem_instance=self.stm)
        wif = self.stm.wallet.getPrivateKeyForPublicKey(acc["posting"]["key_auths"][0][0])
        token = BtsMemo.decode_memo(PrivateKey(wif), response["token"]).replace('\n', '')
        print(self.api.player_delete_team(inp, account, token, mana_cap))

    def help_deleteteam(self):
        print("deleteteam <deckname>")

    def do_savedteams(self, inp):
        if self.account == "":
            print("No account name set... aborting ...")
            return
        account = self.account
        decks = {}
        if "decks" in self.sm_config:
            decks = self.sm_config["decks"]        
        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        response = self.api.get_player_login(account)
        acc = Account(account, steem_instance=self.stm)
        wif = self.stm.wallet.getPrivateKeyForPublicKey(acc["posting"]["key_auths"][0][0])
        token = BtsMemo.decode_memo(PrivateKey(wif), response["token"]).replace('\n', '')
        response = self.api.get_player_saved_teams(account, token, mana_cap)
        deck_response = convert_team_id_to_string(response, self.cards)
        for d in deck_response:
            decks[d] = deck_response[d]        
        if inp == "":
            tx = json.dumps(decks, indent=4)
        else:
            tx = json.dumps(decks[inp], indent=4)
        print(tx)

    def help_savedteams(self):
        print("Shows saved teams.")

    def do_cancel(self, inp):
        if self.account == "":
            print("No account name set... aborting ...")
            return
        acc = Account(self.account, steem_instance=self.stm)
        self.stm.custom_json('sm_cancel_match', "{}", required_posting_auths=[acc["name"]])
        print("sm_cancel_match broadcasted!")
        sleep(3)

    def help_cancel(self):
        print("Broadcasts a custom_json with sm_cancel_match")

    def do_claimquest(self, inp):
        if self.account == "":
            print("No account name set... aborting ...")
            return
        acc = Account(self.account, steem_instance=self.stm)
        response = self.api.get_player_quests(acc["name"])
        if isinstance(response, list) and len(response) == 1:
            response = response[0]
        if response["claim_trx_id"] is not None:
            print("Current quest already claimed")
            return
        if response["completed_items"] < response["total_items"]:
            print("Current quest is not completed (%d / %d)" % (response["completed_items"], response["total_items"]))
            return
        json_dict = {"type": "quest", "quest_id": response["id"]}
        self.stm.custom_json('sm_claim_reward', json_dict, required_posting_auths=[acc["name"]])
        print("sm_claim_reward broadcasted!")
        sleep(3)

    def help_claimquest(self):
        print("Broadcasts a custom_json with sm_claim_reward")

    def do_startquest(self, inp):
        if self.account == "":
            print("No account name set... aborting ...")
            return
        acc = Account(self.account, steem_instance=self.stm)
        response = self.api.get_player_quests(acc["name"])
        if isinstance(response, list) and len(response) == 1:
            response = response[0]
        if response["claim_trx_id"] is None:
            print("Current quest is not completed (%d / %d)" % (response["completed_items"], response["total_items"]))
            return
        if (datetime.utcnow() - datetime.strptime(response["created_date"], timeFormat)).total_seconds() / 60 / 60 < 24:
            print("Please wait %.2fh" % (24 - (datetime.utcnow() - datetime.strptime(response["created_date"], timeFormat)).total_seconds() / 60 / 60))
            return
        json_dict = {"type": "daily"}
        self.stm.custom_json('sm_start_quest', json_dict, required_posting_auths=[acc["name"]])
        print("sm_start_quest broadcasted!")
        success = False
        cnt = 0
        while not success and cnt < 10:
            cnt += 1
            sleep(3)
            response = self.api.get_player_quests(acc["name"])
            if isinstance(response, list) and len(response) == 1:
                response = response[0]
            if (datetime.utcnow() - datetime.strptime(response["created_date"], timeFormat)).total_seconds() / 60 / 60 < 1.0:
                success = True
        quest_name = response["name"]
        for q in self.settings["quests"]:
            if q["name"] == quest_name:
                print(q["objective"])

    def help_startquest(self):
        print("Broadcasts a custom_json with sm_start_quest")

    def do_splinter(self, inp):
        if self.account == "":
            print("No account name set... aborting ...")
            return        
        splinter = inp.split(" ")[0].lower()
        if splinter == "water":
            splinter = "blue"
        elif splinter == "fire":
            splinter = "red"
        elif splinter == "earth":
            splinter = "green"
        elif splinter == "life":
            splinter = "white"
        elif splinter == "death":
            splinter = "black"
        elif splinter == "dragon":
            splinter = "gold"
        if len(inp.split(" ")) > 1:
            summoner_level = int(inp.split(" ")[1])
        else:
            summoner_level = 4
        stop_block = self.b.get_current_block_num()
        start_block = stop_block - 20 * 60 * 1
        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        ruleset = self.settings["ranked_settings"]["ruleset"]
        match_type = self.match_type
        acc = Account(self.account, steem_instance=self.stm)
        response = self.api.get_collection(acc["name"])
        mycards = get_cards_collection(response, self.cards)
        
        find_match_cnt = 0
        deck_score = {}
        conter_deck = {}
        cnt = 0
        last_id_block = []
        last_round_blocknum = start_block - 1
        block = start_block
        last_created_date = ""
        first_created_date = None
        while block <= stop_block:
            cnt += 1
            if cnt % 1 == 0:
                print("reading block %d - %s" % (block, last_created_date))
            response = ""
            cnt2 = 0
            while str(response) != '<Response [200]>' and cnt2 < 10:
                response = requests.get("https://steemmonsters.com/transactions/history?from_block=%d" % block)
                if str(response) != '<Response [200]>':
                    sleep(2)
                cnt2 += 1        
            for hist in response.json():
                if hist["type"] != "sm_team_reveal":
                    continue
                if not hist["success"]:
                    continue
                if hist["block_num"] > last_round_blocknum:
                    last_id_block = [hist["id"]]
                    last_round_blocknum = hist["block_num"]
                    block = last_round_blocknum
                elif hist["id"] not in last_id_block:
                    last_id_block.append(hist["id"])
                else:
                    continue
                last_created_date = hist["created_date"]
                if first_created_date is None:
                    first_created_date = hist["created_date"]
                result = json.loads(hist["result"])
                if "status" in result and result["status"] == "Waiting for opponent reveal.":
                    continue
                
                if "battle" in result:
                    if result["battle"]["mana_cap"] != mana_cap:
                        continue
                    deck_mana_cap = result["battle"]["mana_cap"]
                    deck_ruleset = result["battle"]["ruleset"]
                    if "details" in result["battle"]:
                        team1_summoner_level = get_summoner_level(result["battle"]["details"]["team1"]["summoner"], self.cards, xp_level, max_level_rarity)
                        team1 = [{"id": result["battle"]["details"]["team1"]["summoner"]["card_detail_id"], "level": result["battle"]["details"]["team1"]["summoner"]["level"]}]
                        for m in result["battle"]["details"]["team1"]["monsters"]:
                            team1.append({"id": m["card_detail_id"], "level": m["level"]})
                        team1_player = result["battle"]["details"]["team1"]["player"]
                        if team1_summoner_level != summoner_level:
                            continue
                        team2_summoner_level = get_summoner_level(result["battle"]["details"]["team2"]["summoner"], self.cards, xp_level, max_level_rarity)
                        team2 = [{"id": result["battle"]["details"]["team2"]["summoner"]["card_detail_id"], "level": result["battle"]["details"]["team2"]["summoner"]["level"]}]
                        for m in result["battle"]["details"]["team2"]["monsters"]:
                            team2.append({"id": m["card_detail_id"], "level": m["level"]})
                        team2_player = result["battle"]["details"]["team2"]["player"]
                        winner = result["battle"]["details"]["winner"] 
                        if team2_summoner_level != summoner_level:
                            continue                        
                    else:
                        continue
                else:
                    continue      
                
                team1_str = ""
                for t in team1:
                    if team1_str != "":
                        team1_str += ","
                    team1_str += str(t["id"])+"-"+str(t["level"])
                    
                team2_str = ""
                for t in team2:
                    if team2_str != "":
                        team2_str += ","
                    team2_str += str(t["id"])+"-"+str(t["level"])              
    
                
                if winner == team1_player:
                    if self.cards[team1[0]["id"]]["color"].lower() == splinter:
                        if team1_str in deck_score:
                            deck_score[team1_str]["n"] += 1
                            deck_score[team1_str]["score"] += 1
                            deck_score[team1_str]["win"] += 1
                        else:
                            deck_score[team1_str] = {"n": 1, "score": 1, "win": 1, "loose": 0, "mana_cap": deck_mana_cap, "ruleset": deck_ruleset}
                    if self.cards[team2[0]["id"]]["color"].lower() == splinter:
                        if team2_str in deck_score:
                            deck_score[team2_str]["n"] += 1
                            deck_score[team2_str]["score"] -= 1
                            deck_score[team2_str]["loose"] += 1
                        else:
                            deck_score[team2_str] = {"n": 1, "score": -1, "win": 0, "loose": 1, "mana_cap": deck_mana_cap, "ruleset": deck_ruleset}
                else:
                    if self.cards[team2[0]["id"]]["color"].lower() == splinter:
                        if team2_str in deck_score:
                            deck_score[team2_str]["n"] += 1
                            deck_score[team2_str]["score"] += 1
                            deck_score[team2_str]["win"] += 1
                        else:
                            deck_score[team2_str] = {"n": 1, "score": 1, "win": 1, "loose": 0, "mana_cap": deck_mana_cap, "ruleset": deck_ruleset}
                    if self.cards[team1[0]["id"]]["color"].lower() == splinter:
                        if team1_str in deck_score:
                            deck_score[team1_str]["n"] += 1
                            deck_score[team1_str]["score"] -= 1
                            deck_score[team1_str]["loose"] += 1
                        else:
                            deck_score[team1_str] = {"n": 1, "score": -1, "win": 0, "loose": 1, "mana_cap": deck_mana_cap, "ruleset": deck_ruleset}
        deck_score_list = []
        for d in deck_score:
            if deck_score[d]["mana_cap"] != mana_cap:
                continue
            deck_score_list.append(deck_score[d])
            deck_score_list[-1]["deck"] = d
        sorted_deck = sorted(deck_score_list, key=lambda x: x["win"] / x["n"], reverse=True)
        t = PrettyTable(["n", "win ratio", "summoner", "monsters"])
        t.align = "l"
        index = 0
        for deck in sorted_deck[:15]:
            [summoner_str, monster_str] = expand_short_form(deck["deck"], self.cards)
            t.add_row(["%d" % index, "%.2f %%" % (deck["win"] / (deck["win"] + deck["loose"]) * 100), summoner_str, monster_str])        
            index += 1
        deck_selected = False
        while not deck_selected:
            print(t)
            try:
                if six.PY3:
                    value = input("Select deck number: ")
                    if value == "":
                        continue
                    deck_index = int(value)
                else:
                    value = raw_input("Select deck number: ")
                    if value == "":
                        continue
                    deck_index = int(value)                
            except KeyboardInterrupt:
                print("Exiting cleanly...")
                return            

            mana_cap = self.settings["ranked_settings"]["mana_cap"]
            deck_selected = True
            [summoner, monsters] = expand_short_form(sorted_deck[deck_index]["deck"], self.cards, output_type="id")
            if summoner["id"] not in mycards:
                print("%s is not in collection" % (self.cards[summoner["id"]]["name"]))
                deck_selected = False
                continue
            for m in monsters:
                if m["id"] not in mycards:
                    print("%s is not in collection" % (self.cards[m["id"]]["name"]))
                    deck_selected = False
                    continue
        if six.PY3:
            team_name = input("Please enter team name: ")
        else:
            team_name = raw_input("Please enter team name: ")        

        team = OrderedDict({"summoner": summoner, "monsters": monsters})
        if six.PY2:
            team_enc = urllib.quote_plus(json.dumps(team))
        else:
            team_enc = urllib.parse.quote_plus(json.dumps(team))

        response = self.api.get_player_login(acc["name"])

        wif = self.stm.wallet.getPrivateKeyForPublicKey(acc["posting"]["key_auths"][0][0])
        token = BtsMemo.decode_memo(PrivateKey(wif), response["token"]).replace('\n', '')
        print(self.api.player_save_team(team_name, team_enc, acc["name"], token, mana_cap))
        
    def help_splinter(self):
        print("splinter <splinter> returns different currently played teams.")

    def do_play(self, inp):
        if self.account == "":
            print("No account set... aborting...")
            return
        if inp == "":
            inp = "random"
        account = self.account
        quest_mode = False
        random_mode = False
        current_deck_index = 0
        decks = {}
        if "decks" in self.sm_config:
            decks = self.sm_config["decks"]
        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        response = self.api.get_player_login(account)
        acc = Account(account, steem_instance=self.stm)
        wif = self.stm.wallet.getPrivateKeyForPublicKey(acc["posting"]["key_auths"][0][0])
        token = BtsMemo.decode_memo(PrivateKey(wif), response["token"]).replace('\n', '')
        response = self.api.get_player_saved_teams(account, token, mana_cap)
        deck_response = convert_team_id_to_string(response, self.cards)
        for d in deck_response:
            decks[d] = deck_response[d]
        win_left = 0
        if inp[:6] == "quest ":
            inp = inp[6:]
            quest_mode = True
            
            response = self.api.get_player_quests(account)
            if isinstance(response, list) and len(response) == 1:
                response = response[0]        
            if response["claim_trx_id"] is None and response["completed_items"] < response["total_items"]:
                win_left = response["total_items"] - response["completed_items"]
        elif inp[:7] == "random ":
            inp = inp[7:]
            random_mode = True
        if inp not in ["random", "mirror"]:
            if "decks" not in self.sm_config or inp not in self.sm_config["decks"]:

                if inp.split(",")[0] in decks:
                    deck_ids = decks[inp.split(",")[0]]
                else:
                    print("Could not find %s in saved decks" % inp)
                    return
            else:
                deck_ids = decks[inp]

        statistics = {"won": 0, "battles": 0, "loosing_streak": 0,
                      "winning_streak": 0, "last_match_won": False, "last_match_lose": False}
        play_round = 0

        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        ruleset = self.settings["ranked_settings"]["ruleset"]
        match_type = self.match_type

        acc = Account(self.account, steem_instance=self.stm)

        response = self.api.get_player_details(acc["name"])
        print("%s rank: %s, rating: %d, battles: %d, "
              "wins: %d, cur. streak: %d" % (acc["name"], response["rank"], response["rating"],
                                             response["battles"], response["wins"], response["current_streak"]))

        response = self.api.get_collection(acc["name"])
        mycards = get_cards_collection(response, self.cards)

        continue_playing = True
        team_found = False
        while continue_playing and (self.sm_config["play_counter"] < 0 or play_round < self.sm_config["play_counter"] or quest_mode):
            if "play_inside_ranking_border" in self.sm_config and self.sm_config["play_inside_ranking_border"] and not quest_mode:
                ranking_border = self.sm_config["ranking_border"]
                response = self.api.get_player_details(acc["name"])
                if response["rating"] < ranking_border[0] or response["rating"] > ranking_border[1]:
                    print("Stop playing, rating %d outside [%d, %d]" % (response["rating"], ranking_border[0], ranking_border[1]))
                    continue_playing = False
                    continue
            if "stop_on_loosing_streak" in self.sm_config and self.sm_config["stop_on_loosing_streak"] > 0 and not quest_mode:
                if statistics["loosing_streak"] >= self.sm_config["stop_on_loosing_streak"]:
                    print("Stop playing, did lose %d times in a row" % (statistics["loosing_streak"]))
                    continue_playing = False
                    continue
            if quest_mode:
                response = self.api.get_player_quests(account)
                if isinstance(response, list) and len(response) == 1:
                    response = response[0]        
                if response["claim_trx_id"] is None and response["completed_items"] < response["total_items"]:
                    win_left = response["total_items"] - response["completed_items"]
                if win_left <= 0:
                    print("Stop playing, won enough times to solve the quest!")
                    continue_playing = False
                    continue                
            if inp == "random":
                deck_ids_list = list(self.sm_config["decks"].keys())
                deck_ids = self.sm_config["decks"][deck_ids_list[random.randint(0, len(deck_ids_list) - 1)]]
                print("Random mode: play %s" % str(deck_ids))
            elif inp == "mirror":
                if "switch_on_loosing_streak" in self.sm_config and self.sm_config["switch_on_loosing_streak"] > 0:
                    if statistics["loosing_streak"] >= self.sm_config["switch_on_loosing_streak"]:
                        team_found = False      
                elif statistics["last_match_lose"]:
                    team_found = False
                if "switch_on_winning_streak" in self.sm_config and self.sm_config["switch_on_winning_streak"] > 0:
                    if statistics["winning_streak"] >= self.sm_config["switch_on_winning_streak"]:
                        team_found = False              
                while not team_found:
                    rand_number = random.randint(0, 99)
                    leaderboard = self.api.players_leaderboard()
                    account = leaderboard[rand_number]["player"]
                    mana_cap = self.settings["ranked_settings"]["mana_cap"]
                    response = self.api.get_player_teams_last_used(account, mana_cap)
                    if len(response) == 0:
                        continue
                    deck_ids = convert_team_id_to_string(response, self.cards)

                    all_card_in_selection = True
                    for ids in deck_ids:
                        if isinstance(ids, str):
                            card_id = self.cards_by_name[ids.split(":")[0]]["id"]
                        else:
                            card_id = ids
                        if card_id not in mycards:
                            all_card_in_selection = False
                    if not all_card_in_selection:
                        continue
                    team_found = True
                    print("selected deck %s" % str(deck_ids))
            elif inp not in ["random", "mirror"] and len(inp.split(",")) > 0:
                change_team = False
                if "switch_on_loosing_streak" in self.sm_config and self.sm_config["switch_on_loosing_streak"] > 0:
                    if statistics["loosing_streak"] >= self.sm_config["switch_on_loosing_streak"]:
                        change_team = True
                elif statistics["last_match_lose"]:
                    change_team = True
                if "switch_on_winning_streak" in self.sm_config and self.sm_config["switch_on_winning_streak"] > 0:
                    if statistics["winning_streak"] >= self.sm_config["switch_on_winning_streak"]:
                        change_team = True          
                if change_team:
                    deck_list = inp.split(",")
                    if random_mode:
                        current_deck_index = random.randint(0, len(deck_list) - 1)
                    else:
                        current_deck_index += 1
                        if current_deck_index >= len(deck_list):
                            current_deck_index = 0
                    current_deck_name = inp.split(",")[current_deck_index].strip()
                    if current_deck_name in decks:
                        deck_ids = decks[current_deck_name]
                        print("Switch deck to %s" % str(current_deck_name))
                    else:
                        print("Could not find %s in saved decks" % current_deck_name)
                        return

            if play_round > 0 and "play_delay" in self.sm_config:
                if self.sm_config["play_delay"] >= 1:
                    print("waiting %d seconds" % self.sm_config["play_delay"])
                    try:
                        sleep(self.sm_config["play_delay"])
                    except KeyboardInterrupt:
                        print("Stop playing...")
                        return
            play_round += 1
            secret = generate_key(10)
            monsters = []
            summoner = None
            summoner_level = 4
            for ids in deck_ids:
                if isinstance(ids, str):
                    card_id = self.cards_by_name[ids.split(":")[0]]["id"]
                else:
                    card_id = ids

                if card_id not in mycards:
                    print("%s is not in collection" % (self.cards[card_id]["name"]))
                    return

                if summoner is None:
                    summoner = mycards[card_id]["uid"]
                    for x in xp_level:
                        if x["edition"] == mycards[card_id]["edition"] and x["rarity"] == self.cards[card_id]["rarity"]:
                            summoner_level = 0
                            for l in x["xp_level"]:
                                if mycards[card_id]["xp"] >= x["xp_level"][l]:
                                    summoner_level = l
                    summoner_level = int(math.ceil(summoner_level / max_level_rarity[self.cards[card_id]["rarity"]] * 4))
                else:
                    monsters.append(mycards[card_id]["uid"])

            deck = {"trx_id": "", "summoner": summoner, "monsters": monsters, "secret": secret}

            team_hash = generate_team_hash(deck["summoner"], deck["monsters"], deck["secret"])
            json_data = {"match_type": match_type, "mana_cap": mana_cap, "team_hash": team_hash, "summoner_level": summoner_level, "ruleset": ruleset}
            self.stm.custom_json('sm_find_match', json_data, required_posting_auths=[acc["name"]])
            print("sm_find_match broadcasted...")
            try:
                sleep(3)
            except KeyboardInterrupt:
                print("Exiting cleanly...")
                return
            found = False
            start_block_num = None
            for h in self.b.stream(opNames=["custom_json"]):
                if start_block_num is None:
                    start_block_num = h["block_num"]
                elif (h["block_num"] - start_block_num) * 20 > 60:
                    print("Could not find transaction id %s" % (deck["trx_id"]))
                    break
                if h["id"] == 'sm_find_match':
                    if json.loads(h['json'])["team_hash"] == team_hash:
                        found = True
                        break
            deck["trx_id"] = h['trx_id']
            block_num = h["block_num"]
            print("Transaction id found (%d - %s)" % (block_num, deck["trx_id"]))
            if not found:
                self.stm.custom_json('sm_cancel_match', "{}", required_posting_auths=[acc["name"]])
                try:
                    sleep(3)
                except KeyboardInterrupt:
                    print("Exiting cleanly...")
                    return
                continue

            response = ""
            cnt2 = 0
            trx_found = False
            while not trx_found and cnt2 < 60:
                response = requests.get("https://steemmonsters.com/transactions/lookup?trx_id=%s" % deck["trx_id"])
                if str(response) != '<Response [200]>':
                    sleep(1)
                else:
                    if 'error' in response.json() and "not found" in response.json()["error"]:
                        try:
                            sleep(1)
                        except KeyboardInterrupt:
                            print("Exiting cleanly...")
                            return
                    elif 'error' in response.json():
                        trx_found = True
                    elif "trx_info" in response.json() and response.json()["trx_info"]["success"]:
                        trx_found = True
                    else:
                        sleep(1)
                    # elif 'error' in response.json():
                    #    print(response.json()["error"])
                cnt2 += 1
            if 'error' in response.json():
                print(response.json()["error"])
                if "The current player is already looking for a match." in response.json()["error"]:
                    self.stm.custom_json('sm_cancel_match', "{}", required_posting_auths=[acc["name"]])
                    try:
                        sleep(3)
                    except KeyboardInterrupt:
                        print("Exiting cleanly...")
                        return
                break
            else:
                print("Transaction is valid...")
            #     print(response.json())

            match_cnt = 0
            match_found = False
            while not match_found and match_cnt < 60:
                match_cnt += 1
                response = self.api.get_battle_status(deck["trx_id"])
                if "status" in response and response["status"] > 0 and response["status"] < 3:
                    match_found = True
                sleep(1)
                # print("open %s" % str(open_match))
                # print("Waiting %s" % str(reveal_match))
            # print("Opponents found: %s" % str(reveal_match))
            if not match_found:
                print("Timeout and no opponent found...")
                continue
            print("Opponent found...")

            json_data = deck
            self.stm.custom_json('sm_team_reveal', json_data, required_posting_auths=[acc["name"]])
            print("sm_team_reveal broadcasted and waiting for results.")
            response = ""
            try:
                sleep(2)
            except KeyboardInterrupt:
                print("Exiting cleanly...")
                return
            cnt2 = 0

            found_match = False
            while not found_match and cnt2 < 40:
                response = requests.get("https://steemmonsters.com/battle/result?id=%s" % deck["trx_id"])
                if str(response) != '<Response [200]>':
                    try:
                        sleep(2)
                    except KeyboardInterrupt:
                        print("Exiting cleanly...")
                        return
                elif 'Error' in response.json():
                    try:
                        sleep(2)
                    except KeyboardInterrupt:
                        print("Exiting cleanly...")
                        return
                else:
                    found_match = True
                cnt2 += 1
            if cnt2 == 40:
                print("Could not found opponent!")
                response = self.api.get_battle_status(deck["trx_id"])
                if "reveal_tx" in response and response["reveal_tx"] is None:
                    print("Error broadcasting sm_team_reveal. Check your teams for validity (Summoners must be included).")
                    return
                self.stm.custom_json('sm_cancel_match', "{}", required_posting_auths=[acc["name"]])
                sleep(3)
                continue
            winner = response.json()["winner"]
            team1_player = response.json()["player_1"]
            team2_player = response.json()["player_2"]

            battle_details = json.loads(response.json()["details"])
            team1 = [{"id": battle_details["team1"]["summoner"]["card_detail_id"], "level": battle_details["team1"]["summoner"]["level"]}]
            for m in battle_details["team1"]["monsters"]:
                team1.append({"id": m["card_detail_id"], "level": m["level"]})
            team1_player = battle_details["team1"]["player"]
            team1_str = ""
            for m in team1:
                team1_str += self.cards[m["id"]]["name"] + ':%d, ' % m["level"]
            team1_str = team1_str[:-2]

            team2 = [{"id": battle_details["team2"]["summoner"]["card_detail_id"], "level": battle_details["team2"]["summoner"]["level"]}]
            for m in battle_details["team2"]["monsters"]:
                team2.append({"id": m["card_detail_id"], "level": m["level"]})
            team2_player = battle_details["team2"]["player"]
            team2_str = ""
            for m in team2:
                team2_str += self.cards[m["id"]]["name"] + ':%d, ' % m["level"]
            team2_str = team2_str[:-2]

            if team1_player == winner:
                print("match " + colored(team1_player, "green") + " - " + colored(team2_player, "red"))
            else:
                print("match " + colored(team2_player, "green") + " - " + colored(team1_player, "red"))

            if team1_player == acc["name"]:
                print("Opponent ranking: %d" % response.json()["player_2_rating_initial"])
                print("Opponents team: %s" % team2_str)
            else:
                print("Opponent ranking: %d" % response.json()["player_1_rating_initial"])
                print("Opponents team: %s" % team1_str)

            if winner == acc["name"]:
                if statistics["last_match_won"]:
                    statistics["winning_streak"] += 1
                statistics["won"] += 1
                win_left -= 1
                statistics["loosing_streak"] = 0
                statistics["last_match_won"] = True
                statistics["last_match_lose"] = False
            else:
                if statistics["last_match_lose"]:
                    statistics["loosing_streak"] += 1
                statistics["winning_streak"] = 0
                statistics["last_match_won"] = False
                statistics["last_match_lose"] = True

            statistics["battles"] += 1
            if len(inp.split(",")) > 0:
                print("%d of %d matches won using %s deck (%s)" % (statistics["won"], statistics["battles"], inp.split(",")[current_deck_index], inp))
            else:
                print("%d of %d matches won using %s deck" % (statistics["won"], statistics["battles"], inp))
            if acc["name"] == response.json()["player_1"]:
                print("Score %d -> %d" % (response.json()["player_1_rating_initial"], response.json()["player_1_rating_final"]))
            else:
                print("Score %d -> %d" % (response.json()["player_2_rating_initial"], response.json()["player_2_rating_final"]))
            print("--------------")

    def help_play(self):
        print("Starts playing with given deck")

    def do_stream(self, inp):
        block_num = self.b.get_current_block_num()
        match_cnt = 0
        open_match = {}
        reveal_match = {}

        while True:
            try:
                match_cnt += 1

                response = self.api.get_from_block(block_num)
                for r in response:
                    block_num = r["block_num"]
                    if r["type"] == "sm_find_match":
                        player = r["player"]
                        player_info = self.api.get_player_details(player)
                        if not r["success"]:
                            continue

                        data = json.loads(r["data"])
                        if data["match_type"] != "Ranked":
                            continue
                        if player not in open_match:
                            open_match[player] = {"type": r["type"], "block_num": block_num, "player": player, "mana_cap": data["mana_cap"], "summoner_level": data["summoner_level"]}
                            log("%s (%d) with summoner_level %d starts searching (%d player searching)" % (player, player_info["rating"], data["summoner_level"], len(open_match)), color="yellow")
                    elif r["type"] == "sm_team_reveal":
                        result = json.loads(r["result"])
                        player = r["player"]

                        if player in open_match:
                            player_data = open_match.pop(player)
                            waiting_time = (block_num - player_data["block_num"]) * 3
                        else:
                            waiting_time = 0
                            if "battle" in result:
                                mana_cap = result["battle"]["mana_cap"]
                            else:
                                mana_cap = 0
                            player_data = {"type": r["type"], "block_num": block_num, "player": player, "mana_cap": mana_cap, "summoner_level": 0}
                        if player not in reveal_match:
                            if "status" in result and "Waiting for opponent reveal." in result["status"]:
                                reveal_match[player] = player_data
                                log("%s waits for opponent reveal after %d s (%d player waiting)" % (player, waiting_time, len(reveal_match)), color="white")
                        else:
                            if "status" in result and "Waiting for opponent reveal." not in result["status"]:
                                reveal_match.pop(player)

                        if "battle" in result:
                            team1 = [{"id": result["battle"]["details"]["team1"]["summoner"]["card_detail_id"], "level": result["battle"]["details"]["team1"]["summoner"]["level"]}]
                            for m in result["battle"]["details"]["team1"]["monsters"]:
                                team1.append({"id": m["card_detail_id"], "level": m["level"]})
                            team1_player = result["battle"]["details"]["team1"]["player"]
                            team1_summoner = result["battle"]["details"]["team1"]["summoner"]
                            summoner1 = self.cards[team1_summoner["card_detail_id"]]["name"] + ':%d' % team1_summoner["level"]

                            team2 = [{"id": result["battle"]["details"]["team2"]["summoner"]["card_detail_id"], "level": result["battle"]["details"]["team2"]["summoner"]["level"]}]
                            for m in result["battle"]["details"]["team2"]["monsters"]:
                                team2.append({"id": m["card_detail_id"], "level": m["level"]})
                            team2_player = result["battle"]["details"]["team2"]["player"]
                            team2_summoner = result["battle"]["details"]["team2"]["summoner"]
                            summoner2 = self.cards[team2_summoner["card_detail_id"]]["name"] + ':%d' % team2_summoner["level"]
                            winner = result["battle"]["details"]["winner"]
                            if team1_player == winner:
                                print("match " + colored("%s (%s)" % (team1_player, summoner1), "green") + " - " + colored("%s (%s)" % (team2_player, summoner2), "red"))
                            else:
                                print("match " + colored("%s (%s)" % (team2_player, summoner2), "green") + " - " + colored("%s (%s)" % (team1_player, summoner1), "red"))
                            if team2_player in open_match:
                                open_match.pop(team2_player)
                            if team1_player in open_match:
                                open_match.pop(team1_player)
                            if team2_player in reveal_match:
                                reveal_match.pop(team2_player)
                            if team1_player in reveal_match:
                                reveal_match.pop(team1_player)
            except KeyboardInterrupt:
                print("Exiting cleanly...")
                return

    def help_stream(self):
        print("Shows who is currently playing.")

    def default(self, inp):
        if inp == 'x' or inp == 'q':
            return self.do_exit(inp)

        print("Default: {}".format(inp))

    do_EOF = do_exit
    help_EOF = help_exit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config")
    args = parser.parse_args()
    smprompt = SMPrompt()
    if args.config:
        smprompt.do_reload_config(args.config)
    smprompt.cmdloop()


if __name__ == '__main__':
    main()
