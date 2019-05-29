# This Python file uses the following encoding: utf-8
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import bytes, int, str
import os
import ast
import json
import sys
from prettytable import PrettyTable
from datetime import datetime, timedelta
import pytz
import time
import math
import random
import logging
import click
import yaml
import re
from morphenepython.instance import set_shared_morphene_instance, shared_morphene_instance
from morphenepython.amount import Amount
from morphenepython.account import Account
from morphenepython.morphene import MorpheneClient
from morphenepython.block import Block
from morphenepython.profile import Profile
from morphenepython.wallet import Wallet
from morphenepython.asset import Asset
from morphenepython.witness import Witness, WitnessesRankedByVote, WitnessesVotedByAccount
from morphenepython.blockchain import Blockchain
from morphenepython.utils import formatTimeString, seperate_yaml_dict_from_body
from morphenepython import exceptions
from morphenepython.version import version as __version__
from morphenepython.asciichart import AsciiChart
from morphenepython.transactionbuilder import TransactionBuilder
from timeit import default_timer as timer
from morphenepythonbase import operations
from morphenepythongraphenebase.account import PrivateKey, PublicKey, BrainKey
from morphenepythongraphenebase.base58 import Base58
from morphenepython.nodelist import NodeList
from morphenepython.imageuploader import ImageUploader
from morphenepython.rc import RC


click.disable_unicode_literals_warning = True
log = logging.getLogger(__name__)
try:
    import keyring
    if not isinstance(keyring.get_keyring(), keyring.backends.fail.Keyring):
        KEYRING_AVAILABLE = True
    else:
        KEYRING_AVAILABLE = False
except ImportError:
    KEYRING_AVAILABLE = False

FUTURES_MODULE = None
if not FUTURES_MODULE:
    try:
        from concurrent.futures import ThreadPoolExecutor, wait, as_completed
        FUTURES_MODULE = "futures"
    except ImportError:
        FUTURES_MODULE = None


availableConfigurationKeys = [
    "default_account",
    "nodes",
    "password_storage",
    "client_id",
]


def prompt_callback(ctx, param, value):
    if value in ["yes", "y", "ye"]:
        value = True
    else:
        print("Please write yes, ye or y to confirm!")
        ctx.abort()


def asset_callback(ctx, param, value):
    if value not in ["MORPH"]:
        print("Please MORPH as asset!")
        ctx.abort()
    else:
        return value


def prompt_flag_callback(ctx, param, value):
    if not value:
        ctx.abort()


def unlock_wallet(stm, password=None):
    if mph.unsigned and mph.nobroadcast:
        return True
    password_storage = mph.config["password_storage"]
    if not password and KEYRING_AVAILABLE and password_storage == "keyring":
        password = keyring.get_password("morphenepython", "wallet")
    if not password and password_storage == "environment" and "UNLOCK" in os.environ:
        password = os.environ.get("UNLOCK")
    if bool(password):
        mph.wallet.unlock(password)
    else:
        password = click.prompt("Password to unlock wallet or posting/active wif", confirmation_prompt=False, hide_input=True)
        try:
            mph.wallet.unlock(password)
        except:
            try:
                mph.wallet.setKeys([password])
                print("Wif accepted!")
                return True                
            except:
                raise exceptions.WrongMasterPasswordException("entered password is not a valid password/wif")

    if mph.wallet.locked():
        if password_storage == "keyring" or password_storage == "environment":
            print("Wallet could not be unlocked with %s!" % password_storage)
            password = click.prompt("Password to unlock wallet", confirmation_prompt=False, hide_input=True)
            if bool(password):
                unlock_wallet(stm, password=password)
                if not mph.wallet.locked():
                    return True
        else:
            print("Wallet could not be unlocked!")
        return False
    else:
        print("Wallet Unlocked!")
        return True


def node_answer_time(node):
    try:
        stm_local = MorpheneClient(node=node, num_retries=2, num_retries_call=2, timeout=10)
        start = timer()
        stm_local.get_config(use_stored_data=False)
        stop = timer()
        rpc_answer_time = stop - start
    except KeyboardInterrupt:
        rpc_answer_time = float("inf")
        raise KeyboardInterrupt()
    except:
        rpc_answer_time = float("inf")
    return rpc_answer_time


@click.group(chain=True)
@click.option(
    '--node', '-n', default="", help="URL for public Morphene Blockchain API (e.g. https://morphene.io/rpc)")
@click.option(
    '--offline', '-o', is_flag=True, default=False, help="Prevent connecting to network")
@click.option(
    '--no-broadcast', '-d', is_flag=True, default=False, help="Do not broadcast")
@click.option(
    '--no-wallet', '-p', is_flag=True, default=False, help="Do not load the wallet")
@click.option(
    '--unsigned', '-x', is_flag=True, default=False, help="Nothing will be signed")
@click.option(
    '--expires', '-e', default=30,
    help='Delay in seconds until transactions are supposed to expire(defaults to 60)')
@click.option(
    '--verbose', '-v', default=3, help='Verbosity')
@click.version_option(version=__version__)
def cli(node, offline, no_broadcast, no_wallet, unsigned, expires, verbose):

    # Logging
    log = logging.getLogger(__name__)
    verbosity = ["critical", "error", "warn", "info", "debug"][int(
        min(verbose, 4))]
    log.setLevel(getattr(logging, verbosity.upper()))
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, verbosity.upper()))
    ch.setFormatter(formatter)
    log.addHandler(ch)
    debug = verbose > 0
    stm = MorpheneClient(
        node=node,
        nobroadcast=no_broadcast,
        offline=offline,
        nowallet=no_wallet,
        unsigned=unsigned,
        expiration=expires,
        debug=debug,
        num_retries=10,
        num_retries_call=3,
        timeout=15,
        autoconnect=False
    )
    set_shared_morphene_instance(stm)

    pass


@cli.command()
@click.argument('key')
@click.argument('value')
def set(key, value):
    """ Set default_account or nodes

        set [key] [value]
    """
    stm = shared_morphene_instance()
    if key == "default_account":
        if mph.rpc is not None:
            mph.rpc.rpcconnect()
        mph.set_default_account(value)
    elif key == "nodes" or key == "node":
        if bool(value) or value != "default":
            mph.set_default_nodes(value)
        else:
            mph.set_default_nodes("")
    elif key == "password_storage":
        mph.config["password_storage"] = value
        if KEYRING_AVAILABLE and value == "keyring":
            password = click.prompt("Password to unlock wallet (Will be stored in keyring)", confirmation_prompt=False, hide_input=True)
            password = keyring.set_password("morphenepython", "wallet", password)
        elif KEYRING_AVAILABLE and value != "keyring":
            try:
                keyring.delete_password("morphenepython", "wallet")
            except keyring.errors.PasswordDeleteError:
                print("")
        if value == "environment":
            print("The wallet password can be stored in the UNLOCK environment variable to skip password prompt!")
    elif key == "client_id":
        mph.config["client_id"] = value
    elif key == "hot_sign_redirect_uri":
        mph.config["hot_sign_redirect_uri"] = value
    elif key == "sc2_api_url":
        mph.config["sc2_api_url"] = value
    elif key == "oauth_base_url":
        mph.config["oauth_base_url"] = value
    else:
        print("wrong key")


@cli.command()
@click.option('--results', is_flag=True, default=False, help="Shows result of changing the node.")
def nextnode(results):
    """ Uses the next node in list
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    mph.move_current_node_to_front()
    node = mph.get_default_nodes()
    offline = mph.offline
    if len(node) < 2:
        print("At least two nodes are needed!")
        return
    node = node[1:] + [node[0]]
    if not offline:
        mph.rpc.next()
        mph.get_blockchain_version()
    while not offline and node[0] != mph.rpc.url and len(node) > 1:
        node = node[1:] + [node[0]]
    mph.set_default_nodes(node)
    if not results:
        return

    t = PrettyTable(["Key", "Value"])
    t.align = "l"
    if not offline:
        t.add_row(["Node-Url", mph.rpc.url])
    else:
        t.add_row(["Node-Url", node[0]])
    if not offline:
        t.add_row(["Version", mph.get_blockchain_version()])
    else:
        t.add_row(["Version", "morphenepy is in offline mode..."])
    print(t)


@cli.command()
@click.option(
    '--raw', is_flag=True, default=False,
    help="Returns only the raw value")
@click.option(
    '--sort', is_flag=True, default=False,
    help="Sort all nodes by ping value")
@click.option(
    '--remove', is_flag=True, default=False,
    help="Remove node with errors from list")
@click.option(
    '--threading', is_flag=True, default=False,
    help="Use a thread for each node")
def pingnode(raw, sort, remove, threading):
    """ Returns the answer time in milliseconds
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    nodes = mph.get_default_nodes()
    if not raw:
        t = PrettyTable(["Node", "Answer time [ms]"])
        t.align = "l"
    if sort:
        ping_times = []
        for node in nodes:
            ping_times.append(1000.)
        if threading and FUTURES_MODULE:
            pool = ThreadPoolExecutor(max_workers=len(nodes) + 1)
            futures = []
        for i in range(len(nodes)):
            try:
                if not threading or not FUTURES_MODULE:
                    ping_times[i] = node_answer_time(nodes[i])
                else:
                    futures.append(pool.submit(node_answer_time, nodes[i]))
                if not threading or not FUTURES_MODULE:
                    print("node %s results in %.2f" % (nodes[i], ping_times[i]))
            except KeyboardInterrupt:
                ping_times[i] = float("inf")
                break
        if threading and FUTURES_MODULE:
            ping_times = [r.result() for r in as_completed(futures)]
        sorted_arg = sorted(range(len(ping_times)), key=ping_times.__getitem__)
        sorted_nodes = []
        for i in sorted_arg:
            if not remove or ping_times[i] != float("inf"):
                sorted_nodes.append(nodes[i])
        mph.set_default_nodes(sorted_nodes)
        if not raw:
            for i in sorted_arg:
                t.add_row([nodes[i], "%.2f" % (ping_times[i] * 1000)])
            print(t)
        else:
            print(ping_times[sorted_arg])
    else:
        node = mph.rpc.url
        rpc_answer_time = node_answer_time(node)
        rpc_time_str = "%.2f" % (rpc_answer_time * 1000)
        if raw:
            print(rpc_time_str)
            return
        t.add_row([node, rpc_time_str])
        print(t)


@cli.command()
@click.option(
    '--version', is_flag=True, default=False,
    help="Returns only the raw version value")
@click.option(
    '--url', is_flag=True, default=False,
    help="Returns only the raw url value")
def currentnode(version, url):
    """ Sets the currently working node at the first place in the list
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    offline = mph.offline
    mph.move_current_node_to_front()
    node = mph.get_default_nodes()
    if version and not offline:
        print(mph.get_blockchain_version())
        return
    elif version and offline:
        print("Node is offline")
        return
    if url and not offline:
        print(mph.rpc.url)
        return
    t = PrettyTable(["Key", "Value"])
    t.align = "l"
    if not offline:
        t.add_row(["Node-Url", mph.rpc.url])
    else:
        t.add_row(["Node-Url", node[0]])
    if not offline:
        t.add_row(["Version", mph.get_blockchain_version()])
    else:
        t.add_row(["Version", "morphenepy is in offline mode..."])
    print(t)


@cli.command()
@click.option(
    '--show', '-s', is_flag=True, default=False,
    help="Prints the updated nodes")
@click.option(
    '--test', '-t', is_flag=True, default=False,
    help="Do change the node list, only print the newest nodes setup.")
@click.option(
    '--only-https', '-h', is_flag=True, default=False,
    help="Use only https nodes.")
@click.option(
    '--only-wss', '-w', is_flag=True, default=False,
    help="Use only websocket nodes.")
def updatenodes(show, test, only_https, only_wss):
    """ Update the nodelist from @fullnodeupdate
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    t = PrettyTable(["node", "Version", "score"])
    t.align = "l"
    nodelist = NodeList()
    nodelist.update_nodes(morphene_instance=stm)
    nodes = nodelist.get_nodes(normal=not, wss=not only_https, https=not only_wss)
    if show or test:
        sorted_nodes = sorted(nodelist, key=lambda node: node["score"], reverse=True)
        for node in sorted_nodes:
            if node["url"] in nodes:
                score = float("{0:.1f}".format(node["score"]))
                t.add_row([node["url"], node["version"], score])
        print(t)
    if not test:
        mph.set_default_nodes(nodes)


@cli.command()
def config():
    """ Shows local configuration
    """
    stm = shared_morphene_instance()
    t = PrettyTable(["Key", "Value"])
    t.align = "l"
    for key in mph.config:
        # hide internal config data
        if key in availableConfigurationKeys and key != "nodes" and key != "node":
            t.add_row([key, mph.config[key]])
    node = mph.get_default_nodes()
    nodes = json.dumps(node, indent=4)
    t.add_row(["nodes", nodes])
    if "password_storage" not in availableConfigurationKeys:
        t.add_row(["password_storage", mph.config["password_storage"]])
    t.add_row(["data_dir", mph.config.data_dir])
    print(t)


@cli.command()
@click.option('--wipe', is_flag=True, default=False,
              help="Wipe old wallet without prompt.")
def createwallet(wipe):
    """ Create new wallet with a new password
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if mph.wallet.created() and not wipe:
        wipe_answer = click.prompt("'Do you want to wipe your wallet? Are your sure? This is IRREVERSIBLE! If you dont have a backup you may lose access to your account! [y/n]",
                                   default="n")
        if wipe_answer in ["y", "ye", "yes"]:
            mph.wallet.wipe(True)
        else:
            return
    elif wipe:
        mph.wallet.wipe(True)
    password = None
    password = click.prompt("New wallet password", confirmation_prompt=True, hide_input=True)
    if not bool(password):
        print("Password cannot be empty! Quitting...")
        return
    password_storage = mph.config["password_storage"]
    if KEYRING_AVAILABLE and password_storage == "keyring":
        password = keyring.set_password("morphenepython", "wallet", password)
    elif password_storage == "environment":
        print("The new wallet password can be stored in the UNLOCK environment variable to skip password prompt!")
    mph.wallet.create(password)
    set_shared_morphene_instance(stm)


@cli.command()
@click.option('--test-unlock', is_flag=True, default=False, help='test if unlock is sucessful')
def walletinfo(test_unlock):
    """ Show info about wallet
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()    
    t = PrettyTable(["Key", "Value"])
    t.align = "l"
    t.add_row(["created", mph.wallet.created()])
    t.add_row(["locked", mph.wallet.locked()])
    t.add_row(["Number of stored keys", len(mph.wallet.getPublicKeys())])
    t.add_row(["sql-file", mph.wallet.keyStorage.sqlDataBaseFile])
    password_storage = mph.config["password_storage"]
    t.add_row(["password_storage", password_storage])
    password = os.environ.get("UNLOCK")
    if password is not None:
        t.add_row(["UNLOCK env set", "yes"])
    else:
        t.add_row(["UNLOCK env set", "no"])
    if KEYRING_AVAILABLE:
        t.add_row(["keyring installed", "yes"])
    else:
        t.add_row(["keyring installed", "no"])
    if test_unlock:
        if unlock_wallet(stm):
            t.add_row(["Wallet unlock", "successful"])
        else:
            t.add_row(["Wallet unlock", "not working"])
    # t.add_row(["getPublicKeys", str(mph.wallet.getPublicKeys())])
    print(t)


@cli.command()
@click.option('--unsafe-import-key',
              help='WIF key to parse (unsafe, unless shell history is deleted afterwards)', multiple=True)
def parsewif(unsafe_import_key):
    """ Parse a WIF private key without importing
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if unsafe_import_key:
        for key in unsafe_import_key:
            try:
                pubkey = PrivateKey(key, prefix=mph.prefix).pubkey
                print(pubkey)
                account = mph.wallet.getAccountFromPublicKey(str(pubkey))
                account = Account(account, morphene_instance=stm)
                key_type = mph.wallet.getKeyType(account, str(pubkey))
                print("Account: %s - %s" % (account["name"], key_type))
            except Exception as e:
                print(str(e))
    else:
        while True:
            wifkey = click.prompt("Enter private key", confirmation_prompt=False, hide_input=True)
            if not wifkey or wifkey == "quit" or wifkey == "exit":
                break
            try:
                pubkey = PrivateKey(wifkey, prefix=mph.prefix).pubkey
                print(pubkey)
                account = mph.wallet.getAccountFromPublicKey(str(pubkey))
                account = Account(account, morphene_instance=stm)
                key_type = mph.wallet.getKeyType(account, str(pubkey))
                print("Account: %s - %s" % (account["name"], key_type))
            except Exception as e:
                print(str(e))
                continue


@cli.command()
@click.option('--unsafe-import-key',
              help='Private key to import to wallet (unsafe, unless shell history is deleted afterwards)')
def addkey(unsafe_import_key):
    """ Add key to wallet

        When no [OPTION] is given, a password prompt for unlocking the wallet
        and a prompt for entering the private key are shown.
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not unlock_wallet(stm):
        return
    if not unsafe_import_key:
        unsafe_import_key = click.prompt("Enter private key", confirmation_prompt=False, hide_input=True)
    mph.wallet.addPrivateKey(unsafe_import_key)
    set_shared_morphene_instance(stm)


@cli.command()
@click.option('--confirm',
              prompt='Are your sure? This is IRREVERSIBLE! If you dont have a backup you may lose access to your account!',
              hide_input=False, callback=prompt_flag_callback, is_flag=True,
              confirmation_prompt=False, help='Please confirm!')
@click.argument('pub')
def delkey(confirm, pub):
    """ Delete key from the wallet

        PUB is the public key from the private key
        which will be deleted from the wallet
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not unlock_wallet(stm):
        return
    mph.wallet.removePrivateKeyFromPublicKey(pub)
    set_shared_morphene_instance(stm)


@cli.command()
@click.option('--import-brain-key', help='Imports a brain key and derives a private and public key', is_flag=True, default=False)
@click.option('--sequence', help='Sequence number, influences the derived private key. (default is 0)', default=0)
def keygen(import_brain_key, sequence):
    """ Creates a new random brain key and prints its derived private key and public key.
        The generated key is not stored.
    """
    if import_brain_key:
        brain_key = click.prompt("Enter brain key", confirmation_prompt=False, hide_input=True)
    else:
        brain_key = None
    bk = BrainKey(brainkey=brain_key, sequence=sequence)
    t = PrettyTable(["Key", "Value"])
    t.align = "l"
    t.add_row(["Brain Key", bk.get_brainkey()])
    t.add_row(["Private Key", str(bk.get_private())])
    t.add_row(["Public Key", format(bk.get_public(), "MPH")])
    print(t)


@cli.command()
@click.argument('name')
@click.option('--unsafe-import-token',
              help='Private key to import to wallet (unsafe, unless shell history is deleted afterwards)')
def addtoken(name, unsafe_import_token):
    """ Add key to wallet

        When no [OPTION] is given, a password prompt for unlocking the wallet
        and a prompt for entering the private key are shown.
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not unlock_wallet(stm):
        return
    if not unsafe_import_token:
        unsafe_import_token = click.prompt("Enter private token", confirmation_prompt=False, hide_input=True)
    mph.wallet.addToken(name, unsafe_import_token)
    set_shared_morphene_instance(stm)


@cli.command()
@click.option('--confirm',
              prompt='Are your sure?',
              hide_input=False, callback=prompt_flag_callback, is_flag=True,
              confirmation_prompt=False, help='Please confirm!')
@click.argument('name')
def deltoken(confirm, name):
    """ Delete name from the wallet

        name is the public name from the private token
        which will be deleted from the wallet
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not unlock_wallet(stm):
        return
    mph.wallet.removeTokenFromPublicName(name)
    set_shared_morphene_instance(stm)


@cli.command()
def listkeys():
    """ Show stored keys
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    t = PrettyTable(["Available Key"])
    t.align = "l"
    for key in mph.wallet.getPublicKeys():
        t.add_row([key])
    print(t)


@cli.command()
def listaccounts():
    """Show stored accounts"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    t = PrettyTable(["Name", "Type", "Available Key"])
    t.align = "l"
    for account in mph.wallet.getAccounts():
        t.add_row([
            account["name"] or "n/a", account["type"] or "n/a",
            account["pubkey"]
        ])
    print(t)


@cli.command()
@click.argument('to', nargs=1)
@click.argument('amount', nargs=1)
@click.argument('asset', nargs=1, callback=asset_callback)
@click.argument('memo', nargs=1, required=False)
@click.option('--account', '-a', help='Transfer from this account')
def transfer(to, amount, asset, memo, account):
    """Transfer MORPH"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not account:
        account = mph.config["default_account"]
    if not bool(memo):
        memo = ''
    if not unlock_wallet(stm):
        return
    acc = Account(account, morphene_instance=stm)
    tx = acc.transfer(to, amount, asset, memo)
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
@click.argument('amount', nargs=1)
@click.option('--account', '-a', help='Powerup from this account')
@click.option('--to', help='Powerup this account', default=None)
def powerup(amount, account, to):
    """Power up (vest MORPH as MORPH POWER)"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not account:
        account = mph.config["default_account"]
    if not unlock_wallet(stm):
        return
    acc = Account(account, morphene_instance=stm)
    try:
        amount = float(amount)
    except:
        amount = str(amount)
    tx = acc.transfer_to_vesting(amount, to=to)
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
@click.argument('amount', nargs=1)
@click.option('--account', '-a', help='Powerup from this account')
def powerdown(amount, account):
    """Power down (start withdrawing VESTS)

        amount is in VESTS
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not account:
        account = mph.config["default_account"]
    if not unlock_wallet(stm):
        return
    acc = Account(account, morphene_instance=stm)
    try:
        amount = float(amount)
    except:
        amount = str(amount)
    tx = acc.withdraw_vesting(amount)
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
@click.argument('amount', nargs=1)
@click.argument('to_account', nargs=1)
@click.option('--account', '-a', help='Delegate from this account')
def delegate(amount, to_account, account):
    """Delegate (start delegating VESTS to another account)

        amount is in VESTS
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not account:
        account = mph.config["default_account"]
    if not unlock_wallet(stm):
        return
    acc = Account(account, morphene_instance=stm)
    try:
        amount = float(amount)
    except:
        amount = Amount(str(amount), morphene_instance=stm)
        if amount.symbol == mph.morph_symbol:
            amount = float(amount)

    tx = acc.delegate_vesting_shares(to_account, amount)
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
@click.argument('to', nargs=1)
@click.option('--percentage', default=100, help='The percent of the withdraw to go to the "to" account')
@click.option('--account', '-a', help='Powerup from this account')
@click.option('--auto_vest', help='Set to true if the from account should receive the VESTS as'
              'VESTS, or false if it should receive them as MORPH.', is_flag=True)
def powerdownroute(to, percentage, account, auto_vest):
    """Setup a powerdown route"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not account:
        account = mph.config["default_account"]
    if not unlock_wallet(stm):
        return
    acc = Account(account, morphene_instance=stm)
    tx = acc.set_withdraw_vesting_route(to, percentage, auto_vest=auto_vest)
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
def changewalletpassphrase():
    """ Change wallet password
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()    
    if not unlock_wallet(stm):
        return
    newpassword = None
    newpassword = click.prompt("New wallet password", confirmation_prompt=True, hide_input=True)
    if not bool(newpassword):
        print("Password cannot be empty! Quitting...")
        return
    password_storage = mph.config["password_storage"]
    if KEYRING_AVAILABLE and password_storage == "keyring":
        keyring.set_password("morphenepython", "wallet", newpassword)
    elif password_storage == "environment":
        print("The new wallet password can be stored in the UNLOCK invironment variable to skip password prompt!")
    mph.wallet.changePassphrase(newpassword)


@cli.command()
@click.argument('account', nargs=-1)
def power(account):
    """ Shows vote power and bandwidth
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if len(account) == 0:
        if "default_account" in mph.config:
            account = [mph.config["default_account"]]
    for name in account:
        a = Account(name, morphene_instance=stm)
        print("\n@%s" % a.name)
        a.print_info(use_table=True)


@cli.command()
@click.argument('account', nargs=-1)
def balance(account):
    """ Shows balance
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if len(account) == 0:
        if "default_account" in mph.config:
            account = [mph.config["default_account"]]
    for name in account:
        a = Account(name, morphene_instance=stm)
        print("\n@%s" % a.name)
        t = PrettyTable(["Account", "MORPH", "VESTS"])
        t.align = "r"
        t.add_row([
            'Available',
            str(a.balances['available'][0]),
            str(a.balances['available'][1]),
            str(a.balances['available'][2]),
        ])
        t.add_row([
            'Rewards',
            str(a.balances['rewards'][0]),
            str(a.balances['rewards'][1]),
            str(a.balances['rewards'][2]),
        ])
        t.add_row([
            'Savings',
            str(a.balances['savings'][0]),
            str(a.balances['savings'][1]),
            'N/A',
        ])
        t.add_row([
            'TOTAL',
            str(a.balances['total'][0]),
            str(a.balances['total'][1]),
            str(a.balances['total'][2]),
        ])
        print(t)


@cli.command()
@click.argument('account', nargs=-1, required=False)
def interest(account):
    """ Get information about interest payment
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not account:
        if "default_account" in mph.config:
            account = [mph.config["default_account"]]

    t = PrettyTable([
        "Account", "Last Interest Payment", "Next Payment"
    ])
    t.align = "r"
    for a in account:
        a = Account(a, morphene_instance=stm)
        i = a.interest()
        t.add_row([
            a["name"],
            i["last_payment"],
            "in %s" % (i["next_payment_duration"])
        ])
    print(t)


@cli.command()
@click.argument('account', nargs=-1, required=False)
def follower(account):
    """ Get information about followers
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not account:
        if "default_account" in mph.config:
            account = [mph.config["default_account"]]
    for a in account:
        a = Account(a, morphene_instance=stm)
        print("\nFollowers statistics for @%s (please wait...)" % a.name)
        followers = a.get_followers(False)
        followers.print_summarize_table(tag_type="Followers")


@cli.command()
@click.argument('account', nargs=-1, required=False)
def following(account):
    """ Get information about following
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not account:
        if "default_account" in mph.config:
            account = [mph.config["default_account"]]
    for a in account:
        a = Account(a, morphene_instance=stm)
        print("\nFollowing statistics for @%s (please wait...)" % a.name)
        following = a.get_following(False)
        following.print_summarize_table(tag_type="Following")


@cli.command()
@click.argument('account', nargs=-1, required=False)
def muter(account):
    """ Get information about muter
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not account:
        if "default_account" in mph.config:
            account = [mph.config["default_account"]]
    for a in account:
        a = Account(a, morphene_instance=stm)
        print("\nMuters statistics for @%s (please wait...)" % a.name)
        muters = a.get_muters(False)
        muters.print_summarize_table(tag_type="Muters")


@cli.command()
@click.argument('account', nargs=-1, required=False)
def muting(account):
    """ Get information about muting
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not account:
        if "default_account" in mph.config:
            account = [mph.config["default_account"]]
    for a in account:
        a = Account(a, morphene_instance=stm)
        print("\nMuting statistics for @%s (please wait...)" % a.name)
        muting = a.get_mutings(False)
        muting.print_summarize_table(tag_type="Muting")


@cli.command()
@click.argument('account', nargs=1, required=False)
def permissions(account):
    """ Show permissions of an account
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not account:
        if "default_account" in mph.config:
            account = mph.config["default_account"]
    account = Account(account, morphene_instance=stm)
    t = PrettyTable(["Permission", "Threshold", "Key/Account"], hrules=0)
    t.align = "r"
    for permission in ["owner", "active", "posting"]:
        auths = []
        for type_ in ["account_auths", "key_auths"]:
            for authority in account[permission][type_]:
                auths.append("%s (%d)" % (authority[0], authority[1]))
        t.add_row([
            permission,
            account[permission]["weight_threshold"],
            "\n".join(auths),
        ])
    print(t)


@cli.command()
@click.argument('foreign_account', nargs=1, required=False)
@click.option('--permission', default="posting", help='The permission to grant (defaults to "posting")')
@click.option('--account', '-a', help='The account to allow action for')
@click.option('--weight', help='The weight to use instead of the (full) threshold. '
              'If the weight is smaller than the threshold, '
              'additional signatures are required')
@click.option('--threshold', help='The permission\'s threshold that needs to be reached '
              'by signatures to be able to interact')
def allow(foreign_account, permission, account, weight, threshold):
    """Allow an account/key to interact with your account

        foreign_account: The account or key that will be allowed to interact with account.
            When not given, password will be asked, from which a public key is derived.
            This derived key will then interact with your account.
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not account:
        account = mph.config["default_account"]
    if not unlock_wallet(stm):
        return
    if permission not in ["posting", "active", "owner"]:
        print("Wrong permission, please use: posting, active or owner!")
        return
    acc = Account(account, morphene_instance=stm)
    if not foreign_account:
        from morphenepythongraphenebase.account import PasswordKey
        pwd = click.prompt("Password for Key Derivation", confirmation_prompt=True, hide_input=True)
        foreign_account = format(PasswordKey(account, pwd, permission).get_public(), mph.prefix)
    if threshold is not None:
        threshold = int(threshold)
    tx = acc.allow(foreign_account, weight=weight, permission=permission, threshold=threshold)
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
@click.argument('foreign_account', nargs=1, required=False)
@click.option('--permission', default="posting", help='The permission to grant (defaults to "posting")')
@click.option('--account', '-a', help='The account to disallow action for')
@click.option('--threshold', help='The permission\'s threshold that needs to be reached '
              'by signatures to be able to interact')
def disallow(foreign_account, permission, account, threshold):
    """Remove allowance an account/key to interact with your account"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not account:
        account = mph.config["default_account"]
    if not unlock_wallet(stm):
        return
    if permission not in ["posting", "active", "owner"]:
        print("Wrong permission, please use: posting, active or owner!")
        return
    if threshold is not None:
        threshold = int(threshold)
    acc = Account(account, morphene_instance=stm)
    if not foreign_account:
        from morphenepythongraphenebase.account import PasswordKey
        pwd = click.prompt("Password for Key Derivation", confirmation_prompt=True)
        foreign_account = [format(PasswordKey(account, pwd, permission).get_public(), mph.prefix)]
    tx = acc.disallow(foreign_account, permission=permission, threshold=threshold)
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
@click.argument('creator', nargs=1, required=True)
@click.option('--fee', help='When fee is 0 (default) a subsidized account is claimed and can be created later with create_claimed_account', default=0.0)
@click.option('--number', '-n', help='Number of subsidized accounts to be claimed (default = 1), when fee = 0 MORPH', default=1)
def claimaccount(creator, fee, number):
    """Claim account for claimed account creation."""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not creator:
        creator = mph.config["default_account"]
    if not unlock_wallet(stm):
        return
    creator = Account(creator, morphene_instance=stm)
    fee = Amount("%.3f %s" % (float(fee), mph.morph_symbol), morphene_instance=stm)
    tx = None
    if float(fee) == 0:
        rc = RC(morphene_instance=stm)
        current_costs = rc.claim_account(tx_size=200)
        current_mana = creator.get_rc_manabar()["current_mana"]
        last_mana = current_mana
        cnt = 0
        print("Current costs %.2f G RC - current mana %.2f G RC" % (current_costs / 1e9, current_mana / 1e9))
        print("Account can claim %d accounts" % (int(current_mana / current_costs)))
        while current_costs + 10 < current_mana and cnt < number:
            if cnt > 0:
                print("Current costs %.2f G RC - current mana %.2f G RC" % (current_costs / 1e9, current_mana / 1e9))
                tx = json.dumps(tx, indent=4)
                print(tx)
            cnt += 1
            tx = mph.claim_account(creator, fee=fee)
            time.sleep(10)
            creator.refresh()
            current_mana = creator.get_rc_manabar()["current_mana"]
            print("Account claimed and %.2f G RC paid." % ((last_mana - current_mana) / 1e9))
            last_mana = current_mana
        if cnt == 0:
            print("Not enough RC for a claim!")
    else:
        tx = mph.claim_account(creator, fee=fee)
    if tx is not None:
        tx = json.dumps(tx, indent=4)
        print(tx)


@cli.command()
@click.argument('accountname', nargs=1, required=True)
@click.option('--account', '-a', help='Account that pays the fee')
@click.option('--owner', help='Main owner key - when not given, a passphrase is used to create keys.')
@click.option('--active', help='Active key - when not given, a passphrase is used to create keys.')
@click.option('--memo', help='Memo key - when not given, a passphrase is used to create keys.')
@click.option('--posting', help='posting key - when not given, a passphrase is used to create keys.')
@click.option('--create-claimed-account', '-c', help='Instead of paying the account creation fee a subsidized account is created.', is_flag=True, default=False)
def newaccount(accountname, account, owner, active, memo, posting, create_claimed_account):
    """Create a new account"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not account:
        account = mph.config["default_account"]
    if not unlock_wallet(stm):
        return
    acc = Account(account, morphene_instance=stm)
    if owner is None or active is None or memo is None or posting is None:
        password = click.prompt("Keys were not given - Passphrase is used to create keys\n New Account Passphrase", confirmation_prompt=True, hide_input=True)
        if not password:
            print("You cannot chose an empty password")
            return
        if create_claimed_account:
            tx = mph.create_claimed_account(accountname, creator=acc, password=password)
        else:
            tx = mph.create_account(accountname, creator=acc, password=password)
    else:
        if create_claimed_account:
            tx = mph.create_claimed_account(accountname, creator=acc, owner_key=owner, active_key=active, memo_key=memo, posting_key=posting)
        else:
            tx = mph.create_account(accountname, creator=acc, owner_key=owner, active_key=active, memo_key=memo, posting_key=posting)        
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
@click.argument('variable', nargs=1, required=False)
@click.argument('value', nargs=1, required=False)
@click.option('--account', '-a', help='setprofile as this user')
@click.option('--pair', '-p', help='"Key=Value" pairs', multiple=True)
def setprofile(variable, value, account, pair):
    """Set a variable in an account\'s profile"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    keys = []
    values = []
    if pair:
        for p in pair:
            key, value = p.split("=")
            keys.append(key)
            values.append(value)
    if variable and value:
        keys.append(variable)
        values.append(value)

    profile = Profile(keys, values)

    if not account:
        account = mph.config["default_account"]
    if not unlock_wallet(stm):
        return
    acc = Account(account, morphene_instance=stm)

    json_metadata = Profile(acc["json_metadata"] if acc["json_metadata"] else {})
    json_metadata.update(profile)
    tx = acc.update_account_profile(json_metadata)
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
@click.argument('variable', nargs=-1, required=True)
@click.option('--account', '-a', help='delprofile as this user')
def delprofile(variable, account):
    """Delete a variable in an account\'s profile"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()

    if not account:
        account = mph.config["default_account"]
    if not unlock_wallet(stm):
        return
    acc = Account(account, morphene_instance=stm)
    json_metadata = Profile(acc["json_metadata"])

    for var in variable:
        json_metadata.remove(var)

    tx = acc.update_account_profile(json_metadata)
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
@click.argument('account', nargs=1, required=True)
@click.option('--roles', help='Import specified keys (owner, active, posting, memo).', default=["active", "posting", "memo"])
def importaccount(account, roles):
    """Import an account using a passphrase"""
    from morphenepythongraphenebase.account import PasswordKey
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not unlock_wallet(stm):
        return
    account = Account(account, morphene_instance=stm)
    imported = False
    password = click.prompt("Account Passphrase", confirmation_prompt=False, hide_input=True)
    if not password:
        print("You cannot chose an empty Passphrase")
        return
    if "owner" in roles:
        owner_key = PasswordKey(account["name"], password, role="owner")
        owner_pubkey = format(owner_key.get_public_key(), mph.prefix)
        if owner_pubkey in [x[0] for x in account["owner"]["key_auths"]]:
            print("Importing owner key!")
            owner_privkey = owner_key.get_private_key()
            mph.wallet.addPrivateKey(owner_privkey)
            imported = True

    if "active" in roles:
        active_key = PasswordKey(account["name"], password, role="active")
        active_pubkey = format(active_key.get_public_key(), mph.prefix)
        if active_pubkey in [x[0] for x in account["active"]["key_auths"]]:
            print("Importing active key!")
            active_privkey = active_key.get_private_key()
            mph.wallet.addPrivateKey(active_privkey)
            imported = True

    if "posting" in roles:
        posting_key = PasswordKey(account["name"], password, role="posting")
        posting_pubkey = format(posting_key.get_public_key(), mph.prefix)
        if posting_pubkey in [
            x[0] for x in account["posting"]["key_auths"]
        ]:
            print("Importing posting key!")
            posting_privkey = posting_key.get_private_key()
            mph.wallet.addPrivateKey(posting_privkey)
            imported = True

    if "memo" in roles:
        memo_key = PasswordKey(account["name"], password, role="memo")
        memo_pubkey = format(memo_key.get_public_key(), mph.prefix)
        if memo_pubkey == account["memo_key"]:
            print("Importing memo key!")
            memo_privkey = memo_key.get_private_key()
            mph.wallet.addPrivateKey(memo_privkey)
            imported = True

    if not imported:
        print("No matching key(s) found. Password correct?")


@cli.command()
@click.option('--account', '-a', help='The account to updatememokey action for')
@click.option('--key', help='The new memo key')
def updatememokey(account, key):
    """Update an account\'s memo key"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not account:
        account = mph.config["default_account"]
    if not unlock_wallet(stm):
        return
    acc = Account(account, morphene_instance=stm)
    if not key:
        from morphenepythongraphenebase.account import PasswordKey
        pwd = click.prompt("Password for Memo Key Derivation", confirmation_prompt=True, hide_input=True)
        memo_key = PasswordKey(account, pwd, "memo")
        key = format(memo_key.get_public_key(), mph.prefix)
        memo_privkey = memo_key.get_private_key()
        if not mph.nobroadcast:
            mph.wallet.addPrivateKey(memo_privkey)
    tx = acc.update_memo_key(key)
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
@click.argument('witness', nargs=1)
@click.option('--account', '-a', help='Your account')
def approvewitness(witness, account):
    """Approve a witnesses"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not account:
        account = mph.config["default_account"]
    if not unlock_wallet(stm):
        return
    acc = Account(account, morphene_instance=stm)
    tx = acc.approvewitness(witness, approve=True)
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
@click.argument('witness', nargs=1)
@click.option('--account', '-a', help='Your account')
def disapprovewitness(witness, account):
    """Disapprove a witnesses"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not account:
        account = mph.config["default_account"]
    if not unlock_wallet(stm):
        return
    acc = Account(account, morphene_instance=stm)
    tx = acc.disapprovewitness(witness)
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
@click.option('--file', '-i', help='Load transaction from file. If "-", read from stdin (defaults to "-")')
@click.option('--outfile', '-o', help='Load transaction from file. If "-", read from stdin (defaults to "-")')
def sign(file, outfile):
    """Sign a provided transaction with available and required keys"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not unlock_wallet(stm):
        return
    if file and file != "-":
        if not os.path.isfile(file):
            raise Exception("File %s does not exist!" % file)
        with open(file) as fp:
            tx = fp.read()
        if tx.find('\0') > 0:
            with open(file, encoding='utf-16') as fp:
                tx = fp.read()
    else:
        tx = click.get_text_stream('stdin')
    tx = ast.literal_eval(tx)
    tx = mph.sign(tx, reconstruct_tx=False)
    tx = json.dumps(tx, indent=4)
    if outfile and outfile != "-":
        with open(outfile, 'w') as fp:
            fp.write(tx)
    else:
        print(tx)


@cli.command()
@click.option('--file', help='Load transaction from file. If "-", read from stdin (defaults to "-")')
def broadcast(file):
    """broadcast a signed transaction"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if file and file != "-":
        if not os.path.isfile(file):
            raise Exception("File %s does not exist!" % file)
        with open(file) as fp:
            tx = fp.read()
        if tx.find('\0') > 0:
            with open(file, encoding='utf-16') as fp:
                tx = fp.read()
    else:
        tx = click.get_text_stream('stdin')
    tx = ast.literal_eval(tx)
    tx = mph.broadcast(tx)
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
@click.option('--witness', help='Witness name')
@click.option('--maximum_block_size', help='Max block size')
@click.option('--account_creation_fee', help='Account creation fee')
@click.option('--url', help='Witness URL')
@click.option('--signing_key', help='Signing Key')
def witnessupdate(witness, maximum_block_size, account_creation_fee, url, signing_key):
    """Change witness properties"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not witness:
        witness = mph.config["default_account"]
    if not unlock_wallet(stm):
        return
    witness = Witness(witness, morphene_instance=stm)
    props = witness["props"]
    if account_creation_fee is not None:
        props["account_creation_fee"] = str(
            Amount("%.3f %s" % (float(account_creation_fee), mph.morph_symbol), morphene_instance=stm))
    if maximum_block_size is not None:
        props["maximum_block_size"] = int(maximum_block_size)
    tx = witness.update(signing_key or witness["signing_key"], url or witness["url"], props)
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
@click.argument('witness', nargs=1)
def witnessdisable(witness):
    """Disable a witness"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not witness:
        witness = mph.config["default_account"]
    if not unlock_wallet(stm):
        return
    witness = Witness(witness, morphene_instance=stm)
    if not witness.is_active:
        print("Cannot disable a disabled witness!")
        return
    props = witness["props"]
    tx = witness.update('MPH1111111111111111111111111111111114T1Anm', witness["url"], props)
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
@click.argument('witness', nargs=1)
@click.argument('signing_key', nargs=1)
def witnessenable(witness, signing_key):
    """Enable a witness"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not witness:
        witness = mph.config["default_account"]
    if not unlock_wallet(stm):
        return
    witness = Witness(witness, morphene_instance=stm)
    props = witness["props"]
    tx = witness.update(signing_key, witness["url"], props)
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
@click.argument('witness', nargs=1)
@click.argument('pub_signing_key', nargs=1)
@click.option('--maximum_block_size', help='Max block size', default=65536)
@click.option('--account_creation_fee', help='Account creation fee', default=0.1)
@click.option('--url', help='Witness URL', default="")
def witnesscreate(witness, pub_signing_key, maximum_block_size, account_creation_fee, url):
    """Create a witness"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not unlock_wallet(stm):
        return
    props = {
        "account_creation_fee":
            Amount("%.3f %s" % (float(account_creation_fee), mph.morph_symbol), morphene_instance=stm),
        "maximum_block_size":
            int(maximum_block_size)
    }

    tx = mph.witness_update(pub_signing_key, url, props, account=witness)
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
@click.argument('witness', nargs=1)
@click.argument('wif', nargs=1)
@click.option('--account_creation_fee', help='Account creation fee (float)')
@click.option('--account_subsidy_budget', help='Account subisidy per block')
@click.option('--account_subsidy_decay', help='Per block decay of the account subsidy pool')
@click.option('--maximum_block_size', help='Max block size')
@click.option('--new_signing_key', help='Set new signing key')
@click.option('--url', help='Witness URL')
def witnessproperties(witness, wif, account_creation_fee, account_subsidy_budget, account_subsidy_decay, maximum_block_size, new_signing_key, url):
    """Update witness properties of witness WITNESS with the witness signing key WIF"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    # if not unlock_wallet(stm):
    #    return
    props = {}
    if account_creation_fee is not None:
        props["account_creation_fee"] = Amount("%.3f %s" % (float(account_creation_fee), mph.morph_symbol), morphene_instance=stm)
    if account_subsidy_budget is not None:
        props["account_subsidy_budget"] = int(account_subsidy_budget)
    if account_subsidy_decay is not None:
        props["account_subsidy_decay"] = int(account_subsidy_decay)
    if maximum_block_size is not None:
        props["maximum_block_size"] = int(maximum_block_size)
    if new_signing_key is not None:
        props["new_signing_key"] = new_signing_key
    if url is not None:
        props["url"] = url

    tx = mph.witness_set_properties(wif, witness, props)
    tx = json.dumps(tx, indent=4)
    print(tx)


@cli.command()
@click.argument('witness', nargs=1)
def witness(witness):
    """ List witness information
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    witness = Witness(witness, morphene_instance=stm)
    witness_json = witness.json()
    witness_schedule = mph.get_witness_schedule()
    config = mph.get_config()
    if "VIRTUAL_SCHEDULE_LAP_LENGTH2" in config:
        lap_length = int(config["VIRTUAL_SCHEDULE_LAP_LENGTH2"])
    else:
        lap_length = int(config["MORPHENE_VIRTUAL_SCHEDULE_LAP_LENGTH2"])
    rank = 0
    active_rank = 0
    found = False
    witnesses = WitnessesRankedByVote(limit=250, morphene_instance=stm)
    vote_sum = witnesses.get_votes_sum()
    for w in witnesses:
        rank += 1
        if w.is_active:
            active_rank += 1
        if w["owner"] == witness["owner"]:
            found = True
            break
    virtual_time_to_block_num = int(witness_schedule["num_scheduled_witnesses"]) / (lap_length / (vote_sum + 1))
    t = PrettyTable(["Key", "Value"])
    t.align = "l"
    for key in sorted(witness_json):
        value = witness_json[key]
        if key in ["props"]:
            value = json.dumps(value, indent=4)
        t.add_row([key, value])
    if found:
        t.add_row(["rank", rank])
        t.add_row(["active_rank", active_rank])
    virtual_diff = int(witness_json["virtual_scheduled_time"]) - int(witness_schedule['current_virtual_time'])
    block_diff_est = virtual_diff * virtual_time_to_block_num
    if active_rank > 20:
        t.add_row(["virtual_time_diff", virtual_diff])
        t.add_row(["block_diff_est", int(block_diff_est)])
        next_block_s = int(block_diff_est) * 3
        next_block_min = next_block_s / 60
        next_block_h = next_block_min / 60
        next_block_d = next_block_h / 24
        time_diff_est = ""
        if next_block_d > 1:
            time_diff_est = "%.2f days" % next_block_d
        elif next_block_h > 1:
            time_diff_est = "%.2f hours" % next_block_h
        elif next_block_min > 1:
            time_diff_est = "%.2f minutes" % next_block_min
        else:
            time_diff_est = "%.2f seconds" % next_block_s
        t.add_row(["time_diff_est", time_diff_est])
    print(t)


@cli.command()
@click.argument('account', nargs=1, required=False)
@click.option('--limit', help='How many witnesses should be shown', default=100)
def witnesses(account, limit):
    """ List witnesses
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if account:
        account = Account(account, morphene_instance=stm)
        account_name = account["name"]
        if account["proxy"] != "":
            account_name = account["proxy"]
            account_type = "Proxy"
        else:
            account_type = "Account"
        witnesses = WitnessesVotedByAccount(account_name, morphene_instance=stm)
        print("%s: @%s (%d of 30)" % (account_type, account_name, len(witnesses)))
    else:
        witnesses = WitnessesRankedByVote(limit=limit, morphene_instance=stm)
    witnesses.printAsTable()


@cli.command()
@click.argument('blocknumber', nargs=1, required=False)
@click.option('--trx', '-t', help='Show only one transaction number', default=None)
@click.option('--use-api', '-u', help='Uses the get_potential_signatures api call', is_flag=True, default=False)
def verify(blocknumber, trx, use_api):
    """Returns the public signing keys for a block"""
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    b = Blockchain(morphene_instance=stm)
    i = 0
    if not blocknumber:
        blocknumber = b.get_current_block_num()
    try:
        int(blocknumber)
        block = Block(blocknumber, morphene_instance=stm)
        if trx is not None:
            i = int(trx)
            trxs = [block.json_transactions[int(trx)]]
        else:
            trxs = block.json_transactions
    except Exception:
        trxs = [b.get_transaction(blocknumber)]
        blocknumber = trxs[0]["block_num"]
    wallet = Wallet(morphene_instance=stm)
    t = PrettyTable(["trx", "Signer key", "Account"])
    t.align = "l"
    if not use_api:
        from morphenepythonbase.signedtransactions import Signed_Transaction
    for trx in trxs:
        if not use_api:
            # trx is now identical to the output of get_transaction
            # This is just for testing porpuse
            if True:
                signed_tx = Signed_Transaction(trx.copy())
            else:
                tx = b.get_transaction(trx["transaction_id"])
                signed_tx = Signed_Transaction(tx)
            public_keys = []
            for key in signed_tx.verify(chain=mph.chain_params, recover_parameter=True):
                public_keys.append(format(Base58(key, prefix=mph.prefix), mph.prefix))
        else:
            tx = TransactionBuilder(tx=trx, morphene_instance=stm)
            public_keys = tx.get_potential_signatures()
        accounts = []
        empty_public_keys = []
        for key in public_keys:
            account = wallet.getAccountFromPublicKey(key)
            if account is None:
                empty_public_keys.append(key)
            else:
                accounts.append(account)
        new_public_keys = []
        for key in public_keys:
            if key not in empty_public_keys or use_api:
                new_public_keys.append(key)
        if isinstance(new_public_keys, list) and len(new_public_keys) == 1:
            new_public_keys = new_public_keys[0]
        else:
            new_public_keys = json.dumps(new_public_keys, indent=4)
        if isinstance(accounts, list) and len(accounts) == 1:
            accounts = accounts[0]
        else:
            accounts = json.dumps(accounts, indent=4)
        t.add_row(["%d" % i, new_public_keys, accounts])
        i += 1
    print(t)


@cli.command()
@click.argument('objects', nargs=-1)
def info(objects):
    """ Show basic blockchain info

        General information about the blockchain, a block,
        an account, or a public key
    """
    stm = shared_morphene_instance()
    if mph.rpc is not None:
        mph.rpc.rpcconnect()
    if not objects:
        t = PrettyTable(["Key", "Value"])
        t.align = "l"
        info = mph.get_dynamic_global_properties()
        morph_per_mvest = mph.get_morph_per_mvest()
        chain_props = mph.get_chain_properties()
        for key in info:
            t.add_row([key, info[key]])
        t.add_row(["morph per mvest", morph_per_mvest])
        t.add_row(["account_creation_fee", chain_props["account_creation_fee"]])
        print(t.get_string(sortby="Key"))
        # Block
    for obj in objects:
        if re.match("^[0-9-]*$", obj) or re.match("^-[0-9]*$", obj) or re.match("^[0-9-]*:[0-9]", obj) or re.match("^[0-9-]*:-[0-9]", obj):
            tran_nr = ''
            if re.match("^[0-9-]*:[0-9-]", obj):
                obj, tran_nr = obj.split(":")
            if int(obj) < 1:
                b = Blockchain(morphene_instance=stm)
                block_number = b.get_current_block_num() + int(obj) - 1
            else:
                block_number = obj
            block = Block(block_number, morphene_instance=stm)
            if block:
                t = PrettyTable(["Key", "Value"])
                t.align = "l"
                block_json = block.json()
                for key in sorted(block_json):
                    value = block_json[key]
                    if key == "transactions" and not bool(tran_nr):
                        t.add_row(["Nr. of transactions", len(value)])
                    elif key == "transactions" and bool(tran_nr):
                        if int(tran_nr) < 0:
                            tran_nr = len(value) + int(tran_nr)
                        else:
                            tran_nr = int(tran_nr)
                        if len(value) > tran_nr - 1 and tran_nr > -1:
                            t_value = json.dumps(value[tran_nr], indent=4)
                            t.add_row(["transaction %d/%d" % (tran_nr, len(value)), t_value])
                    elif key == "transaction_ids" and not bool(tran_nr):
                        t.add_row(["Nr. of transaction_ids", len(value)])
                    elif key == "transaction_ids" and bool(tran_nr):
                        if int(tran_nr) < 0:
                            tran_nr = len(value) + int(tran_nr)
                        else:
                            tran_nr = int(tran_nr)
                        if len(value) > tran_nr - 1 and tran_nr > -1:
                            t.add_row(["transaction_id %d/%d" % (int(tran_nr), len(value)), value[tran_nr]])
                    else:
                        t.add_row([key, value])
                print(t)
            else:
                print("Block number %s unknown" % obj)
        elif re.match("^[a-zA-Z0-9\-\._]{2,16}$", obj):
            account = Account(obj, morphene_instance=stm)
            t = PrettyTable(["Key", "Value"])
            t.align = "l"
            account_json = account.json()
            for key in sorted(account_json):
                value = account_json[key]
                if key == "json_metadata":
                    value = json.dumps(json.loads(value or "{}"), indent=4)
                elif key in ["posting", "witness_votes", "active", "owner"]:
                    value = json.dumps(value, indent=4)
                elif isinstance(value, dict) and "asset" in value:
                    value = str(account[key])
                t.add_row([key, value])
            print(t)

            # witness available?
            try:
                witness = Witness(obj, morphene_instance=stm)
                witness_json = witness.json()
                t = PrettyTable(["Key", "Value"])
                t.align = "l"
                for key in sorted(witness_json):
                    value = witness_json[key]
                    if key in ["props"]:
                        value = json.dumps(value, indent=4)
                    t.add_row([key, value])
                print(t)
            except exceptions.WitnessDoesNotExistsException as e:
                print(str(e))
        # Public Key
        elif re.match("^" + mph.prefix + ".{48,55}$", obj):
            account = mph.wallet.getAccountFromPublicKey(obj)
            if account:
                account = Account(account, morphene_instance=stm)
                key_type = mph.wallet.getKeyType(account, obj)
                t = PrettyTable(["Account", "Key_type"])
                t.align = "l"
                t.add_row([account["name"], key_type])
                print(t)
            else:
                print("Public Key %s not known" % obj)
        else:
            print("Couldn't identify object to read")


if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        os.environ['SSL_CERT_FILE'] = os.path.join(sys._MEIPASS, 'lib', 'cert.pem')
        cli(sys.argv[1:])
    else:
        cli()
