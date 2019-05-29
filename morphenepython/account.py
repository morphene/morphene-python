# This Python file uses the following encoding: utf-8
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import bytes, int, str
import pytz
import json
from datetime import datetime, timedelta, date, time
import math
import random
import logging
from prettytable import PrettyTable
from morphenepython.instance import shared_morphene_instance
from .exceptions import AccountDoesNotExistsException, OfflineHasNoRPCException
from morphenepythonapi.exceptions import ApiNotSupported, MissingRequiredActiveAuthority
from .blockchainobject import BlockchainObject
from .blockchain import Blockchain
from .utils import formatTimeString, formatTimedelta, remove_from_dict, addTzInfo
from morphenepython.amount import Amount
from morphenepythonbase import operations
from morphenepython.rc import RC
from morphenepythongraphenebase.account import PrivateKey, PublicKey, PasswordKey
from morphenepythongraphenebase.py23 import bytes_types, integer_types, string_types, text_type
from morphenepython.constants import MORPHENE_1_PERCENT, MORPHENE_100_PERCENT, MORPHENE_VOTING_MANA_REGENERATION_SECONDS
log = logging.getLogger(__name__)


class Account(BlockchainObject):
    """ This class allows to easily access Account data

        :param str account_name: Name of the account
        :param MorpheneClient morphene_instance: MorpheneClient
               instance
        :param bool lazy: Use lazy loading
        :param bool full: Obtain all account data including orders, positions,
               etc.
        :returns: Account data
        :rtype: dictionary
        :raises morphenepython.exceptions.AccountDoesNotExistsException: if account
                does not exist

        Instances of this class are dictionaries that come with additional
        methods (see below) that allow dealing with an account and its
        corresponding functions.

        .. code-block:: python

            >>> from morphenepython.account import Account
            >>> from morphenepython import MorpheneClient
            >>> mph = MorpheneClient("https://morphene.io/rpc")
            >>> account = Account("initwitness", morphene_instance=mph)
            >>> print(account)
            <Account initwitness>
            >>> print(account.balances) # doctest: +SKIP

        .. note:: This class comes with its own caching function to reduce the
                  load on the API server. Instances of this class can be
                  refreshed with ``Account.refresh()``. The cache can be
                  cleared with ``Account.clear_cache()``

    """

    type_id = 2

    def __init__(
        self,
        account,
        full=True,
        lazy=False,
        morphene_instance=None
    ):
        """Initialize an account

        :param str account: Name of the account
        :param MorpheneClient morphene_instance: MorpheneClient
               instance
        :param bool lazy: Use lazy loading
        :param bool full: Obtain all account data including orders, positions,
               etc.
        """
        self.full = full
        self.lazy = lazy
        self.morphene = morphene_instance or shared_morphene_instance()
        if isinstance(account, dict):
            account = self._parse_json_data(account)
        super(Account, self).__init__(
            account,
            lazy=lazy,
            full=full,
            id_item="name",
            morphene_instance=morphene_instance
        )

    def refresh(self):
        """ Refresh/Obtain an account's data from the API server
        """
        if not self.morphene.is_connected():
            return
        if self.full:
            account = self.morphene.rpc.get_accounts(
                [self.identifier], api="database")
        else:
            account = self.morphene.rpc.lookup_account_names(
                [self.identifier], api="database")
        if account and isinstance(account, list) and len(account) == 1:
            account = account[0]
        if not account:
            raise AccountDoesNotExistsException(self.identifier)
        account = self._parse_json_data(account)
        self.identifier = account["name"]
        # self.morphene.refresh_data()

        super(Account, self).__init__(account, id_item="name", lazy=self.lazy, full=self.full, morphene_instance=self.morphene)

    def _parse_json_data(self, account):
        parse_int = [
            "withdrawn", "to_withdraw",
        ]
        for p in parse_int:
            if p in account and isinstance(account.get(p), string_types):
                account[p] = int(account.get(p, 0))
        if "proxied_vsf_votes" in account:
            proxied_vsf_votes = []
            for p_int in account["proxied_vsf_votes"]:
                if isinstance(p_int, string_types):
                    proxied_vsf_votes.append(int(p_int))
                else:
                    proxied_vsf_votes.append(p_int)
            account["proxied_vsf_votes"] = proxied_vsf_votes
        parse_times = [
            "last_owner_update", "last_account_update", "created", "last_owner_proved", "last_active_proved",
            "last_account_recovery", "next_vesting_withdrawal",
        ]
        for p in parse_times:
            if p in account and isinstance(account.get(p), string_types):
                account[p] = formatTimeString(account.get(p, "1970-01-01T00:00:00"))
        # Parse Amounts
        amounts = [
            "balance",
            "vesting_shares",
            "delegated_vesting_shares",
            "received_vesting_shares",
            "vesting_withdraw_rate",
            "vesting_balance",
        ]
        for p in amounts:
            if p in account and isinstance(account.get(p), (string_types, list, dict)):
                account[p] = Amount(account[p], morphene_instance=self.morphene)
        return account

    def json(self):
        output = self.copy()
        parse_int_without_zero = [
            "withdrawn", "to_withdraw",
        ]
        for p in parse_int_without_zero:
            if p in output and isinstance(output[p], integer_types) and output[p] != 0:
                output[p] = str(output[p])
        if "proxied_vsf_votes" in output:
            proxied_vsf_votes = []
            for p_int in output["proxied_vsf_votes"]:
                if isinstance(p_int, integer_types) and p_int != 0:
                    proxied_vsf_votes.append(str(p_int))
                else:
                    proxied_vsf_votes.append(p_int)
            output["proxied_vsf_votes"] = proxied_vsf_votes
        parse_times = [
            "last_owner_update", "last_account_update", "created", "last_owner_proved", "last_active_proved",
            "last_account_recovery", "next_vesting_withdrawal",
        ]
        for p in parse_times:
            if p in output:
                p_date = output.get(p, datetime(1970, 1, 1, 0, 0))
                if isinstance(p_date, (datetime, date, time)):
                    output[p] = formatTimeString(p_date)
                else:
                    output[p] = p_date
        amounts = [
            "balance",
            "vesting_shares",
            "delegated_vesting_shares",
            "received_vesting_shares",
            "vesting_withdraw_rate",
            "vesting_balance",
        ]
        for p in amounts:
            if p in output:
                if p in output:
                    output[p] = output.get(p).json()
        return json.loads(str(json.dumps(output)))

    def get_rc(self):
        """Return RC of account"""
        b = Blockchain(morphene_instance=self.morphene)
        return b.find_rc_accounts(self["name"])

    def get_rc_manabar(self):
        """Returns current_mana and max_mana for RC"""
        rc_param = self.get_rc()
        max_mana = int(rc_param["max_rc"])
        last_mana = int(rc_param["rc_manabar"]["current_mana"])
        last_update_time = rc_param["rc_manabar"]["last_update_time"]
        last_update = datetime.utcfromtimestamp(last_update_time)
        diff_in_seconds = (datetime.utcnow() - last_update).total_seconds()
        current_mana = int(last_mana + diff_in_seconds * max_mana / MORPHENE_VOTING_MANA_REGENERATION_SECONDS)
        if current_mana > max_mana:
            current_mana = max_mana
        if max_mana > 0:
            current_pct = current_mana / max_mana * 100
        else:
            current_pct = 0
        max_rc_creation_adjustment = Amount(rc_param["max_rc_creation_adjustment"], morphene_instance=self.morphene)
        return {"last_mana": last_mana, "last_update_time": last_update_time, "current_mana": current_mana,
                "max_mana": max_mana, "current_pct": current_pct, "max_rc_creation_adjustment": max_rc_creation_adjustment}

    def get_similar_account_names(self, limit=5):
        """ Returns ``limit`` account names similar to the current account
            name as a list

            :param int limit: limits the number of accounts, which will be
                returned
            :returns: Similar account names as list
            :rtype: list

            This is a wrapper around :func:`morphenepython.blockchain.Blockchain.get_similar_account_names()`
            using the current account name as reference.

        """
        b = Blockchain(morphene_instance=self.morphene)
        return b.get_similar_account_names(self.name, limit=limit)

    @property
    def name(self):
        """ Returns the account name
        """
        return self["name"]

    @property
    def profile(self):
        """ Returns the account profile
        """
        metadata = self.json_metadata
        if "profile" in metadata:
            return metadata["profile"]
        else:
            return {}

    @property
    def vests(self):
        """ Returns the accounts VESTS
        """
        return self.get_vests()

    @property
    def json_metadata(self):
        if self["json_metadata"] == '':
            return {}
        return json.loads(self["json_metadata"])

    def print_info(self, force_refresh=False, return_str=False, use_table=False, **kwargs):
        """ Prints import information about the account
        """
        if force_refresh:
            self.refresh()
            self.morphene.refresh_data(True)
        try:
            rc_mana = self.get_rc_manabar()
            rc = self.get_rc()
            rc_calc = RC(morphene_instance=self.morphene)
        except:
            rc_mana = None
            rc_calc = None

        if use_table:
            t = PrettyTable(["Key", "Value"])
            t.align = "l"
            t.add_row(["Name", self.name])
            t.add_row(["VESTS", "%.2f %s" % (self.get_vests(), self.morphene.morph_symbol)])
            t.add_row(["Balance", "%s, %s" % (str(self.balances["available"][0]), str(self.balances["available"][1]))])
            if rc_mana is not None:
                estimated_rc = int(rc["max_rc"]) * rc_mana["current_pct"] / 100
                t.add_row(["Remaining RC", "%.2f %%" % (rc_mana["current_pct"])])
                t.add_row(["Remaining RC", "(%.0f G RC of %.0f G RC)" % (estimated_rc / 10**9, int(rc["max_rc"]) / 10**9)])
                t.add_row(["Full in ", "%s" % (self.get_manabar_recharge_time_str(rc_mana))])
                t.add_row(["Est. RC for a transfer", "%.2f G RC" % (rc_calc.transfer() / 10**9)])

                t.add_row(["Transfer with current RC", "%d transfers" % (int(estimated_rc / rc_calc.transfer()))])

            if return_str:
                return t.get_string(**kwargs)
            else:
                print(t.get_string(**kwargs))
        else:
            ret = self.name + " (%.2f) \n" % (self.rep)
            ret += "--- Balance ---\n"
            ret += "%.2f VESTS" % (self.get_vests())
            ret += "%s\n" % (str(self.balances["available"][0]))
            if rc_mana is not None:
                estimated_rc = int(rc["max_rc"]) * rc_mana["current_pct"] / 100
                ret += "--- RC manabar ---\n"
                ret += "Remaining: %.2f %%" % (rc_mana["current_pct"])
                ret += " (%.0f G RC of %.0f G RC)\n" % (estimated_rc / 10**9, int(rc["max_rc"]) / 10**9)
                ret += "full in %s\n" % (self.get_manabar_recharge_time_str(rc_mana))
                ret += "--- Approx Costs ---\n"
                ret += "transfer - %.2f G RC - enough RC for %d transfers\n" % (rc_calc.transfer() / 10**9, int(estimated_rc / rc_calc.transfer()))
            if return_str:
                return ret
            print(ret)

    def get_manabar(self):
        """ Return manabar
        """
        max_mana = self.get_effective_vesting_shares()
        if max_mana == 0:
            props = self.morphene.get_chain_properties()
            required_fee_morph = Amount(props["account_creation_fee"], morphene_instance=self.morphene)
            max_mana = int(required_fee_morph)
        last_mana = int(self["voting_manabar"]["current_mana"])
        last_update_time = self["voting_manabar"]["last_update_time"]
        last_update = datetime.utcfromtimestamp(last_update_time)
        diff_in_seconds = (addTzInfo(datetime.utcnow()) - addTzInfo(last_update)).total_seconds()
        current_mana = int(last_mana + diff_in_seconds * max_mana / MORPHENE_VOTING_MANA_REGENERATION_SECONDS)
        if current_mana > max_mana:
            current_mana = max_mana
        if max_mana > 0:
            current_mana_pct = current_mana / max_mana * 100
        else:
            current_mana_pct = 0
        return {"last_mana": last_mana, "last_update_time": last_update_time,
                "current_mana": current_mana, "max_mana": max_mana, "current_mana_pct": current_mana_pct}

    def get_vests(self, only_own_vests=False):
        """ Returns the account vests
        """
        vests = (self["vesting_shares"])
        if not only_own_vests and "delegated_vesting_shares" in self and "received_vesting_shares" in self:
            vests = vests - (self["delegated_vesting_shares"]) + (self["received_vesting_shares"])

        return vests

    def get_effective_vesting_shares(self):
        """Returns the effective vesting shares"""
        vesting_shares = int(self["vesting_shares"])
        if "delegated_vesting_shares" in self and "received_vesting_shares" in self:
            vesting_shares = vesting_shares - int(self["delegated_vesting_shares"]) + int(self["received_vesting_shares"])
        timestamp = (self["next_vesting_withdrawal"] - addTzInfo(datetime(1970, 1, 1))).total_seconds()
        if timestamp > 0 and "vesting_withdraw_rate" in self and "to_withdraw" in self and "withdrawn" in self:
            vesting_shares -= min(int(self["vesting_withdraw_rate"]), int(self["to_withdraw"]) - int(self["withdrawn"]))
        return vesting_shares

    def get_creator(self):
        """ Returns the account creator or `None` if the account was mined
        """
        if self['mined']:
            return None
        ops = list(self.get_account_history(0, 0))
        if not ops or 'creator' not in ops[0]:
            return None
        return ops[0]['creator']

    def get_manabar_recharge_time_str(self, manabar, recharge_pct_goal=100):
        """ Returns the account manabar recharge time as string

            :param dict manabar: manabar dict from get_manabar() or get_rc_manabar()
            :param float recharge_pct_goal: mana recovery goal in percentage (default is 100)

        """
        remainingTime = self.get_manabar_recharge_timedelta(manabar, recharge_pct_goal=recharge_pct_goal)
        return formatTimedelta(remainingTime)

    def get_manabar_recharge_timedelta(self, manabar, recharge_pct_goal=100):
        """ Returns the account mana recharge time as timedelta object

            :param dict manabar: manabar dict from get_manabar() or get_rc_manabar()
            :param float recharge_pct_goal: mana recovery goal in percentage (default is 100)

        """
        if "current_mana_pct" in manabar:
            missing_rc_pct = recharge_pct_goal - manabar["current_mana_pct"]
        else:
            missing_rc_pct = recharge_pct_goal - manabar["current_pct"]
        if missing_rc_pct < 0:
            return 0
        recharge_seconds = missing_rc_pct * 100 * MORPHENE_VOTING_MANA_REGENERATION_SECONDS / MORPHENE_100_PERCENT
        return timedelta(seconds=recharge_seconds)

    def get_manabar_recharge_time(self, manabar, recharge_pct_goal=100):
        """ Returns the account mana recharge time in minutes

            :param dict manabar: manabar dict from get_manabar() or get_rc_manabar()
            :param float recharge_pct_goal: mana recovery goal in percentage (default is 100)

        """
        return addTzInfo(datetime.utcnow()) + self.get_manabar_recharge_timedelta(manabar, recharge_pct_goal)

    @property
    def available_balances(self):
        """ List balances of an account. This call returns instances of
            :class:`morphenepython.amount.Amount`.
        """
        amount_list = ["balance", "vesting_shares"]
        available_amount = []
        for amount in amount_list:
            if amount in self:
                available_amount.append(self[amount].copy())
        return available_amount

    @property
    def total_balances(self):
        symbols = []
        for balance in self.available_balances:
            symbols.append(balance["symbol"])
        ret = []
        for i in range(len(symbols)):
            balance_sum = self.get_balance(self.available_balances, symbols[i])
            ret.append(balance_sum)
        return ret

    @property
    def balances(self):
        """ Returns all account balances as dictionary
        """
        return self.get_balances()

    def get_balances(self):
        """ Returns all account balances as dictionary

            :returns: Account balances
            :rtype: dictionary

            Sample output:

                .. code-block:: js

                    {
                        'available': [102.985 MORPH, 102.985000 VESTS],
                        'total': [102.985 MORPH, 102.985000 VESTS]
                    }

        """
        return {
            'available': self.available_balances,
            'total': self.total_balances,
        }

    def get_balance(self, balances, symbol):
        """ Obtain the balance of a specific Asset. This call returns instances of
            :class:`morphenepython.amount.Amount`. Available balance types:

            * "available"
            * "total"

            :param str balances: Defines the balance type
            :param symbol: Can be "MORPH" or "VESTS
            :type symbol: str, dict

            .. code-block:: python

                >>> from morphenepython.account import Account
                >>> account = Account("initwitness")
                >>> account.get_balance("available", "MORPH")
                1000000.000 MORPH

        """
        if isinstance(balances, string_types):
            if balances == "available":
                balances = self.available_balances
            elif balances == "total":
                balances = self.total_balances
            else:
                return
        
        if isinstance(symbol, dict) and "symbol" in symbol:
            symbol = symbol["symbol"]

        for b in balances:
            if b["symbol"] == symbol:
                return b
        from .amount import Amount
        return Amount(0, symbol, morphene_instance=self.morphene)

    @property
    def is_fully_loaded(self):
        """ Is this instance fully loaded / e.g. all data available?

            :rtype: bool
        """
        return (self.full)

    def ensure_full(self):
        """Ensure that all data are loaded"""
        if not self.is_fully_loaded:
            self.full = True
            self.refresh()

    def get_owner_history(self, account=None):
        """ Returns the owner history of an account.

            :param str account: When set, a different account is used for the request (Default is object account name)

            :rtype: list

            .. code-block:: python

                >>> from morphenepython.account import Account
                >>> account = Account("morphenepython.app")
                >>> account.get_owner_history()
                []

        """
        if account is None:
            account = self["name"]
        elif isinstance(account, Account):
            account = account["name"]
        if not self.morphene.is_connected():
            raise OfflineHasNoRPCException("No RPC available in offline mode!")
        self.morphene.rpc.set_next_node_on_empty_reply(False)
        return self.morphene.rpc.get_owner_history(account)

    def get_vesting_delegations(self, start_account="", limit=100, account=None):
        """ Returns the vesting delegations by an account.

            :param str account: When set, a different account is used for the request (Default is object account name)
            :param str start_account: delegatee to start with, leave empty to start from the first by name
            :param int limit: maximum number of results to return
            :rtype: list

            .. code-block:: python

                >>> from morphenepython.account import Account
                >>> account = Account("morphenepython.app")
                >>> account.get_vesting_delegations()
                []

        """
        if account is None:
            account = self["name"]
        elif isinstance(account, Account):
            account = account["name"]
        if not self.morphene.is_connected():
            raise OfflineHasNoRPCException("No RPC available in offline mode!")
        self.morphene.rpc.set_next_node_on_empty_reply(False)
        return self.morphene.rpc.get_vesting_delegations(account, start_account, limit)

    def get_withdraw_routes(self, account=None):
        """ Returns the withdraw routes for an account.

            :param str account: When set, a different account is used for the request (Default is object account name)

            :rtype: list

            .. code-block:: python

                >>> from morphenepython.account import Account
                >>> account = Account("morphenepython.app")
                >>> account.get_withdraw_routes()
                []

        """
        if account is None:
            account = self["name"]
        elif isinstance(account, Account):
            account = account["name"]
        if not self.morphene.is_connected():
            raise OfflineHasNoRPCException("No RPC available in offline mode!")
        self.morphene.rpc.set_next_node_on_empty_reply(False)
        return self.morphene.rpc.get_withdraw_routes(account, 'all')

    def get_recovery_request(self, account=None):
        """ Returns the recovery request for an account

            :param str account: When set, a different account is used for the request (Default is object account name)

            :rtype: list

            .. code-block:: python

                >>> from morphenepython.account import Account
                >>> account = Account("morphenepython.app")
                >>> account.get_recovery_request()
                []

        """
        if account is None:
            account = self["name"]
        elif isinstance(account, Account):
            account = account["name"]
        if not self.morphene.is_connected():
            raise OfflineHasNoRPCException("No RPC available in offline mode!")
        self.morphene.rpc.set_next_node_on_empty_reply(False)
        return self.morphene.rpc.find_account_recovery_requests({'account': account}, api="database")['requests']

    def get_escrow(self, escrow_id=0, account=None):
        """ Returns the escrow for a certain account by id

            :param int escrow_id: Id
            :param str account: When set, a different account is used for the request (Default is object account name)

            :rtype: list

            .. code-block:: python

                >>> from morphenepython.account import Account
                >>> account = Account("morphenepython.app")
                >>> account.get_escrow(1234)
                []

        """
        if account is None:
            account = self["name"]
        elif isinstance(account, Account):
            account = account["name"]
        if not self.morphene.is_connected():
            raise OfflineHasNoRPCException("No RPC available in offline mode!")
        self.morphene.rpc.set_next_node_on_empty_reply(False)
        return self.morphene.rpc.find_escrows({'from': account}, api="database")['escrows']

    def verify_account_authority(self, keys, account=None):
        """ Returns true if the signers have enough authority to authorize an account.

            :param list keys: public key
            :param str account: When set, a different account is used for the request (Default is object account name)

            :rtype: dictionary

            .. code-block:: python

                >>> from morphenepython.account import Account
                >>> account = Account("initwitness")
                >>> print(account.verify_account_authority(["MPH7Q2rLBqzPzFeteQZewv9Lu3NLE69fZoLeL6YK59t7UmssCBNTU"])["valid"])
                False

        """
        if account is None:
            account = self["name"]
        elif isinstance(account, Account):
            account = account["name"]
        if not self.morphene.is_connected():
            raise OfflineHasNoRPCException("No RPC available in offline mode!")
        if not isinstance(keys, list):
            keys = [keys]
        self.morphene.rpc.set_next_node_on_empty_reply(False)
        try:
            return self.morphene.rpc.verify_account_authority({'account': account, 'signers': keys}, api="database")
        except MissingRequiredActiveAuthority:
            return {'valid': False}

    def get_expiring_vesting_delegations(self, after=None, limit=1000, account=None):
        """ Returns the expirations for vesting delegations.

            :param datetime after: expiration after
            :param int limit: limits number of shown entries
            :param str account: When set, a different account is used for the request (Default is object account name)

            :rtype: list

            .. code-block:: python

                >>> from morphenepython.account import Account
                >>> account = Account("morphenepython.app")
                >>> account.get_expiring_vesting_delegations()
                []

        """
        if account is None:
            account = self["name"]
        elif isinstance(account, Account):
            account = account["name"]
        if not self.morphene.is_connected():
            raise OfflineHasNoRPCException("No RPC available in offline mode!")
        self.morphene.rpc.set_next_node_on_empty_reply(False)
        if after is None:
            after = addTzInfo(datetime.utcnow()) - timedelta(days=8)
        return self.morphene.rpc.get_expiring_vesting_delegations(account, formatTimeString(after), limit)

    def virtual_op_count(self, until=None):
        """ Returns the number of individual account transactions

            :rtype: list
        """
        if until is not None:
            return self.estimate_virtual_op_num(until, stop_diff=1)
        else:
            try:
                op_count = 0
                op_count = self._get_account_history(start=-1, limit=0)
                if isinstance(op_count, list) and len(op_count) > 0 and len(op_count[0]) > 0:
                    return op_count[0][0]
                else:
                    return 0
            except IndexError:
                return 0

    def _get_account_history(self, account=None, start=-1, limit=0):
        if account is None:
            account = self
        account = Account(account, morphene_instance=self.morphene)
        if not self.morphene.is_connected():
            raise OfflineHasNoRPCException("No RPC available in offline mode!")
        self.morphene.rpc.set_next_node_on_empty_reply(False)
        ret = self.morphene.rpc.get_account_history(account["name"], start, limit, api="database")
        if len(ret) == 0 and limit == 0:
            ret = self.morphene.rpc.get_account_history(account["name"], start, limit + 1, api="database")
        return ret

    def estimate_virtual_op_num(self, blocktime, stop_diff=0, max_count=100):
        """ Returns an estimation of an virtual operation index for a given time or blockindex

            :param blocktime: start time or start block index from which account
                operation should be fetched
            :type blocktime: int, datetime
            :param int stop_diff: Sets the difference between last estimation and
                new estimation at which the estimation stops. Must not be zero. (default is 1)
            :param int max_count: sets the maximum number of iterations. -1 disables this (default 100)

            .. testsetup::

                import pytz
                from morphenepython.account import Account
                from morphenepython.blockchain import Blockchain
                from datetime import datetime, timedelta
                from timeit import time as t

            .. testcode::

                utc = pytz.timezone('UTC')
                start_time = utc.localize(datetime.utcnow()) - timedelta(days=7)
                acc = Account("initwitness")
                start_op = acc.estimate_virtual_op_num(start_time)

                b = Blockchain()
                start_block_num = b.get_estimated_block_num(start_time)
                start_op2 = acc.estimate_virtual_op_num(start_block_num)

            .. testcode::

                acc = Account("initwitness")
                block_num = 21248120
                start = t.time()
                op_num = acc.estimate_virtual_op_num(block_num, stop_diff=1, max_count=10)
                stop = t.time()
                print(stop - start)
                for h in acc.get_account_history(op_num, 0):
                    block_est = h["block"]
                print(block_est - block_num)

        """
        def get_blocknum(index):
            op = self._get_account_history(start=(index))
            return op[0][1]['block']

        max_index = self.virtual_op_count()
        if max_index < stop_diff:
            return 0

        # calculate everything with block numbers
        created = get_blocknum(0)

        # convert blocktime to block number if given as a datetime/date/time
        if isinstance(blocktime, (datetime, date, time)):
            b = Blockchain(morphene_instance=self.morphene)
            target_blocknum = b.get_estimated_block_num(addTzInfo(blocktime), accurate=True)
        else:
            target_blocknum = blocktime

        # the requested blocknum/timestamp is before the account creation date
        if target_blocknum <= created:
            return 0

        # get the block number from the account's latest operation
        latest_blocknum = get_blocknum(-1)

        # requested blocknum/timestamp is after the latest account operation
        if target_blocknum >= latest_blocknum:
            return max_index

        # all account ops in a single block
        if latest_blocknum - created == 0:
            return 0

        # set initial search range
        op_num = 0
        op_lower = 0
        block_lower = created
        op_upper = max_index
        block_upper = latest_blocknum
        last_op_num = None
        cnt = 0

        while True:
            # check if the maximum number of iterations was reached
            if max_count != -1 and cnt >= max_count:
                # did not converge, return the current state
                return op_num

            # linear approximation between the known upper and
            # lower bounds for the first iteration
            if cnt < 1:
                op_num = int((target_blocknum - block_lower) / (block_upper - block_lower) * (op_upper - op_lower) + op_lower)
            else:
                # divide and conquer for the following iterations
                op_num = int((op_upper + op_lower) / 2)
                if op_upper == op_lower + 1:  # round up if we're close to target
                    op_num += 1

            # get block number for current op number estimation
            if op_num != last_op_num:
                block_num = get_blocknum(op_num)
                last_op_num = op_num

            # check if the required accuracy was reached
            if op_upper - op_lower <= stop_diff or \
               op_upper == op_lower + 1:
                return op_num

            # set new upper/lower boundaries for next iteration
            if block_num < target_blocknum:
                # current op number was too low -> search upwards
                op_lower = op_num
                block_lower = block_num
            else:
                # current op number was too high or matched the target block
                # -> search downwards
                op_upper = op_num
                block_upper = block_num
            cnt += 1

    def get_account_history(self, index, limit, order=-1, start=None, stop=None, use_block_num=True, only_ops=[], exclude_ops=[], raw_output=False):
        """ Returns a generator for individual account transactions. This call can be used in a
            ``for`` loop.

            :param int index: first number of transactions to return
            :param int limit: limit number of transactions to return
            :param start: start number/date of transactions to
                return (*optional*)
            :type start: int, datetime
            :param stop: stop number/date of transactions to
                return (*optional*)
            :type stop: int, datetime
            :param bool use_block_num: if true, start and stop are block numbers, otherwise virtual OP count numbers.
            :param array only_ops: Limit generator by these
                operations (*optional*)
            :param array exclude_ops: Exclude thse operations from
                generator (*optional*)
            :param int batch_size: internal api call batch size (*optional*)
            :param int order: 1 for chronological, -1 for reverse order
            :param bool raw_output: if False, the output is a dict, which
                includes all values. Otherwise, the output is list.

            .. note::

                only_ops and exclude_ops takes an array of strings:
                The full list of operation ID's can be found in
                morphenepythonbase.operationids.ops.
                Example: ['transfer', 'vote']

        """
        if order != -1 and order != 1:
            raise ValueError("order must be -1 or 1!")
        # self.morphene.rpc.set_next_node_on_empty_reply(True)
        txs = self._get_account_history(start=index, limit=limit)
        if txs is None:
            return
        start = addTzInfo(start)
        stop = addTzInfo(stop)

        if order == -1:
            txs_list = reversed(txs)
        else:
            txs_list = txs
        for item in txs_list:
            item_index, event = item
            if start and isinstance(start, (datetime, date, time)):
                timediff = start - formatTimeString(event["timestamp"])
                if timediff.total_seconds() * float(order) > 0:
                    continue
            elif start is not None and use_block_num and order == 1 and event['block'] < start:
                continue
            elif start is not None and use_block_num and order == -1 and event['block'] > start:
                continue
            elif start is not None and not use_block_num and order == 1 and item_index < start:
                continue
            elif start is not None and not use_block_num and order == -1 and item_index > start:
                continue
            if stop is not None and isinstance(stop, (datetime, date, time)):
                timediff = stop - formatTimeString(event["timestamp"])
                if timediff.total_seconds() * float(order) < 0:
                    return
            elif stop is not None and use_block_num and order == 1 and event['block'] > stop:
                return
            elif stop is not None and use_block_num and order == -1 and event['block'] < stop:
                return
            elif stop is not None and not use_block_num and order == 1 and item_index > stop:
                return
            elif stop is not None and not use_block_num and order == -1 and item_index < stop:
                return

            if isinstance(event['op'], list):
                op_type, op = event['op']
            else:
                op_type = event['op']['type']
                if len(op_type) > 10 and op_type[len(op_type) - 10:] == "_operation":
                    op_type = op_type[:-10]
                op = event['op']['value']
            block_props = remove_from_dict(event, keys=['op'], keep_keys=False)

            def construct_op(account_name):
                # verbatim output from morphened
                if raw_output:
                    return item

                # index can change during reindexing in
                # future hard-forks. Thus we cannot take it for granted.
                immutable = op.copy()
                immutable.update(block_props)
                immutable.update({
                    'account': account_name,
                    'type': op_type,
                })
                _id = Blockchain.hash_op(immutable)
                immutable.update({
                    '_id': _id,
                    'index': item_index,
                })
                return immutable

            if exclude_ops and op_type in exclude_ops:
                continue
            if not only_ops or op_type in only_ops:
                yield construct_op(self["name"])

    def history(
        self, start=None, stop=None, use_block_num=True,
        only_ops=[], exclude_ops=[], batch_size=1000, raw_output=False
    ):
        """ Returns a generator for individual account transactions. The
            earlist operation will be first. This call can be used in a
            ``for`` loop.

            :param start: start number/date of transactions to return (*optional*)
            :type start: int, datetime
            :param stop: stop number/date of transactions to return (*optional*)
            :type stop: int, datetime
            :param bool use_block_num: if true, start and stop are block numbers,
                otherwise virtual OP count numbers.
            :param array only_ops: Limit generator by these
                operations (*optional*)
            :param array exclude_ops: Exclude thse operations from
                generator (*optional*)
            :param int batch_size: internal api call batch size (*optional*)
            :param bool raw_output: if False, the output is a dict, which
                includes all values. Otherwise, the output is list.

            .. note::
                only_ops and exclude_ops takes an array of strings:
                The full list of operation ID's can be found in
                morphenepythonbase.operationids.ops.
                Example: ['transfer', 'vote']

            .. testsetup::

                from morphenepython.account import Account
                from datetime import datetime

            .. testcode::

                acc = Account("initwitness")
                max_op_count = acc.virtual_op_count()
                # Returns the 100 latest operations
                acc_op = []
                for h in acc.history(start=max_op_count - 99, stop=max_op_count, use_block_num=False):
                    acc_op.append(h)
                len(acc_op)

            .. testoutput::

                100

            .. testcode::

                acc = Account("test")
                max_block = 21990141
                # Returns the account operation inside the last 100 block. This can be empty.
                acc_op = []
                for h in acc.history(start=max_block - 99, stop=max_block, use_block_num=True):
                    acc_op.append(h)
                len(acc_op)

            .. testoutput::

                0

            .. testcode::

                acc = Account("test")
                start_time = datetime(2018, 3, 1, 0, 0, 0)
                stop_time = datetime(2018, 3, 2, 0, 0, 0)
                # Returns the account operation from 1.4.2018 back to 1.3.2018
                acc_op = []
                for h in acc.history(start=start_time, stop=stop_time):
                    acc_op.append(h)
                len(acc_op)

            .. testoutput::

                0

        """
        _limit = batch_size
        max_index = self.virtual_op_count()
        if not max_index:
            return
        start = addTzInfo(start)
        stop = addTzInfo(stop)
        if start is not None and not use_block_num and not isinstance(start, (datetime, date, time)):
            start_index = start
        elif start is not None and max_index > batch_size:
            op_est = self.estimate_virtual_op_num(start, stop_diff=1)
            est_diff = 0
            if isinstance(start, (datetime, date, time)):
                for h in self.get_account_history(op_est, 0):
                    block_date = formatTimeString(h["timestamp"])
                while(op_est > est_diff + batch_size and block_date > start):
                    est_diff += batch_size
                    if op_est - est_diff < 0:
                        est_diff = op_est
                    for h in self.get_account_history(op_est - est_diff, 0):
                        block_date = formatTimeString(h["timestamp"])
            elif not isinstance(start, (datetime, date, time)):
                for h in self.get_account_history(op_est, 0):
                    block_num = h["block"]
                while(op_est > est_diff + batch_size and block_num > start):
                    est_diff += batch_size
                    if op_est - est_diff < 0:
                        est_diff = op_est
                    for h in self.get_account_history(op_est - est_diff, 0):
                        block_num = h["block"]
            start_index = op_est - est_diff
        else:
            start_index = 0

        first = start_index + _limit
        if first > max_index:
            _limit = max_index - start_index + 1
            first = start_index + _limit
        last_round = False
        if _limit < 0:
            return
        while True:
            # RPC call
            for item in self.get_account_history(first, _limit, start=None, stop=None, order=1, raw_output=raw_output):
                if raw_output:
                    item_index, event = item
                    op_type, op = event['op']
                    timestamp = event["timestamp"]
                    block_num = event["block"]
                else:
                    item_index = item['index']
                    op_type = item['type']
                    timestamp = item["timestamp"]
                    block_num = item["block"]
                if start is not None and isinstance(start, (datetime, date, time)):
                    timediff = start - formatTimeString(timestamp)
                    if timediff.total_seconds() > 0:
                        continue
                elif start is not None and use_block_num and block_num < start:
                    continue
                elif start is not None and not use_block_num and item_index < start:
                    continue
                if stop is not None and isinstance(stop, (datetime, date, time)):
                    timediff = stop - formatTimeString(timestamp)
                    if timediff.total_seconds() < 0:
                        first = max_index + _limit
                        return
                elif stop is not None and use_block_num and block_num > stop:
                    return
                elif stop is not None and not use_block_num and item_index > stop:
                    return
                if exclude_ops and op_type in exclude_ops:
                    continue
                if not only_ops or op_type in only_ops:
                    yield item
            if first < max_index and first + _limit >= max_index and not last_round:
                _limit = max_index - first - 1
                first = max_index
                last_round = True
            else:
                first += (_limit + 1)
                if stop is not None and not use_block_num and isinstance(stop, int) and first >= stop + _limit:
                    break
                elif first > max_index or last_round:
                    break

    def history_reverse(
        self, start=None, stop=None, use_block_num=True,
        only_ops=[], exclude_ops=[], batch_size=1000, raw_output=False
    ):
        """ Returns a generator for individual account transactions. The
            latest operation will be first. This call can be used in a
            ``for`` loop.

            :param start: start number/date of transactions to
                return. If negative the virtual_op_count is added. (*optional*)
            :type start: int, datetime
            :param stop: stop number/date of transactions to
                return. If negative the virtual_op_count is added. (*optional*)
            :type stop: int, datetime
            :param bool use_block_num: if true, start and stop are block numbers,
                otherwise virtual OP count numbers.
            :param array only_ops: Limit generator by these
                operations (*optional*)
            :param array exclude_ops: Exclude thse operations from
                generator (*optional*)
            :param int batch_size: internal api call batch size (*optional*)
            :param bool raw_output: if False, the output is a dict, which
                includes all values. Otherwise, the output is list.

            .. note::
                only_ops and exclude_ops takes an array of strings:
                The full list of operation ID's can be found in
                morphenepythonbase.operationids.ops.
                Example: ['transfer', 'vote']

            .. testsetup::

                from morphenepython.account import Account
                from datetime import datetime

            .. testcode::

                acc = Account("initwitness")
                max_op_count = acc.virtual_op_count()
                # Returns the 100 latest operations
                acc_op = []
                for h in acc.history_reverse(start=max_op_count, stop=max_op_count - 99, use_block_num=False):
                    acc_op.append(h)
                len(acc_op)

            .. testoutput::

                100

            .. testcode::

                max_block = 21990141
                acc = Account("test")
                # Returns the account operation inside the last 100 block. This can be empty.
                acc_op = []
                for h in acc.history_reverse(start=max_block, stop=max_block-100, use_block_num=True):
                    acc_op.append(h)
                len(acc_op)

            .. testoutput::

                0

            .. testcode::

                acc = Account("test")
                start_time = datetime(2018, 4, 1, 0, 0, 0)
                stop_time = datetime(2018, 3, 1, 0, 0, 0)
                # Returns the account operation from 1.4.2018 back to 1.3.2018
                acc_op = []
                for h in acc.history_reverse(start=start_time, stop=stop_time):
                    acc_op.append(h)
                len(acc_op)

            .. testoutput::

                0

        """
        _limit = batch_size
        first = self.virtual_op_count()
        start = addTzInfo(start)
        stop = addTzInfo(stop)
        if not first or not batch_size:
            return
        if start is not None and isinstance(start, int) and start < 0 and not use_block_num:
            start += first
        elif start is not None and isinstance(start, int) and not use_block_num:
            first = start
        elif start is not None and first > batch_size:
            op_est = self.estimate_virtual_op_num(start, stop_diff=1)
            est_diff = 0
            if isinstance(start, (datetime, date, time)):
                for h in self.get_account_history(op_est, 0):
                    block_date = formatTimeString(h["timestamp"])
                while(op_est + est_diff + batch_size < first and block_date < start):
                    est_diff += batch_size
                    if op_est + est_diff > first:
                        est_diff = first - op_est
                    for h in self.get_account_history(op_est + est_diff, 0):
                        block_date = formatTimeString(h["timestamp"])
            else:
                for h in self.get_account_history(op_est, 0):
                    block_num = h["block"]
                while(op_est + est_diff + batch_size < first and block_num < start):
                    est_diff += batch_size
                    if op_est + est_diff > first:
                        est_diff = first - op_est
                    for h in self.get_account_history(op_est + est_diff, 0):
                        block_num = h["block"]
            first = op_est + est_diff
        if stop is not None and isinstance(stop, int) and stop < 0 and not use_block_num:
            stop += first

        while True:
            # RPC call
            if first - _limit < 0:
                _limit = first
            for item in self.get_account_history(first, _limit, start=None, stop=None, order=-1, only_ops=only_ops, exclude_ops=exclude_ops, raw_output=raw_output):
                if raw_output:
                    item_index, event = item
                    op_type, op = event['op']
                    timestamp = event["timestamp"]
                    block_num = event["block"]
                else:
                    item_index = item['index']
                    op_type = item['type']
                    timestamp = item["timestamp"]
                    block_num = item["block"]
                if start is not None and isinstance(start, (datetime, date, time)):
                    timediff = start - formatTimeString(timestamp)
                    if timediff.total_seconds() < 0:
                        continue
                elif start is not None and use_block_num and block_num > start:
                    continue
                elif start is not None and not use_block_num and item_index > start:
                    continue
                if stop is not None and isinstance(stop, (datetime, date, time)):
                    timediff = stop - formatTimeString(timestamp)
                    if timediff.total_seconds() > 0:
                        first = 0
                        return
                elif stop is not None and use_block_num and block_num < stop:
                    first = 0
                    return
                elif stop is not None and not use_block_num and item_index < stop:
                    first = 0
                    return
                if exclude_ops and op_type in exclude_ops:
                    continue
                if not only_ops or op_type in only_ops:
                    yield item
            first -= (_limit + 1)
            if first < 1:
                break

    def update_account_profile(self, profile, account=None, **kwargs):
        """ Update an account's profile in json_metadata

            :param dict profile: The new profile to use
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)

            Sample profile structure:

            .. code-block:: js

                {
                    'name': 'Andrew Chaney',
                    'about': 'Morphene Blockchain Founder',
                    'location': 'Cryptoland',
                    'website': 'https://github.com/morphene/morphene-python'
                }

            .. code-block:: python

                from morphenepython.account import Account
                account = Account("test")
                profile = account.profile
                profile["about"] = "test account"
                account.update_account_profile(profile)

        """
        if account is None:
            account = self
        else:
            account = Account(account, morphene_instance=self.morphene)

        if not isinstance(profile, dict):
            raise ValueError("Profile must be a dict type!")

        if self['json_metadata'] == '':
            metadata = {}
        else:
            metadata = json.loads(self['json_metadata'])
        metadata["profile"] = profile
        return self.update_account_metadata(metadata)

    def update_account_metadata(self, metadata, account=None, **kwargs):
        """ Update an account's profile in json_metadata

            :param dict metadata: The new metadata to use
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)

        """
        if account is None:
            account = self
        else:
            account = Account(account, morphene_instance=self.morphene)
        if isinstance(metadata, dict):
            metadata = json.dumps(metadata)
        elif not isinstance(metadata, str):
            raise ValueError("Profile must be a dict or string!")
        op = operations.Account_update(
            **{
                "account": account["name"],
                "memo_key": account["memo_key"],
                "json_metadata": metadata,
                "prefix": self.morphene.prefix,
            })
        return self.morphene.finalizeOp(op, account, "active", **kwargs)

    # -------------------------------------------------------------------------
    #  Approval and Disapproval of witnesses
    # -------------------------------------------------------------------------
    def approvewitness(self, witness, account=None, approve=True, **kwargs):
        """ Approve a witness

            :param list witness: list of Witness name or id
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)

        """
        if account is None:
            account = self
        else:
            account = Account(account, morphene_instance=self.morphene)

        # if not isinstance(witnesses, (list, set, tuple)):
        #     witnesses = {witnesses}

        # for witness in witnesses:
        #     witness = Witness(witness, morphene_instance=self)

        op = operations.Account_witness_vote(**{
            "account": account["name"],
            "witness": witness,
            "approve": approve,
            "prefix": self.morphene.prefix,
        })
        return self.morphene.finalizeOp(op, account, "active", **kwargs)

    def disapprovewitness(self, witness, account=None, **kwargs):
        """ Disapprove a witness

            :param list witness: list of Witness name or id
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        return self.approvewitness(
            witness=witness, account=account, approve=False)

    def update_memo_key(self, key, account=None, **kwargs):
        """ Update an account's memo public key

            This method does **not** add any private keys to your
            wallet but merely changes the memo public key.

            :param str key: New memo public key
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        if account is None:
            account = self
        else:
            account = Account(account, morphene_instance=self.morphene)

        PublicKey(key, prefix=self.morphene.prefix)

        account["memo_key"] = key
        op = operations.Account_update(**{
            "account": account["name"],
            "memo_key": account["memo_key"],
            "json_metadata": account["json_metadata"],
            "prefix": self.morphene.prefix,
        })
        return self.morphene.finalizeOp(op, account, "active", **kwargs)

    def update_account_keys(self, new_password, account=None, **kwargs):
        """ Updates all account keys

            This method does **not** add any private keys to your
            wallet but merely changes the memo public key.

            :param str new_password: is used to derive the owner, active,
                posting and memo key
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        if account is None:
            account = self
        else:
            account = Account(account, morphene_instance=self.morphene)

        key_auths = {}
        for role in ['owner', 'active', 'posting', 'memo']:
            pk = PasswordKey(account['name'], new_password, role=role)
            key_auths[role] = format(pk.get_public_key(), self.morphene.prefix)

        op = operations.Account_update(**{
            "account": account["name"],
            'owner': {'account_auths': [],
                      'key_auths': [[key_auths['owner'], 1]],
                      "address_auths": [],
                      'weight_threshold': 1},
            'active': {'account_auths': [],
                       'key_auths': [[key_auths['active'], 1]],
                       "address_auths": [],
                       'weight_threshold': 1},
            'posting': {'account_auths': account['posting']['account_auths'],
                        'key_auths': [[key_auths['posting'], 1]],
                        "address_auths": [],
                        'weight_threshold': 1},
            'memo_key': key_auths['memo'],
            "json_metadata": account['json_metadata'],
            "prefix": self.morphene.prefix,
        })

        return self.morphene.finalizeOp(op, account, "owner", **kwargs)

    def change_recovery_account(self, new_recovery_account,
                                account=None, **kwargs):
        """Request a change of the recovery account.

        .. note:: It takes 30 days until the change applies. Another
            request within this time restarts the 30 day period.
            Setting the current recovery account again cancels any
            pending change request.

        :param str new_recovery_account: account name of the new
            recovery account
        :param str account: (optional) the account to change the
            recovery account for (defaults to ``default_account``)

        """
        if account is None:
            account = self
        else:
            account = Account(account, morphene_instance=self.morphene)
        # Account() lookup to make sure the new account is valid
        new_rec_acc = Account(new_recovery_account,
                              morphene_instance=self.morphene)
        op = operations.Change_recovery_account(**{
            'account_to_recover': account['name'],
            'new_recovery_account': new_rec_acc['name'],
            'extensions': []
        })
        return self.morphene.finalizeOp(op, account, "owner", **kwargs)

    # -------------------------------------------------------------------------
    # Simple Transfer
    # -------------------------------------------------------------------------
    def transfer(self, to, amount, asset, memo="", account=None, **kwargs):
        """ Transfer an asset to another account.

            :param str to: Recipient
            :param float amount: Amount to transfer
            :param str asset: Asset to transfer
            :param str memo: (optional) Memo, may begin with `#` for encrypted
                messaging
            :param str account: (optional) the source account for the transfer
                if not ``default_account``


            Transfer example:

            .. code-block:: python

                from morphenepython.account import Account
                from morphenepython import MorpheneClient
                active_wif = "5xxxx"
                stm = MorpheneClient(keys=[active_wif])
                acc = Account("test", morphene_instance=stm)
                acc.transfer("test1", 1, "MORPH", "test")

        """

        if account is None:
            account = self
        else:
            account = Account(account, morphene_instance=self.morphene)
        amount = Amount(amount, asset, morphene_instance=self.morphene)
        to = Account(to, morphene_instance=self.morphene)
        if memo and memo[0] == "#":
            from .memo import Memo
            memoObj = Memo(
                from_account=account,
                to_account=to,
                morphene_instance=self.morphene
            )
            memo = memoObj.encrypt(memo[1:])["message"]

        op = operations.Transfer(**{
            "amount": amount,
            "to": to["name"],
            "memo": memo,
            "from": account["name"],
            "prefix": self.morphene.prefix,
        })
        return self.morphene.finalizeOp(op, account, "active", **kwargs)

    def transfer_to_vesting(self, amount, to=None, account=None, **kwargs):
        """ Vest MORPH

            :param float amount: Amount to transfer
            :param str to: Recipient (optional) if not set equal to account
            :param str account: (optional) the source account for the transfer
                if not ``default_account``
        """
        if account is None:
            account = self
        else:
            account = Account(account, morphene_instance=self.morphene)
        if to is None:
            to = self  # powerup on the same account
        else:
            to = Account(to, morphene_instance=self.morphene)
        amount = self._check_amount(amount, self.morphene.morph_symbol)

        to = Account(to, morphene_instance=self.morphene)

        op = operations.Transfer_to_vesting(**{
            "from": account["name"],
            "to": to["name"],
            "amount": amount,
            "prefix": self.morphene.prefix,
        })
        return self.morphene.finalizeOp(op, account, "active", **kwargs)

    def _check_amount(self, amount, symbol):
        if isinstance(amount, (float, integer_types)):
            amount = Amount(amount, symbol, morphene_instance=self.morphene)
        elif isinstance(amount, string_types) and amount.replace('.', '', 1).replace(',', '', 1).isdigit():
            amount = Amount(float(amount), symbol, morphene_instance=self.morphene)
        else:
            amount = Amount(amount, morphene_instance=self.morphene)
        if not amount["symbol"] == symbol:
            raise AssertionError()
        return amount

    def delegate_vesting_shares(self, to_account, vesting_shares,
                                account=None, **kwargs):
        """ Delegate VESTS to another account.

        :param str to_account: Account we are delegating shares to
            (delegatee).
        :param str vesting_shares: Amount of VESTS to delegate eg. `10000
            VESTS`.
        :param str account: The source account (delegator). If not specified,
            ``default_account`` is used.
        """
        if account is None:
            account = self
        else:
            account = Account(account, morphene_instance=self.morphene)
        to_account = Account(to_account, morphene_instance=self.morphene)
        if to_account is None:
            raise ValueError("You need to provide a to_account")
        vesting_shares = self._check_amount(vesting_shares, self.morphene.vests_symbol)

        op = operations.Delegate_vesting_shares(
            **{
                "delegator": account["name"],
                "delegatee": to_account["name"],
                "vesting_shares": vesting_shares,
                "prefix": self.morphene.prefix,
            })
        return self.morphene.finalizeOp(op, account, "active", **kwargs)

    def withdraw_vesting(self, amount, account=None, **kwargs):
        """ Withdraw VESTS from the vesting account.

            :param float amount: number of VESTS to withdraw over a period of
                13 weeks
            :param str account: (optional) the source account for the transfer
                if not ``default_account``

    """
        if account is None:
            account = self
        else:
            account = Account(account, morphene_instance=self.morphene)
        amount = self._check_amount(amount, self.morphene.vests_symbol)

        op = operations.Withdraw_vesting(
            **{
                "account": account["name"],
                "vesting_shares": amount,
                "prefix": self.morphene.prefix,
            })

        return self.morphene.finalizeOp(op, account, "active", **kwargs)

    def set_withdraw_vesting_route(self,
                                   to,
                                   percentage=100,
                                   account=None,
                                   auto_vest=False, **kwargs):
        """ Set up a vesting withdraw route. When vesting shares are
            withdrawn, they will be routed to these accounts based on the
            specified weights.

            :param str to: Recipient of the vesting withdrawal
            :param float percentage: The percent of the withdraw to go
                to the 'to' account.
            :param str account: (optional) the vesting account
            :param bool auto_vest: Set to true if the 'to' account
                should receive the VESTS as VESTS, or false if it should
                receive them as MORPH. (defaults to ``False``)

        """
        if account is None:
            account = self
        else:
            account = Account(account, morphene_instance=self.morphene)
        op = operations.Set_withdraw_vesting_route(
            **{
                "from_account": account["name"],
                "to_account": to,
                "percent": int(percentage * MORPHENE_1_PERCENT),
                "auto_vest": auto_vest
            })

        return self.morphene.finalizeOp(op, account, "active", **kwargs)

    def allow(
        self, foreign, weight=None, permission="posting",
        account=None, threshold=None, **kwargs
    ):
        """ Give additional access to an account by some other public
            key or account.

            :param str foreign: The foreign account that will obtain access
            :param int weight: (optional) The weight to use. If not
                define, the threshold will be used. If the weight is
                smaller than the threshold, additional signatures will
                be required. (defaults to threshold)
            :param str permission: (optional) The actual permission to
                modify (defaults to ``posting``)
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
            :param int threshold: (optional) The threshold that needs to be
                reached by signatures to be able to interact
        """
        from copy import deepcopy
        if account is None:
            account = self
        else:
            account = Account(account, morphene_instance=self.morphene)

        if permission not in ["owner", "posting", "active"]:
            raise ValueError(
                "Permission needs to be either 'owner', 'posting', or 'active"
            )
        account = Account(account, morphene_instance=self.morphene)

        if permission not in account:
            account = Account(account, morphene_instance=self.morphene, lazy=False, full=True)
            account.clear_cache()
            account.refresh()
        if permission not in account:
            account = Account(account, morphene_instance=self.morphene)
        if permission not in account:
            raise AssertionError("Could not access permission")

        if not weight:
            weight = account[permission]["weight_threshold"]

        authority = deepcopy(account[permission])
        try:
            pubkey = PublicKey(foreign, prefix=self.morphene.prefix)
            authority["key_auths"].append([
                str(pubkey),
                weight
            ])
        except:
            try:
                foreign_account = Account(foreign, morphene_instance=self.morphene)
                authority["account_auths"].append([
                    foreign_account["name"],
                    weight
                ])
            except:
                raise ValueError(
                    "Unknown foreign account or invalid public key"
                )
        if threshold:
            authority["weight_threshold"] = threshold
            self.morphene._test_weights_treshold(authority)

        op = operations.Account_update(**{
            "account": account["name"],
            permission: authority,
            "memo_key": account["memo_key"],
            "json_metadata": account["json_metadata"],
            "prefix": self.morphene.prefix
        })
        if permission == "owner":
            return self.morphene.finalizeOp(op, account, "owner", **kwargs)
        else:
            return self.morphene.finalizeOp(op, account, "active", **kwargs)

    def disallow(
        self, foreign, permission="posting",
        account=None, threshold=None, **kwargs
    ):
        """ Remove additional access to an account by some other public
            key or account.

            :param str foreign: The foreign account that will obtain access
            :param str permission: (optional) The actual permission to
                modify (defaults to ``posting``)
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
            :param int threshold: The threshold that needs to be reached
                by signatures to be able to interact
        """
        if account is None:
            account = self
        else:
            account = Account(account, morphene_instance=self.morphene)

        if permission not in ["owner", "active", "posting"]:
            raise ValueError(
                "Permission needs to be either 'owner', 'posting', or 'active"
            )
        authority = account[permission]

        try:
            pubkey = PublicKey(foreign, prefix=self.morphene.prefix)
            affected_items = list(
                [x for x in authority["key_auths"] if x[0] == str(pubkey)])
            authority["key_auths"] = list([x for x in authority["key_auths"] if x[0] != str(pubkey)])
        except:
            try:
                foreign_account = Account(foreign, morphene_instance=self.morphene)
                affected_items = list(
                    [x for x in authority["account_auths"] if x[0] == foreign_account["name"]])
                authority["account_auths"] = list([x for x in authority["account_auths"] if x[0] != foreign_account["name"]])
            except:
                raise ValueError(
                    "Unknown foreign account or unvalid public key"
                )

        if not affected_items:
            raise ValueError("Changes nothing!")
        removed_weight = affected_items[0][1]

        # Define threshold
        if threshold:
            authority["weight_threshold"] = threshold

        # Correct threshold (at most by the amount removed from the
        # authority)
        try:
            self.morphene._test_weights_treshold(authority)
        except:
            log.critical(
                "The account's threshold will be reduced by %d"
                % (removed_weight)
            )
            authority["weight_threshold"] -= removed_weight
            self.morphene._test_weights_treshold(authority)

        op = operations.Account_update(**{
            "account": account["name"],
            permission: authority,
            "memo_key": account["memo_key"],
            "json_metadata": account["json_metadata"],
            "prefix": self.morphene.prefix,
        })
        if permission == "owner":
            return self.morphene.finalizeOp(op, account, "owner", **kwargs)
        else:
            return self.morphene.finalizeOp(op, account, "active", **kwargs)


class AccountsObject(list):
    def printAsTable(self):
        t = PrettyTable(["Name"])
        t.align = "l"
        for acc in self:
            t.add_row([acc['name']])
        print(t)

    def print_summarize_table(self, tag_type="Follower", return_str=False, **kwargs):
        t = PrettyTable([
            "Key", "Value"
        ])
        t.align = "r"
        t.add_row([tag_type + " count", str(len(self))])
        own_mvest = []
        eff_sp = []
        last_vote_h = []
        last_post_d = []
        no_vote = 0
        no_post = 0
        for f in self:
            own_mvest.append(float(f.balances["available"][2]) / 1e6)
            eff_sp.append(f.get_vests())
            last_vote = addTzInfo(datetime.utcnow()) - (f["last_vote_time"])
            if last_vote.days >= 365:
                no_vote += 1
            else:
                last_vote_h.append(last_vote.total_seconds() / 60 / 60)
            last_post = addTzInfo(datetime.utcnow()) - (f["last_root_post"])
            if last_post.days >= 365:
                no_post += 1
            else:
                last_post_d.append(last_post.total_seconds() / 60 / 60 / 24)

        t.add_row(["Summed MVest value", "%.2f" % sum(own_mvest)])
        if (len(eff_sp) > 0):
            t.add_row(["Summed eff. VESTS", "%.2f" % sum(eff_sp)])
            t.add_row(["Mean eff. VESTS", "%.2f" % (sum(eff_sp) / len(eff_sp))])
            t.add_row(["Max eff. VESTS", "%.2f" % max(eff_sp)])
        if (len(last_vote_h) > 0):
            t.add_row(["Mean last vote diff in hours", "%.2f" % (sum(last_vote_h) / len(last_vote_h))])
        if len(last_post_d) > 0:
            t.add_row(["Mean last post diff in days", "%.2f" % (sum(last_post_d) / len(last_post_d))])
        t.add_row([tag_type + " without vote in 365 days", no_vote])
        t.add_row([tag_type + " without post in 365 days", no_post])
        if return_str:
            return t.get_string(**kwargs)
        else:
            print(t.get_string(**kwargs))


class Accounts(AccountsObject):
    """ Obtain a list of accounts

        :param list name_list: list of accounts to fetch
        :param int batch_limit: (optional) maximum number of accounts
            to fetch per call, defaults to 100
        :param MorpheneClient morphene_instance: MorpheneClient() instance to use when
            accessing a RPCcreator = Account(creator, morphene_instance=self)
    """
    def __init__(self, name_list, batch_limit=100, lazy=False, full=True, morphene_instance=None):
        self.morphene = morphene_instance or shared_morphene_instance()
        if not self.morphene.is_connected():
            return
        accounts = []
        name_cnt = 0

        while name_cnt < len(name_list):
            self.morphene.rpc.set_next_node_on_empty_reply(False)
            accounts += self.morphene.rpc.get_accounts(name_list[name_cnt:batch_limit + name_cnt])
            name_cnt += batch_limit

        super(Accounts, self).__init__(
            [
                Account(x, lazy=lazy, full=full, morphene_instance=self.morphene)
                for x in accounts
            ]
        )
