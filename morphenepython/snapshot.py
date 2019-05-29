# This Python file uses the following encoding: utf-8
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import bytes, int, str
import pytz
import json
import re
from datetime import datetime, timedelta, date, time
import math
import random
import logging
from bisect import bisect_left
from morphenepython.utils import formatTimeString, formatTimedelta, remove_from_dict, addTzInfo, parse_time
from morphenepython.amount import Amount
from morphenepython.account import Account
from morphenepython.instance import shared_morphene_instance
from morphenepython.constants import MORPHENE_1_PERCENT, MORPHENE_100_PERCENT

log = logging.getLogger(__name__)


class AccountSnapshot(list):
    """ This class allows to easily access Account history

        :param str account_name: Name of the account
        :param MorpheneClient morphene_instance: MorpheneClient
               instance
    """
    def __init__(self, account, account_history=[], morphene_instance=None):
        self.morphene = morphene_instance or shared_morphene_instance()
        self.account = Account(account, morphene_instance=self.morphene)
        self.reset()
        super(AccountSnapshot, self).__init__(account_history)

    def reset(self):
        """ Resets the arrays not the stored account history
        """
        self.own_vests = [Amount(0, self.morphene.vests_symbol, morphene_instance=self.morphene)]
        self.own_morph = [Amount(0, self.morphene.morph_symbol, morphene_instance=self.morphene)]
        self.delegated_vests_in = [{}]
        self.delegated_vests_out = [{}]
        self.timestamps = [addTzInfo(datetime(1970, 1, 1, 0, 0, 0, 0))]
        import morphenepythonbase.operationids
        self.ops_statistics = morphenepythonbase.operationids.operations.copy()
        for key in self.ops_statistics:
            self.ops_statistics[key] = 0

    def search(self, search_str, start=None, stop=None, use_block_num=True):
        """ Returns ops in the given range"""
        ops = []
        if start is not None:
            start = addTzInfo(start)
        if stop is not None:
            stop = addTzInfo(stop)
        for op in self:
            if use_block_num and start is not None and isinstance(start, int):
                if op["block"] < start:
                    continue
            elif not use_block_num and start is not None and isinstance(start, int):
                if op["index"] < start:
                    continue
            elif start is not None and isinstance(start, (datetime, date, time)):
                if start > formatTimeString(op["timestamp"]):
                    continue
            if use_block_num and stop is not None and isinstance(stop, int):
                if op["block"] > stop:
                    continue
            elif not use_block_num and stop is not None and isinstance(stop, int):
                if op["index"] > stop:
                    continue
            elif stop is not None and isinstance(stop, (datetime, date, time)):
                if stop < formatTimeString(op["timestamp"]):
                    continue
            op_string = json.dumps(list(op.values()))
            if re.search(search_str, op_string):
                ops.append(op)
        return ops

    def get_ops(self, start=None, stop=None, use_block_num=True, only_ops=[], exclude_ops=[]):
        """ Returns ops in the given range"""
        if start is not None:
            start = addTzInfo(start)
        if stop is not None:
            stop = addTzInfo(stop)
        for op in self:
            if use_block_num and start is not None and isinstance(start, int):
                if op["block"] < start:
                    continue
            elif not use_block_num and start is not None and isinstance(start, int):
                if op["index"] < start:
                    continue
            elif start is not None and isinstance(start, (datetime, date, time)):
                if start > formatTimeString(op["timestamp"]):
                    continue
            if use_block_num and stop is not None and isinstance(stop, int):
                if op["block"] > stop:
                    continue
            elif not use_block_num and stop is not None and isinstance(stop, int):
                if op["index"] > stop:
                    continue
            elif stop is not None and isinstance(stop, (datetime, date, time)):
                if stop < formatTimeString(op["timestamp"]):
                    continue
            if exclude_ops and op["type"] in exclude_ops:
                continue
            if not only_ops or op["type"] in only_ops:
                yield op

    def get_data(self, timestamp=None, index=0):
        """ Returns snapshot for given timestamp"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        timestamp = addTzInfo(timestamp)
        # Find rightmost value less than x
        i = bisect_left(self.timestamps, timestamp)
        if i:
            index = i - 1
        else:
            return {}
        ts = self.timestamps[index]
        own = self.own_vests[index]
        din = self.delegated_vests_in[index]
        dout = self.delegated_vests_out[index]
        morph = self.own_morph[index]
        sum_in = sum([din[key].amount for key in din])
        sum_out = sum([dout[key].amount for key in dout])
        sp_in = self.morphene.vests_to_sp(sum_in, timestamp=ts)
        sp_out = self.morphene.vests_to_sp(sum_out, timestamp=ts)
        sp_own = self.morphene.vests_to_sp(own, timestamp=ts)
        sp_eff = sp_own + sp_in - sp_out
        return {"timestamp": ts, "vests": own, "delegated_vests_in": din, "delegated_vests_out": dout,
                "sp_own": sp_own, "sp_eff": sp_eff, "morph": morph, "index": index}

    def get_account_history(self, start=None, stop=None, use_block_num=True):
        """ Uses account history to fetch all related ops

            :param start: start number/date of transactions to
                return (*optional*)
            :type start: int, datetime
            :param stop: stop number/date of transactions to
                return (*optional*)
            :type stop: int, datetime
            :param bool use_block_num: if true, start and stop are block numbers,
                otherwise virtual OP count numbers.

        """
        super(AccountSnapshot, self).__init__(
            [
                h
                for h in self.account.history(start=start, stop=stop, use_block_num=use_block_num)
            ]
        )

    def update(self, timestamp, own, delegated_in=None, delegated_out=None, morph=0):
        """ Updates the internal state arrays

            :param datetime timestamp: datetime of the update
            :param own: vests
            :type own: amount.Amount, float
            :param dict delegated_in: Incoming delegation
            :param dict delegated_out: Outgoing delegation
            :param morph: morph
            :type morph: amount.Amount, float

        """
        self.timestamps.append(timestamp - timedelta(seconds=1))
        self.own_vests.append(self.own_vests[-1])
        self.own_morph.append(self.own_morph[-1])
        self.delegated_vests_in.append(self.delegated_vests_in[-1])
        self.delegated_vests_out.append(self.delegated_vests_out[-1])

        self.timestamps.append(timestamp)
        self.own_vests.append(self.own_vests[-1] + own)
        self.own_morph.append(self.own_morph[-1] + morph)

        new_deleg = dict(self.delegated_vests_in[-1])
        if delegated_in is not None and delegated_in:
            if delegated_in['amount'] == 0:
                del new_deleg[delegated_in['account']]
            else:
                new_deleg[delegated_in['account']] = delegated_in['amount']
        self.delegated_vests_in.append(new_deleg)

        new_deleg = dict(self.delegated_vests_out[-1])
        if delegated_out is not None and delegated_out:
            if delegated_out['account'] is None:
                # return_vesting_delegation
                for delegatee in new_deleg:
                    if new_deleg[delegatee]['amount'] == delegated_out['amount']:
                        del new_deleg[delegatee]
                        break

            elif delegated_out['amount'] != 0:
                # new or updated non-zero delegation
                new_deleg[delegated_out['account']] = delegated_out['amount']

                # skip undelegations here, wait for 'return_vesting_delegation'
                # del new_deleg[delegated_out['account']]

        self.delegated_vests_out.append(new_deleg)

    def build(self, only_ops=[], exclude_ops=[]):
        """ Builds the account history based on all account operations

            :param array only_ops: Limit generator by these
                operations (*optional*)
            :param array exclude_ops: Exclude thse operations from
                generator (*optional*)

        """
        if len(self.timestamps) > 0:
            start_timestamp = self.timestamps[-1]
        else:
            start_timestamp = None
        for op in sorted(self, key=lambda k: k['timestamp']):
            ts = parse_time(op['timestamp'])
            if start_timestamp is not None and start_timestamp > ts:
                continue
            # print(op)
            if op['type'] in exclude_ops:
                continue
            if len(only_ops) > 0 and op['type'] not in only_ops:
                continue
            self.ops_statistics[op['type']] += 1
            self.parse_op(op, only_ops=only_ops)

    def parse_op(self, op, only_ops=[]):
        """ Parse account history operation"""
        ts = parse_time(op['timestamp'])

        if op['type'] == "account_create":
            fee_morph = Amount(op['fee'], morphene_instance=self.morphene).amount
            fee_vests = self.morphene.sp_to_vests(Amount(op['fee'], morphene_instance=self.morphene).amount, timestamp=ts)
            # print(fee_vests)
            if op['new_account_name'] == self.account["name"]:
                self.update(ts, fee_vests, 0, 0)
                return
            if op['creator'] == self.account["name"]:
                self.update(ts, 0, 0, 0, fee_morph * (-1), 0)
                return

        elif op['type'] == "account_create_with_delegation":
            fee_morph = Amount(op['fee'], morphene_instance=self.morphene).amount
            fee_vests = self.morphene.sp_to_vests(Amount(op['fee'], morphene_instance=self.morphene).amount, timestamp=ts)
            if op['new_account_name'] == self.account["name"]:
                if Amount(op['delegation'], morphene_instance=self.morphene).amount > 0:
                    delegation = {'account': op['creator'], 'amount':
                                  Amount(op['delegation'], morphene_instance=self.morphene)}
                else:
                    delegation = None
                self.update(ts, fee_vests, delegation, 0)
                return

            if op['creator'] == self.account["name"]:
                delegation = {'account': op['new_account_name'], 'amount':
                              Amount(op['delegation'], morphene_instance=self.morphene)}
                self.update(ts, 0, 0, delegation, fee_morph * (-1), 0)
                return

        elif op['type'] == "delegate_vesting_shares":
            vests = Amount(op['vesting_shares'], morphene_instance=self.morphene)
            # print(op)
            if op['delegator'] == self.account["name"]:
                delegation = {'account': op['delegatee'], 'amount': vests}
                self.update(ts, 0, 0, delegation)
                return
            if op['delegatee'] == self.account["name"]:
                delegation = {'account': op['delegator'], 'amount': vests}
                self.update(ts, 0, delegation, 0)
                return

        elif op['type'] == "transfer":
            amount = Amount(op['amount'], morphene_instance=self.morphene)
            # print(op)
            if op['from'] == self.account["name"]:
                if amount.symbol == self.morphene.morph_symbol:
                    self.update(ts, 0, 0, 0, amount * (-1), 0)
            if op['to'] == self.account["name"]:
                if amount.symbol == self.morphene.morph_symbol:
                    self.update(ts, 0, 0, 0, amount, 0)
            # print(op, vests)
            # self.update(ts, vests, 0, 0)
            return

        elif op['type'] == "transfer_to_vesting":
            morph = Amount(op['amount'], morphene_instance=self.morphene)
            vests = self.morphene.sp_to_vests(morph.amount, timestamp=ts)
            if op['from'] == self.account["name"]:
                self.update(ts, vests, 0, 0, morph * (-1), 0)
            else:
                self.update(ts, vests, 0, 0, 0, 0)
            # print(op)
            # print(op, vests)
            return

        elif op['type'] == "fill_vesting_withdraw":
            # print(op)
            vests = Amount(op['withdrawn'], morphene_instance=self.morphene)
            self.update(ts, vests * (-1), 0, 0)
            return

        elif op['type'] == "return_vesting_delegation":
            delegation = {'account': None, 'amount':
                          Amount(op['vesting_shares'], morphene_instance=self.morphene)}
            self.update(ts, 0, 0, delegation)
            return

        elif op['type'] == "producer_reward":
            vests = Amount(op['vesting_shares'], morphene_instance=self.morphene)
            self.update(ts, vests, 0, 0)
            return

        elif op['type'] in ['shutdown_witness', 'account_witness_vote', 'witness_update',
                            'account_update', 'account_witness_proxy', 'recover_account',
                            'pow', 'request_account_recovery']:
            return


    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "<%s %s>" % (
            self.__class__.__name__, str(self.account["name"]))
