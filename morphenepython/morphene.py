# This Python file uses the following encoding: utf-8
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import str
from builtins import object
import json
import logging
import re
import os
import math
import ast
import time
from morphenepythongraphenebase.py23 import bytes_types, integer_types, string_types, text_type
from datetime import datetime, timedelta, date
from morphenepythonapi.morphenenoderpc import MorpheneNodeRPC
from morphenepythonapi.exceptions import NoAccessApi, NoApiWithName
from morphenepythongraphenebase.account import PrivateKey, PublicKey
from morphenepythonbase import transactions, operations
from morphenepythongraphenebase.chains import known_chains
from .account import Account
from .amount import Amount
from .storage import configStorage as config
from .version import version as morphenepython_version
from .exceptions import (
    AccountExistsException,
    AccountDoesNotExistsException
)
from .wallet import Wallet
from .transactionbuilder import TransactionBuilder
from .utils import formatTime, remove_from_dict, addTzInfo, formatToTimeStamp
from morphenepython.constants import MORPHENE_100_PERCENT, MORPHENE_1_PERCENT, MORPHENE_RC_REGEN_TIME

log = logging.getLogger(__name__)


class MorpheneClient(object):
    """ Connect to the Morphene network.

        :param str node: Node to connect to *(optional)*
        :param str rpcuser: RPC user *(optional)*
        :param str rpcpassword: RPC password *(optional)*
        :param bool nobroadcast: Do **not** broadcast a transaction!
            *(optional)*
        :param bool unsigned: Do **not** sign a transaction! *(optional)*
        :param bool debug: Enable Debugging *(optional)*
        :param keys: Predefine the wif keys to shortcut the
            wallet database *(optional)*
        :type keys: array, dict, string
        :param wif: Predefine the wif keys to shortcut the
                wallet database *(optional)*
        :type wif: array, dict, string
        :param bool offline: Boolean to prevent connecting to network (defaults
            to ``False``) *(optional)*
        :param int expiration: Delay in seconds until transactions are supposed
            to expire *(optional)* (default is 30)
        :param str blocking: Wait for broadcasted transactions to be included
            in a block and return full transaction (can be "head" or
            "irreversible")
        :param bool bundle: Do not broadcast transactions right away, but allow
            to bundle operations. *(optional)*
        :param int num_retries: Set the maximum number of reconnects to the nodes before
            NumRetriesReached is raised. Disabled for -1. (default is -1)
        :param int num_retries_call: Repeat num_retries_call times a rpc call on node error (default is 5)
        :param int timeout: Timeout setting for https nodes (default is 60)
        :param dict custom_chains: custom chain which should be added to the known chains

        Three wallet operation modes are possible:

        * **Wallet Database**: Here, the morphenelibs load the keys from the
          locally stored wallet SQLite database (see ``storage.py``).
          To use this mode, simply call ``MorpheneClient()`` without the
          ``keys`` parameter
        * **Providing Keys**: Here, you can provide the keys for
          your accounts manually. All you need to do is add the wif
          keys for the accounts you want to use as a simple array
          using the ``keys`` parameter to ``MorpheneClient()``.
        * **Force keys**: This more is for advanced users and
          requires that you know what you are doing. Here, the
          ``keys`` parameter is a dictionary that overwrite the
          ``active``, ``owner``, ``posting`` or ``memo`` keys for
          any account. This mode is only used for *foreign*
          signatures!

        .. code-block:: python

            mph = MorpheneClient(<host>)

        where ``<host>`` starts with ``https://``, ``ws://`` or ``wss://``.

        The purpose of this class it to simplify interaction with the
        Morphene Blockchain.

        The idea is to have a class that allows to do this:

        .. code-block:: python

            >>> from morphenepython import MorpheneClient
            >>> mph = MorpheneClient()
            >>> print(mph.get_blockchain_version())  # doctest: +SKIP

        Example for adding a custom chain:

        .. code-block:: python

            from morphenepython import MorpheneClient
            stm = MorpheneClient(node=["https://mytstnet.com"], custom_chains={"MYTESTNET":
                {'chain_assets': [{'asset': 'MORPH', 'id': 1, 'precision': 3, 'symbol': 'MORPH'},
                                  {'asset': 'VESTS', 'id': 2, 'precision': 6, 'symbol': 'VESTS'}],
                 'chain_id': '79276aea5d4877d9a25892eaa01b0adf019d3e5cb12a97478df3298ccdd01674',
                 'min_version': '0.0.0',
                 'prefix': 'MPH'}
                }
            )

    """

    def __init__(self,
                 node="",
                 rpcuser=None,
                 rpcpassword=None,
                 debug=False,
                 data_refresh_time_seconds=900,
                 **kwargs):
        """Init MorpheneClient

            :param str node: Node to connect to *(optional)*
            :param str rpcuser: RPC user *(optional)*
            :param str rpcpassword: RPC password *(optional)*
            :param bool nobroadcast: Do **not** broadcast a transaction!
                *(optional)*
            :param bool unsigned: Do **not** sign a transaction! *(optional)*
            :param bool debug: Enable Debugging *(optional)*
            :param array,dict,string keys: Predefine the wif keys to shortcut the
                wallet database *(optional)*
            :param array,dict,string wif: Predefine the wif keys to shortcut the
                wallet database *(optional)*
            :param bool offline: Boolean to prevent connecting to network (defaults
                to ``False``) *(optional)*
            :param int expiration: Delay in seconds until transactions are supposed
                to expire *(optional)* (default is 30)
            :param str blocking: Wait for broadcast transactions to be included
                in a block and return full transaction (can be "head" or
                "irreversible")
            :param bool bundle: Do not broadcast transactions right away, but allow
                to bundle operations *(optional)*
            :param int num_retries: Set the maximum number of reconnects to the nodes before
                NumRetriesReached is raised. Disabled for -1. (default is -1)
            :param int num_retries_call: Repeat num_retries_call times a rpc call on node error (default is 5)
                :param int timeout: Timeout setting for https nodes (default is 60)

        """

        self.rpc = None
        self.debug = debug

        self.offline = bool(kwargs.get("offline", False))
        self.nobroadcast = bool(kwargs.get("nobroadcast", False))
        self.unsigned = bool(kwargs.get("unsigned", False))
        self.expiration = int(kwargs.get("expiration", 30))
        self.bundle = bool(kwargs.get("bundle", False))
        self.blocking = kwargs.get("blocking", False)
        self.custom_chains = kwargs.get("custom_chains", {})

        # Store config for access through other Classes
        self.config = config

        if not self.offline:
            self.connect(node=node,
                         rpcuser=rpcuser,
                         rpcpassword=rpcpassword,
                         **kwargs)

        self.data = {'last_refresh': None, 'last_node': None, 'dynamic_global_properties': None,
                     'hardfork_properties': None, 'network': None, 'witness_schedule': None, 'config': None}
        self.data_refresh_time_seconds = data_refresh_time_seconds
        # self.refresh_data()

        # txbuffers/propbuffer are initialized and cleared
        self.clear()

        self.wallet = Wallet(morphene_instance=self, **kwargs)

    # -------------------------------------------------------------------------
    # Basic Calls
    # -------------------------------------------------------------------------
    def connect(self,
                node="",
                rpcuser="",
                rpcpassword="",
                **kwargs):
        """ Connect to Morphene network (internal use only)
        """
        if not node:
            node = self.get_default_nodes()
            if not bool(node):
                raise ValueError("A Morphene node needs to be provided!")

        if not rpcuser and "rpcuser" in config:
            rpcuser = config["rpcuser"]

        if not rpcpassword and "rpcpassword" in config:
            rpcpassword = config["rpcpassword"]

        self.rpc = MorpheneNodeRPC(node, rpcuser, rpcpassword, **kwargs)

    def is_connected(self):
        """Returns if rpc is connected"""
        return self.rpc is not None

    def __repr__(self):
        if self.offline:
            return "<%s offline=True>" % (
                self.__class__.__name__)
        elif self.rpc is not None and len(self.rpc.url) > 0:
            return "<%s node=%s, nobroadcast=%s>" % (
                self.__class__.__name__, str(self.rpc.url), str(self.nobroadcast))
        else:
            return "<%s, nobroadcast=%s>" % (
                self.__class__.__name__, str(self.nobroadcast))

    def refresh_data(self, force_refresh=False, data_refresh_time_seconds=None):
        """ Read and stores Morphene Blockchain parameters
            If the last data refresh is older than data_refresh_time_seconds, data will be refreshed

            :param bool force_refresh: if True, a refresh of the data is enforced
            :param float data_refresh_time_seconds: set a new minimal refresh time in seconds

        """
        if self.offline:
            return
        if data_refresh_time_seconds is not None:
            self.data_refresh_time_seconds = data_refresh_time_seconds
        if self.data['last_refresh'] is not None and not force_refresh and self.data["last_node"] == self.rpc.url:
            if (datetime.utcnow() - self.data['last_refresh']).total_seconds() < self.data_refresh_time_seconds:
                return
        self.data['last_refresh'] = datetime.utcnow()
        self.data["last_node"] = self.rpc.url
        self.data["dynamic_global_properties"] = self.get_dynamic_global_properties(False)
        try:
            self.data['hardfork_properties'] = self.get_hardfork_properties(False)
        except:
            self.data['hardfork_properties'] = None
        self.data['network'] = self.get_network(False)
        self.data['witness_schedule'] = self.get_witness_schedule(False)
        self.data['config'] = self.get_config(False)

    def get_dynamic_global_properties(self, use_stored_data=True):
        """ This call returns the *dynamic global properties*

            :param bool use_stored_data: if True, stored data will be returned. If stored data are
                empty or old, refresh_data() is used.

        """
        if use_stored_data:
            self.refresh_data()
            return self.data['dynamic_global_properties']
        if self.rpc is None:
            return None
        self.rpc.set_next_node_on_empty_reply(True)
        return self.rpc.get_dynamic_global_properties(api="database")

    def get_reserve_ratio(self):
        """ This call returns the *reserve ratio*
        """
        if self.rpc is None:
            return None
        self.rpc.set_next_node_on_empty_reply(True)
        props = self.get_dynamic_global_properties()
        # conf = self.get_config()
        reserve_ratio = {'id': 0, 'average_block_size': props['average_block_size'],
                         'current_reserve_ratio': props['current_reserve_ratio'],
                         'max_virtual_bandwidth': props['max_virtual_bandwidth']}
        return reserve_ratio

    def get_hardfork_properties(self, use_stored_data=True):
        """ Returns Hardfork and live_time of the hardfork

            :param bool use_stored_data: if True, stored data will be returned. If stored data are
                                         empty or old, refresh_data() is used.
        """
        if use_stored_data:
            self.refresh_data()
            return self.data['hardfork_properties']
        if self.rpc is None:
            return None
        ret = None
        self.rpc.set_next_node_on_empty_reply(True)
        ret = self.rpc.get_next_scheduled_hardfork(api="database")

        return ret

    def get_network(self, use_stored_data=True):
        """ Identify the network

            :param bool use_stored_data: if True, stored data will be returned. If stored data are
                                         empty or old, refresh_data() is used.

            :returns: Network parameters
            :rtype: dictionary
        """
        if use_stored_data:
            self.refresh_data()
            return self.data['network']

        if self.rpc is None:
            return None
        try:
            return self.rpc.get_network()
        except:
            return known_chains["MORPHENE"]

    def get_block_interval(self, use_stored_data=True):
        """Returns the block interval in seconds"""
        props = self.get_config(use_stored_data=use_stored_data)
        block_interval = 3
        if props is None:
            return block_interval
        for key in props:
            if key[-14:] == "BLOCK_INTERVAL":
                block_interval = props[key]

        return block_interval

    def get_blockchain_version(self, use_stored_data=True):
        """Returns the blockchain version"""
        props = self.get_config(use_stored_data=use_stored_data)
        blockchain_version = '0.0.0'
        if props is None:
            return blockchain_version
        for key in props:
            if key[-18:] == "BLOCKCHAIN_VERSION":
                blockchain_version = props[key]
        return blockchain_version

    def get_resource_params(self):
        """Returns the resource parameter"""
        return self.rpc.get_resource_params(api="rc")["resource_params"]

    def get_resource_pool(self):
        """Returns the resource pool"""
        return self.rpc.get_resource_pool(api="rc")["resource_pool"]

    def get_rc_cost(self, resource_count):
        """Returns the RC costs based on the resource_count"""
        pools = self.get_resource_pool()
        params = self.get_resource_params()
        config = self.get_config()
        dyn_param = self.get_dynamic_global_properties()
        rc_regen = int(Amount(dyn_param["total_vesting_shares"], morphene_instance=self)) / (MORPHENE_RC_REGEN_TIME / config["MORPHENE_BLOCK_INTERVAL"])
        total_cost = 0
        if rc_regen == 0:
            return total_cost
        for resource_type in resource_count:
            curve_params = params[resource_type]["price_curve_params"]
            current_pool = int(pools[resource_type]["pool"])
            count = resource_count[resource_type]
            count *= params[resource_type]["resource_dynamics_params"]["resource_unit"]
            cost = self._compute_rc_cost(curve_params, current_pool, count, rc_regen)
            total_cost += cost
        return total_cost

    def _compute_rc_cost(self, curve_params, current_pool, resource_count, rc_regen):
        """Helper function for computing the RC costs"""
        num = int(rc_regen)
        num *= int(curve_params['coeff_a'])
        num = int(num) >> int(curve_params['shift'])
        num += 1
        num *= int(resource_count)
        denom = int(curve_params['coeff_b'])
        if int(current_pool) > 0:
            denom += int(current_pool)
        num_denom = num / denom
        return int(num_denom) + 1

    def get_morph_per_mvest(self, time_stamp=None, use_stored_data=True):
        """ Returns the MVEST to MORPH ratio

            :param int time_stamp: (optional) if set, return an estimated
                MORPH per MVEST ratio for the given time stamp. If unset the
                current ratio is returned (default). (can also be a datetime object)
        """
        if self.offline and time_stamp is None:
            time_stamp =datetime.utcnow()

        if time_stamp is not None:
            if isinstance(time_stamp, (datetime, date)):
                time_stamp = formatToTimeStamp(time_stamp)
            a = 2.1325476281078992e-05
            b = -31099.685481490847
            a2 = 2.9019227739473682e-07
            b2 = 48.41432402074669

            if (time_stamp < (b2 - b) / (a - a2)):
                return a * time_stamp + b
            else:
                return a2 * time_stamp + b2
        global_properties = self.get_dynamic_global_properties(use_stored_data=use_stored_data)

        return (
            float(Amount(global_properties['total_vesting_fund_morph'], morphene_instance=self)) /
            (float(Amount(global_properties['total_vesting_shares'], morphene_instance=self)) / 1e6)
        )

    def get_chain_properties(self, use_stored_data=True):
        """ Return witness elected chain properties

            Properties:::

                {
                    'account_creation_fee': '30.000 MORPH',
                    'maximum_block_size': 65536
                }

        """
        if use_stored_data:
            self.refresh_data()
            return self.data['witness_schedule']['median_props']
        else:
            return self.get_witness_schedule(use_stored_data)['median_props']

    def get_witness_schedule(self, use_stored_data=True):
        """ Return witness elected chain properties

        """
        if use_stored_data:
            self.refresh_data()
            return self.data['witness_schedule']

        if self.rpc is None:
            return None
        self.rpc.set_next_node_on_empty_reply(True)
        return self.rpc.get_witness_schedule(api="database")

    def get_config(self, use_stored_data=True):
        """ Returns internal chain configuration.

            :param bool use_stored_data: If True, the cached value is returned
        """
        if use_stored_data:
            self.refresh_data()
            config = self.data['config']
        else:
            if self.rpc is None:
                return None
            self.rpc.set_next_node_on_empty_reply(True)
            config = self.rpc.get_config(api="database")
        return config

    @property
    def chain_params(self):
        if self.offline or self.rpc is None:
            return known_chains["MORPHENE"]
        else:
            return self.get_network()

    @property
    def hardfork(self):
        if self.offline or self.rpc is None:
            versions = known_chains['MORPHENE']['min_version']
        else:
            hf_prop = self.get_hardfork_properties()
            if "current_hardfork_version" in hf_prop:
                versions = hf_prop["current_hardfork_version"]
            else:
                versions = self.get_blockchain_version()
        return int(versions.split('.')[1])

    @property
    def prefix(self):
        return self.chain_params["prefix"]

    def set_default_account(self, account):
        """ Set the default account to be used
        """
        Account(account, morphene_instance=self)
        config["default_account"] = account

    def set_password_storage(self, password_storage):
        """ Set the password storage mode.

            When set to "no", the password has to be provided each time.
            When set to "environment" the password is taken from the
            UNLOCK variable

            When set to "keyring" the password is taken from the
            python keyring module. A wallet password can be stored with
            python -m keyring set morphene wallet password

            :param str password_storage: can be "no",
                "keyring" or "environment"

        """
        config["password_storage"] = password_storage

    def set_default_nodes(self, nodes):
        """ Set the default nodes to be used
        """
        if bool(nodes):
            if isinstance(nodes, list):
                nodes = str(nodes)
            config["node"] = nodes
        else:
            config.delete("node")

    def get_default_nodes(self):
        """Returns the default nodes"""
        if "node" in config:
            nodes = config["node"]
        elif "nodes" in config:
            nodes = config["nodes"]
        elif "default_nodes" in config and bool(config["default_nodes"]):
            nodes = config["default_nodes"]
        else:
            nodes = []
        if isinstance(nodes, str) and nodes[0] == '[' and nodes[-1] == ']':
            nodes = ast.literal_eval(nodes)
        return nodes

    def move_current_node_to_front(self):
        """Returns the default node list, until the first entry
            is equal to the current working node url
        """
        node = self.get_default_nodes()
        if len(node) < 2:
            return
        offline = self.offline
        while not offline and node[0] != self.rpc.url and len(node) > 1:
            node = node[1:] + [node[0]]
        self.set_default_nodes(node)

    def finalizeOp(self, ops, account, permission, **kwargs):
        """ This method obtains the required private keys if present in
            the wallet, finalizes the transaction, signs it and
            broadacasts it

            :param ops: The operation (or list of operations) to
                broadcast
            :type ops: list, GrapheneObject
            :param Account account: The account that authorizes the
                operation
            :param string permission: The required permission for
                signing (active, owner, posting)
            :param TransactionBuilder append_to: This allows to provide an instance of
                TransactionBuilder (see :func:`MorpheneClient.new_tx()`) to specify
                where to put a specific operation.

            .. note:: ``append_to`` is exposed to every method used in the
                Morphene class

            .. note::   If ``ops`` is a list of operation, they all need to be
                        signable by the same key! Thus, you cannot combine ops
                        that require active permission with ops that require
                        posting permission. Neither can you use different
                        accounts for different operations!

            .. note:: This uses :func:`MorpheneClient.txbuffer` as instance of
                :class:`morphenepython.transactionbuilder.TransactionBuilder`.
                You may want to use your own txbuffer
        """
        if self.offline:
                return {}
        if "append_to" in kwargs and kwargs["append_to"]:

            # Append to the append_to and return
            append_to = kwargs["append_to"]
            parent = append_to.get_parent()
            if not isinstance(append_to, (TransactionBuilder)):
                raise AssertionError()
            append_to.appendOps(ops)
            # Add the signer to the buffer so we sign the tx properly
            parent.appendSigner(account, permission)
            # This returns as we used append_to, it does NOT broadcast, or sign
            return append_to.get_parent()
            # Go forward to see what the other options do ...
        else:
            # Append to the default buffer
            self.txbuffer.appendOps(ops)

        # Add signing information, signer, sign and optionally broadcast
        if self.unsigned:
            # In case we don't want to sign anything
            self.txbuffer.addSigningInformation(account, permission)
            return self.txbuffer
        elif self.bundle:
            # In case we want to add more ops to the tx (bundle)
            self.txbuffer.appendSigner(account, permission)
            return self.txbuffer.json()
        else:
            # default behavior: sign + broadcast
            self.txbuffer.appendSigner(account, permission)
            self.txbuffer.sign()
            return self.txbuffer.broadcast()

    def sign(self, tx=None, wifs=[], reconstruct_tx=True):
        """ Sign a provided transaction with the provided key(s)

            :param dict tx: The transaction to be signed and returned
            :param string wifs: One or many wif keys to use for signing
                a transaction. If not present, the keys will be loaded
                from the wallet as defined in "missing_signatures" key
                of the transactions.
            :param bool reconstruct_tx: when set to False and tx
                is already contructed, it will not reconstructed
                and already added signatures remain

        """
        if tx:
            txbuffer = TransactionBuilder(tx, morphene_instance=self)
        else:
            txbuffer = self.txbuffer
        txbuffer.appendWif(wifs)
        txbuffer.appendMissingSignatures()
        txbuffer.sign(reconstruct_tx=reconstruct_tx)
        return txbuffer.json()

    def broadcast(self, tx=None):
        """ Broadcast a transaction to the Morphene network

            :param tx tx: Signed transaction to broadcast

        """
        if tx:
            # If tx is provided, we broadcast the tx
            return TransactionBuilder(tx, morphene_instance=self).broadcast()
        else:
            return self.txbuffer.broadcast()

    def info(self, use_stored_data=True):
        """ Returns the global properties
        """
        return self.get_dynamic_global_properties(use_stored_data=use_stored_data)

    # -------------------------------------------------------------------------
    # Wallet stuff
    # -------------------------------------------------------------------------
    def newWallet(self, pwd):
        """ Create a new wallet. This method is basically only calls
            :func:`morphenepython.wallet.Wallet.create`.

            :param str pwd: Password to use for the new wallet

            :raises WalletExists: if there is already a
                wallet created

        """
        return self.wallet.create(pwd)

    def unlock(self, *args, **kwargs):
        """ Unlock the internal wallet
        """
        return self.wallet.unlock(*args, **kwargs)

    # -------------------------------------------------------------------------
    # Transaction Buffers
    # -------------------------------------------------------------------------
    @property
    def txbuffer(self):
        """ Returns the currently active tx buffer
        """
        return self.tx()

    def tx(self):
        """ Returns the default transaction buffer
        """
        return self._txbuffers[0]

    def new_tx(self, *args, **kwargs):
        """ Let's obtain a new txbuffer

            :returns: id of the new txbuffer
            :rtype: int
        """
        builder = TransactionBuilder(
            *args,
            morphene_instance=self,
            **kwargs
        )
        self._txbuffers.append(builder)
        return builder

    def clear(self):
        self._txbuffers = []
        # Base/Default proposal/tx buffers
        self.new_tx()
        # self.new_proposal()

    # -------------------------------------------------------------------------
    # Account related calls
    # -------------------------------------------------------------------------
    def claim_account(self, creator, fee=None, **kwargs):
        """ Claim account for claimed account creation.

            When fee is 0 MORPH a subsidized account is claimed and can be created
            later with create_claimed_account.
            The number of subsidized account is limited.

            :param str creator: which account should pay the registration fee (RC or MORPH)
                    (defaults to ``default_account``)
            :param str fee: when set to 0 MORPH (default), claim account is paid by RC
        """
        fee = fee if fee is not None else "0 %s" % (self.morphene_symbol)
        if not creator and config["default_account"]:
            creator = config["default_account"]
        if not creator:
            raise ValueError(
                "Not creator account given. Define it with " +
                "creator=x, or set the default_account using morphenepy")
        creator = Account(creator, morphene_instance=self)
        op = {
            "fee": Amount(fee, morphene_instance=self),
            "creator": creator["name"],
            "prefix": self.prefix,
        }
        op = operations.Claim_account(**op)
        return self.finalizeOp(op, creator, "active", **kwargs)

    def create_claimed_account(
        self,
        account_name,
        creator=None,
        owner_key=None,
        active_key=None,
        memo_key=None,
        posting_key=None,
        password=None,
        additional_owner_keys=[],
        additional_active_keys=[],
        additional_posting_keys=[],
        additional_owner_accounts=[],
        additional_active_accounts=[],
        additional_posting_accounts=[],
        storekeys=True,
        store_owner_key=False,
        json_meta=None,
        combine_with_claim_account=False,
        fee=None,
        **kwargs
    ):
        """ Create new claimed account on Morphene

            The brainkey/password can be used to recover all generated keys
            (see :class:`morphenepythongraphenebase.account` for more details.

            By default, this call will use ``default_account`` to
            register a new name ``account_name`` with all keys being
            derived from a new brain key that will be returned. The
            corresponding keys will automatically be installed in the
            wallet.

            .. warning:: Don't call this method unless you know what
                          you are doing! Be sure to understand what this
                          method does and where to find the private keys
                          for your account.

            .. note:: Please note that this imports private keys
                      (if password is present) into the wallet by
                      default when nobroadcast is set to False.
                      However, it **does not import the owner
                      key** for security reasons by default.
                      If you set store_owner_key to True, the
                      owner key is stored.
                      Do NOT expect to be able to recover it from
                      the wallet if you lose your password!

            .. note:: Account creations cost a fee that is defined by
                       the network. If you create an account, you will
                       need to pay for that fee!

            :param str account_name: (**required**) new account name
            :param str json_meta: Optional meta data for the account
            :param str owner_key: Main owner key
            :param str active_key: Main active key
            :param str posting_key: Main posting key
            :param str memo_key: Main memo_key
            :param str password: Alternatively to providing keys, one
                                 can provide a password from which the
                                 keys will be derived
            :param array additional_owner_keys:  Additional owner public keys
            :param array additional_active_keys: Additional active public keys
            :param array additional_posting_keys: Additional posting public keys
            :param array additional_owner_accounts: Additional owner account
                names
            :param array additional_active_accounts: Additional acctive account
                names
            :param bool storekeys: Store new keys in the wallet (default:
                ``True``)
            :param bool combine_with_claim_account: When set to True, a
                claim_account operation is additionally broadcasted
            :param str fee: When combine_with_claim_account is set to True,
                this parameter is used for the claim_account operation

            :param str creator: which account should pay the registration fee
                                (defaults to ``default_account``)
            :raises AccountExistsException: if the account already exists on
                the blockchain

        """
        fee = fee if fee is not None else "0 %s" % (self.morphene_symbol)
        if not creator and config["default_account"]:
            creator = config["default_account"]
        if not creator:
            raise ValueError(
                "Not creator account given. Define it with " +
                "creator=x, or set the default_account using morphenepy")
        if password and (owner_key or active_key or memo_key):
            raise ValueError(
                "You cannot use 'password' AND provide keys!"
            )

        try:
            Account(account_name, morphene_instance=self)
            raise AccountExistsException
        except AccountDoesNotExistsException:
            pass

        creator = Account(creator, morphene_instance=self)

        " Generate new keys from password"
        from morphenepythongraphenebase.account import PasswordKey
        if password:
            active_key = PasswordKey(account_name, password, role="active", prefix=self.prefix)
            owner_key = PasswordKey(account_name, password, role="owner", prefix=self.prefix)
            posting_key = PasswordKey(account_name, password, role="posting", prefix=self.prefix)
            memo_key = PasswordKey(account_name, password, role="memo", prefix=self.prefix)
            active_pubkey = active_key.get_public_key()
            owner_pubkey = owner_key.get_public_key()
            posting_pubkey = posting_key.get_public_key()
            memo_pubkey = memo_key.get_public_key()
            active_privkey = active_key.get_private_key()
            posting_privkey = posting_key.get_private_key()
            owner_privkey = owner_key.get_private_key()
            memo_privkey = memo_key.get_private_key()
            # store private keys
            try:
                if storekeys and not self.nobroadcast:
                    if store_owner_key:
                        self.wallet.addPrivateKey(str(owner_privkey))
                    self.wallet.addPrivateKey(str(active_privkey))
                    self.wallet.addPrivateKey(str(memo_privkey))
                    self.wallet.addPrivateKey(str(posting_privkey))
            except ValueError as e:
                log.info(str(e))

        elif (owner_key and active_key and memo_key and posting_key):
            active_pubkey = PublicKey(
                active_key, prefix=self.prefix)
            owner_pubkey = PublicKey(
                owner_key, prefix=self.prefix)
            posting_pubkey = PublicKey(
                posting_key, prefix=self.prefix)
            memo_pubkey = PublicKey(
                memo_key, prefix=self.prefix)
        else:
            raise ValueError(
                "Call incomplete! Provide either a password or public keys!"
            )
        owner = format(owner_pubkey, self.prefix)
        active = format(active_pubkey, self.prefix)
        posting = format(posting_pubkey, self.prefix)
        memo = format(memo_pubkey, self.prefix)

        owner_key_authority = [[owner, 1]]
        active_key_authority = [[active, 1]]
        posting_key_authority = [[posting, 1]]
        owner_accounts_authority = []
        active_accounts_authority = []
        posting_accounts_authority = []

        # additional authorities
        for k in additional_owner_keys:
            owner_key_authority.append([k, 1])
        for k in additional_active_keys:
            active_key_authority.append([k, 1])
        for k in additional_posting_keys:
            posting_key_authority.append([k, 1])

        for k in additional_owner_accounts:
            addaccount = Account(k, morphene_instance=self)
            owner_accounts_authority.append([addaccount["name"], 1])
        for k in additional_active_accounts:
            addaccount = Account(k, morphene_instance=self)
            active_accounts_authority.append([addaccount["name"], 1])
        for k in additional_posting_accounts:
            addaccount = Account(k, morphene_instance=self)
            posting_accounts_authority.append([addaccount["name"], 1])
        if combine_with_claim_account:
            op = {
                "fee": Amount(fee, morphene_instance=self),
                "creator": creator["name"],
                "prefix": self.prefix,
            }
            op = operations.Claim_account(**op)
            ops = [op]
        op = {
            "creator": creator["name"],
            "new_account_name": account_name,
            'owner': {'account_auths': owner_accounts_authority,
                      'key_auths': owner_key_authority,
                      "address_auths": [],
                      'weight_threshold': 1},
            'active': {'account_auths': active_accounts_authority,
                       'key_auths': active_key_authority,
                       "address_auths": [],
                       'weight_threshold': 1},
            'posting': {'account_auths': active_accounts_authority,
                        'key_auths': posting_key_authority,
                        "address_auths": [],
                        'weight_threshold': 1},
            'memo_key': memo,
            "json_metadata": json_meta or {},
            "prefix": self.prefix,
        }
        op = operations.Create_claimed_account(**op)
        if combine_with_claim_account:
            ops.append(op)
            return self.finalizeOp(ops, creator, "active", **kwargs)
        else:
            return self.finalizeOp(op, creator, "active", **kwargs)

    def create_account(
        self,
        account_name,
        creator=None,
        owner_key=None,
        active_key=None,
        memo_key=None,
        posting_key=None,
        password=None,
        additional_owner_keys=[],
        additional_active_keys=[],
        additional_posting_keys=[],
        additional_owner_accounts=[],
        additional_active_accounts=[],
        additional_posting_accounts=[],
        storekeys=True,
        store_owner_key=False,
        json_meta=None,
        **kwargs
    ):
        """ Create new account on Morphene

            The brainkey/password can be used to recover all generated keys
            (see :class:`morphenepythongraphenebase.account` for more details.

            By default, this call will use ``default_account`` to
            register a new name ``account_name`` with all keys being
            derived from a new brain key that will be returned. The
            corresponding keys will automatically be installed in the
            wallet.

            .. warning:: Don't call this method unless you know what
                          you are doing! Be sure to understand what this
                          method does and where to find the private keys
                          for your account.

            .. note:: Please note that this imports private keys
                      (if password is present) into the wallet by
                      default when nobroadcast is set to False.
                      However, it **does not import the owner
                      key** for security reasons by default.
                      If you set store_owner_key to True, the
                      owner key is stored.
                      Do NOT expect to be able to recover it from
                      the wallet if you lose your password!

            .. note:: Account creations cost a fee that is defined by
                       the network. If you create an account, you will
                       need to pay for that fee!

            :param str account_name: (**required**) new account name
            :param str json_meta: Optional meta data for the account
            :param str owner_key: Main owner key
            :param str active_key: Main active key
            :param str posting_key: Main posting key
            :param str memo_key: Main memo_key
            :param str password: Alternatively to providing keys, one
                                 can provide a password from which the
                                 keys will be derived
            :param array additional_owner_keys:  Additional owner public keys
            :param array additional_active_keys: Additional active public keys
            :param array additional_posting_keys: Additional posting public keys
            :param array additional_owner_accounts: Additional owner account
                names
            :param array additional_active_accounts: Additional acctive account
                names
            :param bool storekeys: Store new keys in the wallet (default:
                ``True``)

            :param str creator: which account should pay the registration fee
                                (defaults to ``default_account``)
            :raises AccountExistsException: if the account already exists on
                the blockchain

        """
        if not creator and config["default_account"]:
            creator = config["default_account"]
        if not creator:
            raise ValueError(
                "Not creator account given. Define it with " +
                "creator=x, or set the default_account using morphenepy")
        if password and (owner_key or active_key or memo_key):
            raise ValueError(
                "You cannot use 'password' AND provide keys!"
            )

        try:
            Account(account_name, morphene_instance=self)
            raise AccountExistsException
        except AccountDoesNotExistsException:
            pass

        creator = Account(creator, morphene_instance=self)

        " Generate new keys from password"
        from morphenepythongraphenebase.account import PasswordKey
        if password:
            active_key = PasswordKey(account_name, password, role="active", prefix=self.prefix)
            owner_key = PasswordKey(account_name, password, role="owner", prefix=self.prefix)
            posting_key = PasswordKey(account_name, password, role="posting", prefix=self.prefix)
            memo_key = PasswordKey(account_name, password, role="memo", prefix=self.prefix)
            active_pubkey = active_key.get_public_key()
            owner_pubkey = owner_key.get_public_key()
            posting_pubkey = posting_key.get_public_key()
            memo_pubkey = memo_key.get_public_key()
            active_privkey = active_key.get_private_key()
            posting_privkey = posting_key.get_private_key()
            owner_privkey = owner_key.get_private_key()
            memo_privkey = memo_key.get_private_key()
            # store private keys
            try:
                if storekeys and not self.nobroadcast:
                    if store_owner_key:
                        self.wallet.addPrivateKey(str(owner_privkey))
                    self.wallet.addPrivateKey(str(active_privkey))
                    self.wallet.addPrivateKey(str(memo_privkey))
                    self.wallet.addPrivateKey(str(posting_privkey))
            except ValueError as e:
                log.info(str(e))

        elif (owner_key and active_key and memo_key and posting_key):
            active_pubkey = PublicKey(
                active_key, prefix=self.prefix)
            owner_pubkey = PublicKey(
                owner_key, prefix=self.prefix)
            posting_pubkey = PublicKey(
                posting_key, prefix=self.prefix)
            memo_pubkey = PublicKey(
                memo_key, prefix=self.prefix)
        else:
            raise ValueError(
                "Call incomplete! Provide either a password or public keys!"
            )
        owner = format(owner_pubkey, self.prefix)
        active = format(active_pubkey, self.prefix)
        posting = format(posting_pubkey, self.prefix)
        memo = format(memo_pubkey, self.prefix)

        owner_key_authority = [[owner, 1]]
        active_key_authority = [[active, 1]]
        posting_key_authority = [[posting, 1]]
        owner_accounts_authority = []
        active_accounts_authority = []
        posting_accounts_authority = []

        # additional authorities
        for k in additional_owner_keys:
            owner_key_authority.append([k, 1])
        for k in additional_active_keys:
            active_key_authority.append([k, 1])
        for k in additional_posting_keys:
            posting_key_authority.append([k, 1])

        for k in additional_owner_accounts:
            addaccount = Account(k, morphene_instance=self)
            owner_accounts_authority.append([addaccount["name"], 1])
        for k in additional_active_accounts:
            addaccount = Account(k, morphene_instance=self)
            active_accounts_authority.append([addaccount["name"], 1])
        for k in additional_posting_accounts:
            addaccount = Account(k, morphene_instance=self)
            posting_accounts_authority.append([addaccount["name"], 1])

        props = self.get_chain_properties()
        if self.hardfork >= 20:
            required_fee_morph = Amount(props["account_creation_fee"], morphene_instance=self)
        else:
            required_fee_morph = Amount(props["account_creation_fee"], morphene_instance=self) * 30
        op = {
            "fee": required_fee_morph,
            "creator": creator["name"],
            "new_account_name": account_name,
            'owner': {'account_auths': owner_accounts_authority,
                      'key_auths': owner_key_authority,
                      "address_auths": [],
                      'weight_threshold': 1},
            'active': {'account_auths': active_accounts_authority,
                       'key_auths': active_key_authority,
                       "address_auths": [],
                       'weight_threshold': 1},
            'posting': {'account_auths': posting_accounts_authority,
                        'key_auths': posting_key_authority,
                        "address_auths": [],
                        'weight_threshold': 1},
            'memo_key': memo,
            "json_metadata": json_meta or {},
            "prefix": self.prefix,
        }
        op = operations.Account_create(**op)
        return self.finalizeOp(op, creator, "active", **kwargs)

    def witness_set_properties(self, wif, owner, props):
        """ Set witness properties

            :param str wif: Private signing key
            :param dict props: Properties
            :param str owner: witness account name

            Properties:::

                {
                    "account_creation_fee": x,
                    "account_subsidy_budget": x,
                    "account_subsidy_decay": x,
                    "maximum_block_size": x,
                    "url": x,
                    "new_signing_key": x
                }

        """

        owner = Account(owner, morphene_instance=self)

        try:
            PrivateKey(wif, prefix=self.prefix)
        except Exception as e:
            raise e
        props_list = [["key", repr(PrivateKey(wif, prefix=self.prefix).pubkey)]]
        for k in props:
            props_list.append([k, props[k]])

        op = operations.Witness_set_properties({"owner": owner["name"], "props": props_list, "prefix": self.prefix})
        tb = TransactionBuilder(morphene_instance=self)
        tb.appendOps([op])
        tb.appendWif(wif)
        tb.sign()
        return tb.broadcast()

    def witness_update(self, signing_key, url, props, account=None, **kwargs):
        """ Creates/updates a witness

            :param str signing_key: Public signing key
            :param str url: URL
            :param dict props: Properties
            :param str account: (optional) witness account name

            Properties:::

                {
                    "account_creation_fee": "3.000 MORPH",
                    "maximum_block_size": 65536,
                }

        """
        if not account and config["default_account"]:
            account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")

        account = Account(account, morphene_instance=self)

        try:
            PublicKey(signing_key, prefix=self.prefix)
        except Exception as e:
            raise e
        if "account_creation_fee" in props:
            props["account_creation_fee"] = Amount(props["account_creation_fee"], morphene_instance=self)
        op = operations.Witness_update(
            **{
                "owner": account["name"],
                "url": url,
                "block_signing_key": signing_key,
                "props": props,
                "fee": Amount(0, self.morphene_symbol, morphene_instance=self),
                "prefix": self.prefix,
            })
        return self.finalizeOp(op, account, "active", **kwargs)

    def _test_weights_treshold(self, authority):
        """ This method raises an error if the threshold of an authority cannot
            be reached by the weights.

            :param dict authority: An authority of an account
            :raises ValueError: if the threshold is set too high
        """
        weights = 0
        for a in authority["account_auths"]:
            weights += int(a[1])
        for a in authority["key_auths"]:
            weights += int(a[1])
        if authority["weight_threshold"] > weights:
            raise ValueError("Threshold too restrictive!")
        if authority["weight_threshold"] == 0:
            raise ValueError("Cannot have threshold of 0")

    def get_api_methods(self):
        """Returns all supported api methods"""
        return self.rpc.get_methods(api="jsonrpc")

    def get_apis(self):
        """Returns all enabled apis"""
        api_methods = self.get_api_methods()
        api_list = []
        for a in api_methods:
            api = a.split(".")[0]
            if api not in api_list:
                api_list.append(api)
        return api_list

    def _get_asset_symbol(self, asset_id):
        """ get the asset symbol from an asset id

            :@param int asset_id: 0 -> MORPH, 2 -> VESTS

        """
        for asset in self.chain_params['chain_assets']:
            if asset['id'] == asset_id:
                return asset['symbol']

        raise KeyError("asset ID not found in chain assets")

    @property
    def morph_symbol(self):
        """ get the current chains symbol for MORPH (e.g. "TESTS" on testnet) """
        return self._get_asset_symbol(1)

    @property
    def vests_symbol(self):
        """ get the current chains symbol for VESTS """
        return self._get_asset_symbol(2)
