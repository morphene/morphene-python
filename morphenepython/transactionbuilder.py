# This Python file uses the following encoding: utf-8
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import str
from future.utils import python_2_unicode_compatible
import logging
from morphenepythongraphenebase.py23 import bytes_types, integer_types, string_types, text_type
from .account import Account
from .utils import formatTimeFromNow
from morphenepythonbase.objects import Operation
from morphenepythongraphenebase.account import PrivateKey, PublicKey
from morphenepythonbase.signedtransactions import Signed_Transaction
from morphenepythonbase import transactions, operations
from .exceptions import (
    InsufficientAuthorityError,
    MissingKeyError,
    InvalidWifError,
    WalletLocked,
    OfflineHasNoRPCException
)
from morphenepython.instance import shared_morphene_instance
log = logging.getLogger(__name__)


@python_2_unicode_compatible
class TransactionBuilder(dict):
    """ This class simplifies the creation of transactions by adding
        operations and signers.
        To build your own transactions and sign them

        :param dict tx: transaction (Optional). If not set, the new transaction is created.
        :param int expiration: Delay in seconds until transactions are supposed
            to expire *(optional)* (default is 30)
        :param MorpheneClient morphene_instance: If not set, shared_morphene_instance() is used

        .. testcode::

           from morphenepython.transactionbuilder import TransactionBuilder
           from morphenepythonbase.operations import Transfer
           from morphenepython import MorpheneClient
           wif = "5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"
           stm = MorpheneClient(nobroadcast=True, keys={'active': wif})
           tx = TransactionBuilder(morphene_instance=stm)
           transfer = {"from": "test", "to": "test1", "amount": "1 STEEM", "memo": ""}
           tx.appendOps(Transfer(transfer))
           tx.appendSigner("test", "active") # or tx.appendWif(wif)
           signed_tx = tx.sign()
           broadcast_tx = tx.broadcast()

    """
    def __init__(
        self,
        tx={},
        morphene_instance=None,
        **kwargs
    ):
        self.morphene = morphene_instance or shared_morphene_instance()
        self.clear()
        if tx and isinstance(tx, dict):
            super(TransactionBuilder, self).__init__(tx)
            # Load operations
            self.ops = tx["operations"]
            self._require_reconstruction = False
        else:
            self._require_reconstruction = True
        self.set_expiration(kwargs.get("expiration", self.morphene.expiration))

    def set_expiration(self, p):
        """Set expiration date"""
        self.expiration = p

    def is_empty(self):
        """Check if ops is empty"""
        return not (len(self.ops) > 0)

    def list_operations(self):
        """List all ops"""
        return [Operation(o, prefix=self.morphene.prefix) for o in self.ops]

    def _is_signed(self):
        """Check if signatures exists"""
        return "signatures" in self and bool(self["signatures"])

    def _is_constructed(self):
        """Check if tx is already constructed"""
        return "expiration" in self and bool(self["expiration"])

    def _is_require_reconstruction(self):
        return self._require_reconstruction

    def _set_require_reconstruction(self):
        self._require_reconstruction = True

    def _unset_require_reconstruction(self):
        self._require_reconstruction = False

    def __repr__(self):
        return str(self)

    def __str__(self):
        return str(self.json())

    def __getitem__(self, key):
        if key not in self:
            self.constructTx()
        return dict(self).__getitem__(key)

    def get_parent(self):
        """ TransactionBuilders don't have parents, they are their own parent
        """
        return self

    def json(self, with_prefix=False):
        """ Show the transaction as plain json
        """
        if not self._is_constructed() or self._is_require_reconstruction():
            self.constructTx()
        json_dict = dict(self)
        if with_prefix:
            json_dict["prefix"] = self.morphene.prefix
        return json_dict

    def appendOps(self, ops, append_to=None):
        """ Append op(s) to the transaction builder

            :param list ops: One or a list of operations
        """
        if isinstance(ops, list):
            self.ops.extend(ops)
        else:
            self.ops.append(ops)
        self._set_require_reconstruction()

    def appendSigner(self, account, permission):
        """ Try to obtain the wif key from the wallet by telling which account
            and permission is supposed to sign the transaction
            It is possible to add more than one signer.
        """
        if not self.morphene.is_connected():
            return
        if permission not in ["active", "owner", "posting"]:
            raise AssertionError("Invalid permission")
        account = Account(account, morphene_instance=self.morphene)
        if permission not in account:
            account = Account(account, morphene_instance=self.morphene, lazy=False, full=True)
            account.clear_cache()
            account.refresh()
        if permission not in account:
            account = Account(account, morphene_instance=self.morphene)
        if permission not in account:
            raise AssertionError("Could not access permission")

        required_treshold = account[permission]["weight_threshold"]
        if self.morphene.wallet.locked():
            raise WalletLocked()

        def fetchkeys(account, perm, level=0):
            if level > 2:
                return []
            r = []
            for authority in account[perm]["key_auths"]:
                try:
                    wif = self.morphene.wallet.getPrivateKeyForPublicKey(
                        authority[0])
                    if wif:
                        r.append([wif, authority[1]])
                except ValueError:
                    pass
                except MissingKeyError:
                    pass

            if sum([x[1] for x in r]) < required_treshold:
                # go one level deeper
                for authority in account[perm]["account_auths"]:
                    auth_account = Account(
                        authority[0], morphene_instance=self.morphene)
                    r.extend(fetchkeys(auth_account, perm, level + 1))

            return r

        if account["name"] not in self.signing_accounts:
            # is the account an instance of public key?
            if isinstance(account, PublicKey):
                self.wifs.add(
                    self.morphene.wallet.getPrivateKeyForPublicKey(
                        str(account)
                    )
                )
            else:
                if permission not in account:
                    raise AssertionError("Could not access permission")
                required_treshold = account[permission]["weight_threshold"]
                keys = fetchkeys(account, permission)
                # If keys are empty, try again with active key
                if not keys and permission == "posting":
                    _keys = fetchkeys(account, "active")
                    keys.extend(_keys)
                # If keys are empty, try again with owner key
                if not keys and permission != "owner":
                    _keys = fetchkeys(account, "owner")
                    keys.extend(_keys)
                for x in keys:
                    self.wifs.add(x[0])

            self.signing_accounts.append(account["name"])

    def appendWif(self, wif):
        """ Add a wif that should be used for signing of the transaction.

            :param string wif: One wif key to use for signing
                a transaction.
        """
        if wif:
            try:
                PrivateKey(wif, prefix=self.morphene.prefix)
                self.wifs.add(wif)
            except:
                raise InvalidWifError

    def clearWifs(self):
        """Clear all stored wifs"""
        self.wifs = set()

    def constructTx(self, ref_block_num=None, ref_block_prefix=None):
        """ Construct the actual transaction and store it in the class's dict
            store

        """
        ops = list()
        for op in self.ops:
            # otherwise, we simply wrap ops into Operations
            ops.extend([Operation(op, prefix=self.morphene.prefix)])

        # We no wrap everything into an actual transaction
        expiration = formatTimeFromNow(
            self.expiration or self.morphene.expiration
        )
        if ref_block_num is None or ref_block_prefix is None:
            ref_block_num, ref_block_prefix = transactions.getBlockParams(
                self.morphene.rpc)
        self.tx = Signed_Transaction(
            ref_block_prefix=ref_block_prefix,
            expiration=expiration,
            operations=ops,
            ref_block_num=ref_block_num,
            custom_chains=self.morphene.custom_chains,
            prefix=self.morphene.prefix
        )

        super(TransactionBuilder, self).update(self.tx.json())
        self._unset_require_reconstruction()

    def sign(self, reconstruct_tx=True):
        """ Sign a provided transaction with the provided key(s)
            One or many wif keys to use for signing a transaction.
            The wif keys can be provided by "appendWif" or the
            signer can be defined "appendSigner". The wif keys
            from all signer that are defined by "appendSigner
            will be loaded from the wallet.

            :param bool reconstruct_tx: when set to False and tx
                is already contructed, it will not reconstructed
                and already added signatures remain

        """
        if not self._is_constructed() or (self._is_constructed() and reconstruct_tx):
            self.constructTx()
        if "operations" not in self or not self["operations"]:
            return
        if self.morphene.use_sc2:
            return
        # We need to set the default prefix, otherwise pubkeys are
        # presented wrongly!
        if self.morphene.rpc is not None:
            operations.default_prefix = (
                self.morphene.chain_params["prefix"])
        elif "blockchain" in self:
            operations.default_prefix = self["blockchain"]["prefix"]

        try:
            signedtx = Signed_Transaction(**self.json(with_prefix=True))
            signedtx.add_custom_chains(self.morphene.custom_chains)
        except:
            raise ValueError("Invalid TransactionBuilder Format")

        if not any(self.wifs):
            raise MissingKeyError

        signedtx.sign(self.wifs, chain=self.morphene.chain_params)
        self["signatures"].extend(signedtx.json().get("signatures"))
        return signedtx

    def verify_authority(self):
        """ Verify the authority of the signed transaction
        """
        try:
            self.morphene.rpc.set_next_node_on_empty_reply(False)
            args = self.json()
            ret = self.morphene.rpc.verify_authority(args, api="database")
            if not ret:
                raise InsufficientAuthorityError
            elif isinstance(ret, dict) and "valid" in ret and not ret["valid"]:
                raise InsufficientAuthorityError
        except Exception as e:
            raise e

    def get_potential_signatures(self):
        """ Returns public key from signature
        """
        if not self.morphene.is_connected():
            raise OfflineHasNoRPCException("No RPC available in offline mode!")
        self.morphene.rpc.set_next_node_on_empty_reply(False)
        args = self.json()
        ret = self.morphene.rpc.get_potential_signatures(args, api="database")
        if 'keys' in ret:
            ret = ret["keys"]
        return ret

    def get_transaction_hex(self):
        """ Returns a hex value of the transaction
        """
        if not self.morphene.is_connected():
            raise OfflineHasNoRPCException("No RPC available in offline mode!")
        self.morphene.rpc.set_next_node_on_empty_reply(False)
        args = self.json()
        ret = self.morphene.rpc.get_transaction_hex(args, api="database")
        if 'hex' in ret:
            ret = ret["hex"]
        return ret

    def get_required_signatures(self, available_keys=list()):
        """ Returns public key from signature
        """
        if not self.morphene.is_connected():
            raise OfflineHasNoRPCException("No RPC available in offline mode!")
        self.morphene.rpc.set_next_node_on_empty_reply(False)
        ret = self.morphene.rpc.get_required_signatures(self.json(), available_keys, api="database")

        return ret

    def broadcast(self, max_block_age=-1):
        """ Broadcast a transaction to the Morphene network
            Returns the signed transaction and clears itself
            after broadast

            Clears itself when broadcast was not successfully.

            :param int max_block_age: max block age

        """
        # Cannot broadcast an empty transaction
        if not self._is_signed():
            self.sign()

        if "operations" not in self or not self["operations"]:
            return
        ret = self.json()
        args = self.json()
        broadcast_api = "network_broadcast"

        if self.morphene.nobroadcast:
            log.info("Not broadcasting anything!")
            self.clear()
            return ret
        # Broadcast
        try:
            self.morphene.rpc.set_next_node_on_empty_reply(False)
            if self.morphene.blocking:
                ret = self.morphene.rpc.broadcast_transaction_synchronous(
                    args, api=broadcast_api)
                if "trx" in ret:
                    ret.update(**ret.get("trx"))
            else:
                self.morphene.rpc.broadcast_transaction(
                    args, api=broadcast_api)
        except Exception as e:
            # log.error("Could Not broadcasting anything!")
            self.clear()
            raise e

        self.clear()
        return ret

    def clear(self):
        """ Clear the transaction builder and start from scratch
        """
        self.ops = []
        self.wifs = set()
        self.signing_accounts = []
        # This makes sure that _is_constructed will return False afterwards
        self["expiration"] = None
        super(TransactionBuilder, self).__init__({})

    def addSigningInformation(self, account, permission, reconstruct_tx=False):
        """ This is a private method that adds side information to a
            unsigned/partial transaction in order to simplify later
            signing (e.g. for multisig or coldstorage)

            Not needed when "appendWif" was already or is going to be used

            FIXME: Does not work with owner keys!

            :param bool reconstruct_tx: when set to False and tx
                is already contructed, it will not reconstructed
                and already added signatures remain

        """
        if not self._is_constructed() or (self._is_constructed() and reconstruct_tx):
            self.constructTx()
        self["blockchain"] = self.morphene.chain_params

        if isinstance(account, PublicKey):
            self["missing_signatures"] = [
                str(account)
            ]
        else:
            accountObj = Account(account, morphene_instance=self.morphene)
            authority = accountObj[permission]
            # We add a required_authorities to be able to identify
            # how to sign later. This is an array, because we
            # may later want to allow multiple operations per tx
            self.update({"required_authorities": {
                accountObj["name"]: authority
            }})
            for account_auth in authority["account_auths"]:
                account_auth_account = Account(account_auth[0], morphene_instance=self.morphene)
                self["required_authorities"].update({
                    account_auth[0]: account_auth_account.get(permission)
                })

            # Try to resolve required signatures for offline signing
            self["missing_signatures"] = [
                x[0] for x in authority["key_auths"]
            ]
            # Add one recursion of keys from account_auths:
            for account_auth in authority["account_auths"]:
                account_auth_account = Account(account_auth[0], morphene_instance=self.morphene)
                self["missing_signatures"].extend(
                    [x[0] for x in account_auth_account[permission]["key_auths"]]
                )

    def appendMissingSignatures(self):
        """ Store which accounts/keys are supposed to sign the transaction

            This method is used for an offline-signer!
        """
        missing_signatures = self.get("missing_signatures", [])
        for pub in missing_signatures:
            try:
                wif = self.morphene.wallet.getPrivateKeyForPublicKey(pub)
                if wif:
                    self.appendWif(wif)
            except MissingKeyError:
                wif = None
