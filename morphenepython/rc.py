# This Python file uses the following encoding: utf-8
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import logging
import json
from .instance import shared_morphene_instance
from morphenepython.constants import state_object_size_info, resource_execution_time
import hashlib
from binascii import hexlify, unhexlify
import os
from pprint import pprint
from morphenepython.amount import Amount
from morphenepythonbase import operations
from morphenepythonbase.objects import Operation
from morphenepythonbase.signedtransactions import Signed_Transaction
from morphenepythongraphenebase.py23 import py23_bytes, bytes_types


class RC(object):
    def __init__(
        self,
        morphene_instance=None,
    ):
        self.morphene = morphene_instance or shared_morphene_instance()

    def get_tx_size(self, op):
        """Returns the tx size of an operation"""
        ops = [Operation(op)]
        prefix = u"MORPH"
        wif = "5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"
        ref_block_num = 34294
        ref_block_prefix = 3707022213
        expiration = "2016-04-06T08:29:27"
        tx = Signed_Transaction(ref_block_num=ref_block_num,
                                ref_block_prefix=ref_block_prefix,
                                expiration=expiration,
                                operations=ops)
        tx = tx.sign([wif], chain=prefix)
        txWire = hexlify(py23_bytes(tx)).decode("ascii")
        tx_size = len(txWire)
        return tx_size

    def get_resource_count(self, tx_size, execution_time_count, state_bytes_count=0, new_account_op_count=0, market_op_count=0):
        """Creates the resource_count dictionary based on tx_size, state_bytes_count, new_account_op_count and market_op_count"""
        resource_count = {"resource_history_bytes": tx_size}
        resource_count["resource_state_bytes"] = state_object_size_info["transaction_object_base_size"]
        resource_count["resource_state_bytes"] += state_object_size_info["transaction_object_byte_size"] * tx_size
        resource_count["resource_state_bytes"] += state_bytes_count
        resource_count["resource_new_accounts"] = new_account_op_count
        resource_count["resource_execution_time"] = execution_time_count
        if market_op_count > 0:
            resource_count["resource_market_bytes"] = tx_size
        return resource_count

    def transfer_dict(self, transfer_dict):
        """Calc RC costs for a transfer dict object"""
        market_op_count = 1
        op = operations.Transfer(**transfer_dict)
        tx_size = self.get_tx_size(op)
        return self.transfer(tx_size=tx_size, market_op_count=market_op_count)

    def transfer(self, tx_size=290, market_op_count=1):
        """Calc RC of a transfer"""
        execution_time_count = resource_execution_time["transfer_operation_exec_time"]
        resource_count = self.get_resource_count(tx_size, execution_time_count, market_op_count=market_op_count)
        return self.morphene.get_rc_cost(resource_count)

    def account_update_dict(self, account_update_dict):
        """Calc RC costs for account update"""
        op = operations.Account_update(**account_update_dict)
        tx_size = self.get_tx_size(op)
        execution_time_count = resource_execution_time["account_update_operation_exec_time"]
        resource_count = self.get_resource_count(tx_size, execution_time_count)
        return self.morphene.get_rc_cost(resource_count)

    def claim_account(self, tx_size=300):
        """Claim account"""
        execution_time_count = resource_execution_time["claim_account_operation_exec_time"]
        resource_count = self.get_resource_count(tx_size, execution_time_count, new_account_op_count=1)
        return self.morphene.get_rc_cost(resource_count)

    def get_authority_byte_count(self, auth):
        return (state_object_size_info["authority_base_size"]
                + state_object_size_info["authority_account_member_size"] * len(auth["account_auths"])
                + state_object_size_info["authority_key_member_size"] * len(auth["key_auths"]))

    def account_create_dict(self, account_create_dict):
        """Calc RC costs for account create"""
        op = operations.Account_create(**account_create_dict)
        state_bytes_count = state_object_size_info["account_object_base_size"]
        state_bytes_count += state_object_size_info["account_authority_object_base_size"]
        state_bytes_count += self.get_authority_byte_count(account_create_dict["owner"])
        state_bytes_count += self.get_authority_byte_count(account_create_dict["active"])
        state_bytes_count += self.get_authority_byte_count(account_create_dict["posting"])
        tx_size = self.get_tx_size(op)
        execution_time_count = resource_execution_time["account_update_operation_exec_time"]
        resource_count = self.get_resource_count(tx_size, execution_time_count, state_bytes_count)
        return self.morphene.get_rc_cost(resource_count)

    def create_claimed_account_dict(self, create_claimed_account_dict):
        """Calc RC costs for claimed account create"""
        op = operations.Create_claimed_account(**create_claimed_account_dict)
        state_bytes_count = state_object_size_info["account_object_base_size"]
        state_bytes_count += state_object_size_info["account_authority_object_base_size"]
        state_bytes_count += self.get_authority_byte_count(create_claimed_account_dict["owner"])
        state_bytes_count += self.get_authority_byte_count(create_claimed_account_dict["active"])
        state_bytes_count += self.get_authority_byte_count(create_claimed_account_dict["posting"])
        tx_size = self.get_tx_size(op)
        execution_time_count = resource_execution_time["account_update_operation_exec_time"]
        resource_count = self.get_resource_count(tx_size, execution_time_count, state_bytes_count)
        return self.morphene.get_rc_cost(resource_count)
