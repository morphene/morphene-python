# This Python file uses the following encoding: utf-8
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import str
import json
from morphenepython.instance import shared_morphene_instance
from morphenepythongraphenebase.py23 import bytes_types, integer_types, string_types, text_type
from .account import Account
from .exceptions import WitnessDoesNotExistsException
from .blockchainobject import BlockchainObject
from .utils import formatTimeString
from datetime import datetime, timedelta, date
from morphenepythonbase import transactions, operations
from morphenepythongraphenebase.account import PrivateKey, PublicKey
import pytz
from prettytable import PrettyTable


class Witness(BlockchainObject):
    """ Read data about a witness in the chain

        :param str account_name: Name of the witness
        :param MorpheneClient morphene_instance: MorpheneClient instance to use when
               accesing a RPC

        .. code-block:: python

           >>> from morphenepython.witness import Witness
           >>> Witness("initwitness")
           <Witness initwitness>

    """
    type_id = 3

    def __init__(
        self,
        owner,
        full=False,
        lazy=False,
        morphene_instance=None
    ):
        self.full = full
        self.lazy = lazy
        self.morphene = morphene_instance or shared_morphene_instance()
        if isinstance(owner, dict):
            owner = self._parse_json_data(owner)
        super(Witness, self).__init__(
            owner,
            lazy=lazy,
            full=full,
            id_item="owner",
            morphene_instance=morphene_instance
        )

    def refresh(self):
        if not self.identifier:
            return
        if not self.morphene.is_connected():
            return
        self.morphene.rpc.set_next_node_on_empty_reply(False)
        witness = self.morphene.rpc.get_witness_by_account(self.identifier)
        if not witness:
            raise WitnessDoesNotExistsException(self.identifier)
        witness = self._parse_json_data(witness)
        super(Witness, self).__init__(witness, id_item="owner", lazy=self.lazy, full=self.full, morphene_instance=self.morphene)

    def _parse_json_data(self, witness):
        parse_times = [
            "created", "hardfork_time_vote",
        ]
        for p in parse_times:
            if p in witness and isinstance(witness.get(p), string_types):
                witness[p] = formatTimeString(witness.get(p, "1970-01-01T00:00:00"))
        parse_int = [
            "votes", "virtual_last_update", "virtual_position", "virtual_scheduled_time",
        ]
        for p in parse_int:
            if p in witness and isinstance(witness.get(p), string_types):
                witness[p] = int(witness.get(p, "0"))
        return witness

    def json(self):
        output = self.copy()
        parse_times = [
            "created", "hardfork_time_vote",
        ]
        for p in parse_times:
            if p in output:
                p_date = output.get(p, datetime(1970, 1, 1, 0, 0))
                if isinstance(p_date, (datetime, date)):
                    output[p] = formatTimeString(p_date)
                else:
                    output[p] = p_date
        parse_int = [
            "votes", "virtual_last_update", "virtual_position", "virtual_scheduled_time",
        ]
        for p in parse_int:
            if p in output and isinstance(output[p], integer_types):
                output[p] = str(output[p])
        return json.loads(str(json.dumps(output)))

    @property
    def account(self):
        return Account(self["owner"], morphene_instance=self.morphene)

    @property
    def is_active(self):
        return len(self['signing_key']) > 3 and self['signing_key'][3:] != '1111111111111111111111111111111114T1Anm'

    def update(self, signing_key, url, props, account=None):
        """ Update witness

            :param str signing_key: Signing key
            :param str url: URL
            :param dict props: Properties
            :param str account: (optional) witness account name

            Properties:::

                {
                    "account_creation_fee": x,
                    "maximum_block_size": x,
                }

        """
        if not account:
            account = self["owner"]
        return self.morphene.witness_update(signing_key, url, props, account=account)


class WitnessesObject(list):
    def printAsTable(self, sort_key="votes", reverse=True, return_str=False, **kwargs):
        utc = pytz.timezone('UTC')
        table_header = ["Name", "Votes [PV]", "Disabled", "Missed", "Fee", "Size", "Version"]
        t = PrettyTable(table_header)
        t.align = "l"
        if sort_key == 'account_creation_fee':
            sortedList = sorted(self, key=lambda self: self['props']['account_creation_fee'], reverse=reverse)
        elif sort_key == 'maximum_block_size':
            sortedList = sorted(self, key=lambda self: self['props']['maximum_block_size'], reverse=reverse)
        elif sort_key == 'votes':
            sortedList = sorted(self, key=lambda self: int(self[sort_key]), reverse=reverse)
        else:
            sortedList = sorted(self, key=lambda self: self[sort_key], reverse=reverse)
        for witness in sortedList:
            disabled = ""
            if not witness.is_active:
                disabled = "yes"

            t.add_row([witness['owner'],
                       str(round(int(witness['votes']) / 1e15, 2)),
                       disabled,
                       str(witness['total_missed']),
                       str(witness['props']['account_creation_fee']),
                       str(witness['props']['maximum_block_size']),
                       witness['running_version']])
        if return_str:
            return t.get_string(**kwargs)
        else:
            print(t.get_string(**kwargs))

    def get_votes_sum(self):
        vote_sum = 0
        for witness in self:
            vote_sum += int(witness['votes'])
        return vote_sum

    def __contains__(self, item):
        from .account import Account
        if isinstance(item, Account):
            name = item["name"]
        elif self.morphene:
            account = Account(item, morphene_instance=self.morphene)
            name = account["name"]

        return (
            any([name == x["owner"] for x in self])
        )

    def __str__(self):
        return self.printAsTable(return_str=True)

    def __repr__(self):
        return "<%s %s>" % (
            self.__class__.__name__, str(self.identifier))


class GetWitnesses(WitnessesObject):
    """ Obtain a list of witnesses

        :param list name_list: list of witneses to fetch
        :param int batch_limit: (optional) maximum number of witnesses
            to fetch per call, defaults to 100
        :param MorpheneClient morphene_instance: MorpheneClient() instance to use when
            accessing a RPCcreator = Witness(creator, morphene_instance=self)

        .. code-block:: python

            from morphenepython.witness import GetWitnesses
            w = GetWitnesses(["initwitness", "jesta"])
            print(w[0].json())
            print(w[1].json())

    """
    def __init__(self, name_list, batch_limit=100, lazy=False, full=True, morphene_instance=None):
        self.morphene = morphene_instance or shared_morphene_instance()
        if not self.morphene.is_connected():
            return
        witnesses = []
        name_cnt = 0
        for witness in name_list:
            witnesses.append(self.morphene.rpc.get_witness_by_account(witness))
        self.identifier = ""
        super(GetWitnesses, self).__init__(
            [
                Witness(x, lazy=lazy, full=full, morphene_instance=self.morphene)
                for x in witnesses
            ]
        )


class Witnesses(WitnessesObject):
    """ Obtain a list of **active** witnesses and the current schedule

        :param MorpheneClient morphene_instance: MorpheneClient instance to use when
            accesing a RPC

        .. code-block:: python

           >>> from morphenepython.witness import Witnesses
           >>> Witnesses()
           <Witnesses >

    """
    def __init__(self, lazy=False, full=True, morphene_instance=None):
        self.morphene = morphene_instance or shared_morphene_instance()
        self.lazy = lazy
        self.full = full
        self.refresh()

    def refresh(self):
        self.morphene.rpc.set_next_node_on_empty_reply(False)
        self.active_witnessess = self.morphene.rpc.get_active_witnesses()
        self.schedule = self.morphene.rpc.get_witness_schedule()
        self.witness_count = self.morphene.rpc.get_witness_count()
        self.current_witness = self.morphene.get_dynamic_global_properties(use_stored_data=False)["current_witness"]
        self.identifier = ""
        super(Witnesses, self).__init__(
            [
                Witness(x, lazy=self.lazy, full=self.full, morphene_instance=self.morphene)
                for x in self.active_witnessess
            ]
        )


class WitnessesVotedByAccount(WitnessesObject):
    """ Obtain a list of witnesses which have been voted by an account

        :param str account: Account name
        :param MorpheneClient morphene_instance: MorpheneClient instance to use when
            accesing a RPC

        .. code-block:: python

           >>> from morphenepython.witness import WitnessesVotedByAccount
           >>> WitnessesVotedByAccount("initwitness")
           <WitnessesVotedByAccount initwitness>

    """
    def __init__(self, account, lazy=False, full=True, morphene_instance=None):
        self.morphene = morphene_instance or shared_morphene_instance()
        self.account = Account(account, full=True, morphene_instance=self.morphene)
        account_name = self.account["name"]
        self.identifier = account_name
        self.morphene.rpc.set_next_node_on_empty_reply(False)
        if "witness_votes" not in self.account:
            return
        witnessess = self.account["witness_votes"]

        super(WitnessesVotedByAccount, self).__init__(
            [
                Witness(x, lazy=lazy, full=full, morphene_instance=self.morphene)
                for x in witnessess
            ]
        )


class WitnessesRankedByVote(WitnessesObject):
    """ Obtain a list of witnesses ranked by Vote

        :param str from_account: Witness name from which the lists starts (default = "")
        :param int limit: Limits the number of shown witnesses (default = 100)
        :param MorpheneClient morphene_instance: MorpheneClient instance to use when
            accesing a RPC

        .. code-block:: python

           >>> from morphenepython.witness import WitnessesRankedByVote
           >>> WitnessesRankedByVote(limit=100)
           <WitnessesRankedByVote >

    """
    def __init__(self, from_account="", limit=100, lazy=False, full=False, morphene_instance=None):
        self.morphene = morphene_instance or shared_morphene_instance()
        witnessList = []
        last_limit = limit
        self.identifier = ""
        self.morphene.rpc.set_next_node_on_empty_reply(False)
        query_limit = 1000
        last_account = from_account
        if limit > query_limit:
            while last_limit > query_limit:
                tmpList = WitnessesRankedByVote(last_account, query_limit)
                if (last_limit < limit):
                    witnessList.extend(tmpList[1:])
                    last_limit -= query_limit - 1
                else:
                    witnessList.extend(tmpList)
                    last_limit -= query_limit
                last_account = witnessList[-1]["owner"]
        if (last_limit < limit):
            last_limit += 1
        witnessess = self.morphene.rpc.get_witnesses_by_vote(last_account, last_limit)
        # self.witness_count = len(self.voted_witnessess)
        if (last_limit < limit):
            witnessess = witnessess[1:]
        if len(witnessess) > 0:
            for x in witnessess:
                witnessList.append(Witness(x, lazy=lazy, full=full, morphene_instance=self.morphene))
        if len(witnessList) == 0:
            return
        super(WitnessesRankedByVote, self).__init__(witnessList)


class ListWitnesses(WitnessesObject):
    """ List witnesses ranked by name

        :param str from_account: Witness name from which the lists starts (default = "")
        :param int limit: Limits the number of shown witnesses (default = 100)
        :param MorpheneClient morphene_instance: MorpheneClient instance to use when
            accesing a RPC

        .. code-block:: python

           >>> from morphenepython.witness import ListWitnesses
           >>> ListWitnesses(from_account="initwitness", limit=100)
           <ListWitnesses initwitness>

    """
    def __init__(self, from_account="", limit=100, lazy=False, full=False, morphene_instance=None):
        self.morphene = morphene_instance or shared_morphene_instance()
        self.identifier = from_account
        self.morphene.rpc.set_next_node_on_empty_reply(False)
        witnessess = self.morphene.rpc.lookup_witness_accounts(from_account, limit)
        if len(witnessess) == 0:
            return
        super(ListWitnesses, self).__init__(
            [
                Witness(x, lazy=lazy, full=full, morphene_instance=self.morphene)
                for x in witnessess
            ]
        )
