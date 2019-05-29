from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import bytes, int, str
from builtins import object
from future.utils import python_2_unicode_compatible
import json
from morphenepythongraphenebase.py23 import py23_bytes, bytes_types, integer_types, string_types, text_type
from collections import OrderedDict
from morphenepythongraphenebase.types import (
    Uint8, Int16, Uint16, Uint32, Uint64,
    Varint32, Int64, String, Bytes, Void,
    Array, PointInTime, Signature, Bool,
    Set, Fixed_array, Optional, Static_variant,
    Map, Id
)
from morphenepythongraphenebase.objects import GrapheneObject, isArgsThisClass
from .objecttypes import object_type
from morphenepythongraphenebase.account import PublicKey
from morphenepythongraphenebase.objects import Operation as GPHOperation
from morphenepythongraphenebase.chains import known_chains
from .operationids import operations, operations_wls
import struct
default_prefix = "MPH"


@python_2_unicode_compatible
class Amount(object):
    def __init__(self, d, prefix=default_prefix):
        if isinstance(d, string_types):
            self.amount, self.symbol = d.strip().split(" ")
            self.precision = None
            for c in known_chains:
                if self.precision is not None:
                    continue
                if known_chains[c]["prefix"] != prefix:
                    continue
                for asset in known_chains[c]["chain_assets"]:
                    if self.precision is not None:
                        continue
                    if asset["symbol"] == self.symbol:
                        self.precision = asset["precision"]
                        self.asset = asset["asset"]
                    elif asset["asset"] == self.symbol:
                        self.precision = asset["precision"]
                        self.asset = asset["asset"]
            if self.precision is None:
                raise Exception("Asset unknown")
            self.amount = round(float(self.amount) * 10 ** self.precision)

            self.str_repr = '{:.{}f} {}'.format((float(self.amount) / 10 ** self.precision), self.precision, self.symbol)
        elif isinstance(d, list):
            self.amount = d[0]
            self.asset = d[2]
            self.precision = d[1]
            self.symbol = None
            for c in known_chains:
                if known_chains[c]["prefix"] != prefix:
                    continue
                for asset in known_chains[c]["chain_assets"]:
                    if asset["asset"] == self.asset:
                        self.symbol = asset["symbol"]
            if self.symbol is None:
                raise ValueError("Unknown NAI, cannot resolve symbol")
            a = Array([String(d[0]), d[1], d[2]])
            self.str_repr = str(a.__str__())
        elif isinstance(d, dict) and "nai" in d:
            self.asset = d["nai"]
            self.symbol = None
            for c in known_chains:
                if known_chains[c]["prefix"] != prefix:
                    continue
                for asset in known_chains[c]["chain_assets"]:
                    if asset["asset"] == d["nai"]:
                        self.symbol = asset["symbol"]
            if self.symbol is None:
                raise ValueError("Unknown NAI, cannot resolve symbol")
            self.amount = d["amount"]
            self.precision = d["precision"]
            self.str_repr = json.dumps(d)
        else:
            self.amount = d.amount
            self.symbol = d.symbol
            self.asset = d.asset["asset"]
            self.precision = d.asset["precision"]
            self.amount = round(float(self.amount) * 10 ** self.precision)
            self.str_repr = str(d)
            # self.str_repr = json.dumps((d.json()))
            # self.str_repr = '{:.{}f} {}'.format((float(self.amount) / 10 ** self.precision), self.precision, self.asset)

    def __bytes__(self):
        # padding
        symbol = self.symbol + "\x00" * (7 - len(self.symbol))
        return (struct.pack("<q", int(self.amount)) + struct.pack("<b", self.precision) +
                py23_bytes(symbol, "ascii"))

    def __str__(self):
        # return json.dumps({"amount": self.amount, "precision": self.precision, "nai": self.asset})
        return self.str_repr


@python_2_unicode_compatible
class Operation(GPHOperation):
    def __init__(self, *args, **kwargs):
        self.prefix = kwargs.pop("prefix", default_prefix)
        super(Operation, self).__init__(*args, **kwargs)

    def _getklass(self, name):
        module = __import__("morphenepythonbase.operations", fromlist=["operations"])
        class_ = getattr(module, name)
        return class_

    def operations(self):
        if self.prefix == "WLS":
            return operations_wls
        return operations

    def getOperationNameForId(self, i):
        """ Convert an operation id into the corresponding string
        """
        for key in self.operations():
            if int(self.operations()[key]) is int(i):
                return key
        return "Unknown Operation ID %d" % i

    def json(self):
        return json.loads(str(self))
        # return json.loads(str(json.dumps([self.name, self.op.toJson()])))

    def __bytes__(self):
        return py23_bytes(Id(self.opId)) + py23_bytes(self.op)

    def __str__(self):
        return json.dumps([self.name.lower(), self.op.toJson()])


class Memo(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
                self.data = args[0].data
        else:
            prefix = kwargs.pop("prefix", default_prefix)
            if "encrypted" not in kwargs or not kwargs["encrypted"]:
                super(Memo, self).__init__(None)
            else:
                if len(args) == 1 and len(kwargs) == 0:
                    kwargs = args[0]
                if "encrypted" in kwargs and kwargs["encrypted"]:
                    super(Memo, self).__init__(OrderedDict([
                        ('from', PublicKey(kwargs["from"], prefix=prefix)),
                        ('to', PublicKey(kwargs["to"], prefix=prefix)),
                        ('nonce', Uint64(int(kwargs["nonce"]))),
                        ('check', Uint32(int(kwargs["check"]))),
                        ('encrypted', Bytes(kwargs["encrypted"]))
                    ]))


class WitnessProps(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            prefix = kwargs.get("prefix", default_prefix)
            super(WitnessProps, self).__init__(OrderedDict([
                ('account_creation_fee', Amount(kwargs["account_creation_fee"], prefix=prefix)),
                ('maximum_block_size', Uint32(kwargs["maximum_block_size"])),
            ]))


class Permission(GrapheneObject):
    def __init__(self, *args, **kwargs):
        if isArgsThisClass(self, args):
            self.data = args[0].data
        else:
            prefix = kwargs.pop("prefix", default_prefix)

            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]

            # Sort keys (FIXME: ideally, the sorting is part of Public
            # Key and not located here)
            kwargs["key_auths"] = sorted(
                kwargs["key_auths"],
                key=lambda x: repr(PublicKey(x[0], prefix=prefix)),
                reverse=False,
            )
            kwargs["account_auths"] = sorted(
                kwargs["account_auths"],
                key=lambda x: x[0],
                reverse=False,
            )
            accountAuths = Map([
                [String(e[0]), Uint16(e[1])]
                for e in kwargs["account_auths"]
            ])
            keyAuths = Map([
                [PublicKey(e[0], prefix=prefix), Uint16(e[1])]
                for e in kwargs["key_auths"]
            ])
            super(Permission, self).__init__(OrderedDict([
                ('weight_threshold', Uint32(int(kwargs["weight_threshold"]))),
                ('account_auths', accountAuths),
                ('key_auths', keyAuths),
            ]))


@python_2_unicode_compatible
class Extension(Array):
    def __str__(self):
        """ We overload the __str__ function because the json
            representation is different for extensions
        """
        return json.dumps(self.json)

