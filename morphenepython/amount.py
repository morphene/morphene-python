# This Python file uses the following encoding: utf-8
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import bytes, int, str
from future.utils import python_2_unicode_compatible
from morphenepythongraphenebase.py23 import bytes_types, integer_types, string_types, text_type
from morphenepython.instance import shared_morphene_instance
from morphenepython.asset import Asset
from decimal import Decimal, ROUND_DOWN


def check_asset(other, self):
    if isinstance(other, dict) and "asset" in other and isinstance(self, dict) and "asset" in self:
        if not other["asset"] == self["asset"]:
            raise AssertionError()
    else:
        if not other == self:
            raise AssertionError()


def quantize(amount, precision):
    # make sure amount is decimal and has the asset precision
    amount = Decimal(amount)
    places = Decimal(10) ** (-precision)
    return amount.quantize(places, rounding=ROUND_DOWN)  


@python_2_unicode_compatible
class Amount(dict):
    """ This class deals with Amounts of any asset to simplify dealing with the tuple::

            (amount, asset)

        :param list args: Allows to deal with different representations of an amount
        :param float amount: Let's create an instance with a specific amount
        :param str asset: Let's you create an instance with a specific asset (symbol)
        :param boolean fixed_point_arithmetic: when set to True, all operation are fixed
            point operations and the amount is always be rounded down to the precision
        :param MorpheneClient morphene_instance: MorpheneClient instance
        :returns: All data required to represent an Amount/Asset
        :rtype: dict
        :raises ValueError: if the data provided is not recognized

        Way to obtain a proper instance:

            * ``args`` can be a string, e.g.:  "1 MORPH"
            * ``args`` can be a dictionary containing ``amount`` and ``asset_id``
            * ``args`` can be a dictionary containing ``amount`` and ``asset``
            * ``args`` can be a list of a ``float`` and ``str`` (symbol)
            * ``args`` can be a list of a ``float`` and a :class:`morphenepython.asset.Asset`
            * ``amount`` and ``asset`` are defined manually

        An instance is a dictionary and comes with the following keys:

            * ``amount`` (float)
            * ``symbol`` (str)
            * ``asset`` (instance of :class:`morphenepython.asset.Asset`)

        Instances of this class can be used in regular mathematical expressions
        (``+-*/%``) such as:

        .. testcode::

            from morphenepython.amount import Amount
            from morphenepython.asset import Asset
            a = Amount("1 MORPH")
            b = Amount(1, "MORPH")
            c = Amount("20", Asset("MORPH"))
            a + b
            a * 2
            a += b
            a /= 2.0

        .. testoutput::

            2.000 MORPH
            2.000 MORPH

    """
    def __init__(self, amount, asset=None, fixed_point_arithmetic=False, morphene_instance=None):
        self["asset"] = {}
        self.fixed_point_arithmetic = fixed_point_arithmetic
        self.morphene = morphene_instance or shared_morphene_instance()
        if amount and asset is None and isinstance(amount, Amount):
            # Copy Asset object
            self["amount"] = amount["amount"]
            self["symbol"] = amount["symbol"]
            self["asset"] = amount["asset"]

        elif amount and asset is None and isinstance(amount, list) and len(amount) == 3:
            # Copy Asset object
            self["amount"] = Decimal(amount[0]) / Decimal(10 ** amount[1])
            self["asset"] = Asset(amount[2], morphene_instance=self.morphene)
            self["symbol"] = self["asset"]["symbol"]

        elif amount and asset is None and isinstance(amount, dict) and "amount" in amount and "nai" in amount and "precision" in amount:
            # Copy Asset object
            self["amount"] = Decimal(amount["amount"]) / Decimal(10 ** amount["precision"])
            self["asset"] = Asset(amount["nai"], morphene_instance=self.morphene)
            self["symbol"] = self["asset"]["symbol"]

        elif amount is not None and asset is None and isinstance(amount, string_types):
            self["amount"], self["symbol"] = amount.split(" ")
            self["asset"] = Asset(self["symbol"], morphene_instance=self.morphene)

        elif (amount and asset is None and isinstance(amount, dict) and "amount" in amount and "asset_id" in amount):
            self["asset"] = Asset(amount["asset_id"], morphene_instance=self.morphene)
            self["symbol"] = self["asset"]["symbol"]
            self["amount"] = Decimal(amount["amount"]) / Decimal(10 ** self["asset"]["precision"])

        elif (amount and asset is None and isinstance(amount, dict) and "amount" in amount and "asset" in amount):
            self["asset"] = Asset(amount["asset"], morphene_instance=self.morphene)
            self["symbol"] = self["asset"]["symbol"]
            self["amount"] = Decimal(amount["amount"]) / Decimal(10 ** self["asset"]["precision"])



        elif isinstance(amount, (float)) and asset and isinstance(asset, Asset):
            self["amount"] = str(amount)
            self["asset"] = asset
            self["symbol"] = self["asset"]["symbol"]

        elif isinstance(amount, (integer_types,  Decimal)) and asset and isinstance(asset, Asset):
            self["amount"] = amount
            self["asset"] = asset
            self["symbol"] = self["asset"]["symbol"]
            
        elif isinstance(amount, (float)) and asset and isinstance(asset, dict):
            self["amount"] = str(amount)
            self["asset"] = asset
            self["symbol"] = self["asset"]["symbol"]

        elif isinstance(amount, (integer_types, Decimal)) and asset and isinstance(asset, dict):
            self["amount"] = amount
            self["asset"] = asset
            self["symbol"] = self["asset"]["symbol"]            

        elif isinstance(amount, (float)) and asset and isinstance(asset, string_types):
            self["amount"] = str(amount)
            self["asset"] = Asset(asset, morphene_instance=self.morphene)
            self["symbol"] = asset

        elif isinstance(amount, (integer_types, Decimal)) and asset and isinstance(asset, string_types):
            self["amount"] = amount
            self["asset"] = Asset(asset, morphene_instance=self.morphene)
            self["symbol"] = asset  
        elif amount and asset and isinstance(asset, Asset):
            self["amount"] = amount
            self["symbol"] = asset["symbol"]
            self["asset"] = asset
        elif amount and asset and isinstance(asset, string_types):
            self["amount"] = amount
            self["asset"] = Asset(asset, morphene_instance=self.morphene)
            self["symbol"] = self["asset"]["symbol"]            
        else:
            raise ValueError
        if self.fixed_point_arithmetic:
            self["amount"] = quantize(self["amount"], self["asset"]["precision"])
        else:
            self["amount"] = Decimal(self["amount"])

    def copy(self):
        """ Copy the instance and make sure not to use a reference
        """
        return Amount(
            amount=self["amount"],
            asset=self["asset"].copy(),
            fixed_point_arithmetic=self.fixed_point_arithmetic,
            morphene_instance=self.morphene)

    @property
    def amount(self):
        """ Returns the amount as float
        """
        return float(self["amount"])

    @property
    def amount_decimal(self):
        """ Returns the amount as decimal
        """
        return self["amount"]

    @property
    def symbol(self):
        """ Returns the symbol of the asset
        """
        return self["symbol"]

    def tuple(self):
        return float(self), self.symbol

    @property
    def asset(self):
        """ Returns the asset as instance of :class:`morphene.asset.Asset`
        """
        if not self["asset"]:
            self["asset"] = Asset(self["symbol"], morphene_instance=self.morphene)
        return self["asset"]

    def json(self):
        return str(self)

    def __str__(self):
        amount = quantize(self["amount"], self["asset"]["precision"])
        return "{:.{prec}f} {}".format(
            amount,
            self["symbol"],
            prec=self["asset"]["precision"]
        )

    def __float__(self):
        if self.fixed_point_arithmetic:
            return float(quantize(self["amount"], self["asset"]["precision"]))
        else:
            return float(self["amount"])

    def __int__(self):
        amount = quantize(self["amount"], self["asset"]["precision"])
        return int(amount * 10 ** self["asset"]["precision"])

    def __add__(self, other):
        a = self.copy()
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"])
            a["amount"] += other["amount"]
        else:
            a["amount"] += Decimal(other)
        if self.fixed_point_arithmetic:
            a["amount"] = quantize(a["amount"], self["asset"]["precision"])
        return a

    def __sub__(self, other):
        a = self.copy()
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"])
            a["amount"] -= other["amount"]
        else:
            a["amount"] -= Decimal(other)
        if self.fixed_point_arithmetic:
            a["amount"] = quantize(a["amount"], self["asset"]["precision"])
        return a

    def __mul__(self, other):
        a = self.copy()
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"])
            a["amount"] *= other["amount"]
        else:
            a["amount"] *= Decimal(other)
        if self.fixed_point_arithmetic:
            a["amount"] = quantize(a["amount"], self["asset"]["precision"])
        return a

    def __floordiv__(self, other):
        a = self.copy()
        a["amount"] //= Decimal(other)
        if self.fixed_point_arithmetic:
            a["amount"] = quantize(a["amount"], self["asset"]["precision"])
        return a

    def __div__(self, other):
        a = self.copy()
        a["amount"] /= Decimal(other)
        if self.fixed_point_arithmetic:
            a["amount"] = quantize(a["amount"], self["asset"]["precision"])
        return a

    def __mod__(self, other):
        a = self.copy()
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"])
            a["amount"] %= other["amount"]
        else:
            a["amount"] %= Decimal(other)
        if self.fixed_point_arithmetic:
            a["amount"] = quantize(a["amount"], self["asset"]["precision"])
        return a

    def __pow__(self, other):
        a = self.copy()
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"])
            a["amount"] **= other["amount"]
        else:
            a["amount"] **= Decimal(other)
        if self.fixed_point_arithmetic:
            a["amount"] = quantize(a["amount"], self["asset"]["precision"])
        return a

    def __iadd__(self, other):
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"])
            self["amount"] += other["amount"]
        else:
            self["amount"] += Decimal(other)
        if self.fixed_point_arithmetic:
            self["amount"] = quantize(self["amount"], self["asset"]["precision"])
        return self

    def __isub__(self, other):
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"])
            self["amount"] -= other["amount"]
        else:
            self["amount"] -= Decimal(other)
        if self.fixed_point_arithmetic:
            self["amount"] = quantize(self["amount"], self["asset"]["precision"])
        return self

    def __imul__(self, other):
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"])
            self["amount"] *= other["amount"]
        else:
            self["amount"] *= Decimal(other)
        
        self["amount"] = quantize(self["amount"], self["asset"]["precision"])
        return self

    def __idiv__(self, other):
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"])
            return self["amount"] / other["amount"]
        else:
            self["amount"] /= Decimal(other)
        if self.fixed_point_arithmetic:
            self["amount"] = quantize(self["amount"], self["asset"]["precision"])
        return self

    def __ifloordiv__(self, other):
        if isinstance(other, Amount):
            self["amount"] //= other["amount"]
        else:
            self["amount"] //= Decimal(other)
        self["amount"] = quantize(self["amount"], self["asset"]["precision"])
        return self

    def __imod__(self, other):
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"])
            self["amount"] %= other["amount"]
        else:
            self["amount"] %= Decimal(other)
        if self.fixed_point_arithmetic:
            self["amount"] = quantize(self["amount"], self["asset"]["precision"])
        return self

    def __ipow__(self, other):
        if isinstance(other, Amount):
            self["amount"] **= other
        else:
            self["amount"] **= Decimal(other)
        if self.fixed_point_arithmetic:
            self["amount"] = quantize(self["amount"], self["asset"]["precision"])
        return self

    def __lt__(self, other):
        quant_amount = quantize(self["amount"], self["asset"]["precision"])
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"])
            return quant_amount < quantize(other["amount"], self["asset"]["precision"])
        else:
            return quant_amount < quantize((other or 0), self["asset"]["precision"])

    def __le__(self, other):
        quant_amount = quantize(self["amount"], self["asset"]["precision"])
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"])
            return quant_amount <= quantize(other["amount"], self["asset"]["precision"])
        else:
            return quant_amount <= quantize((other or 0), self["asset"]["precision"])

    def __eq__(self, other):
        quant_amount = quantize(self["amount"], self["asset"]["precision"])
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"])
            return quant_amount == quantize(other["amount"], self["asset"]["precision"])
        else:
            return quant_amount == quantize((other or 0), self["asset"]["precision"])

    def __ne__(self, other):
        quant_amount = quantize(self["amount"], self["asset"]["precision"])
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"])
            return self["amount"] != quantize(other["amount"], self["asset"]["precision"])
        else:
            return quant_amount != quantize((other or 0), self["asset"]["precision"])

    def __ge__(self, other):
        quant_amount = quantize(self["amount"], self["asset"]["precision"])
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"])
            return self["amount"] >= quantize(other["amount"], self["asset"]["precision"])
        else:
            return quant_amount >= quantize((other or 0), self["asset"]["precision"])

    def __gt__(self, other):
        quant_amount = quantize(self["amount"], self["asset"]["precision"])
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"])
            return quant_amount > quantize(other["amount"], self["asset"]["precision"])
        else:
            return quant_amount > quantize((other or 0), self["asset"]["precision"])

    __repr__ = __str__
    __truediv__ = __div__
    __truemul__ = __mul__
