.. morphene-python documentation master file, created by
   sphinx-quickstart on Fri Jun  5 14:06:38 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. http://sphinx-doc.org/rest.html
   http://sphinx-doc.org/markup/index.html
   http://sphinx-doc.org/markup/para.html
   http://openalea.gforge.inria.fr/doc/openalea/doc/_build/html/source/sphinx/rest_syntax.html
   http://rest-sphinx-memo.readthedocs.org/en/latest/ReST.html

.. image:: _static/morphenepython-logo.svg
   :width: 300 px
   :alt: morphene-python
   :align: center

Welcome to Morphene-Python's documentation!
================================

Morphene is a blockchain-based, trust-less auction platform.

It is based on *Graphene* (tm), a blockchain technology stack (i.e.
software) that allows for fast transactions and ascalable blockchain
solution. In case of Morphene, it comes with decentralized auctions.

The Morphene-Python library has been designed to allow developers to easily
access its routines and make use of the network without dealing with all
the related blockchain technology and cryptography. This library can be
used to do anything that is allowed according to the Morphene
blockchain protocol.


About this Library
------------------

The purpose of *morphenepython* is to simplify development of products and
services that use the Morphene blockchain. It comes with

* its own (bip32-encrypted) wallet
* RPC interface for the Blockchain backend
* JSON-based blockchain objects (accounts, blocks, prices, markets, etc)
* a simple to use yet powerful API
* transaction construction and signing
* push notification API
* *and more*

Quickstart
----------

.. note:: All methods that construct and sign a transaction can be given
          the ``account=`` parameter to identify the user that is going
          to affected by this transaction, e.g.:
          
          * the source account in a transfer
          * the accout that buys/sells an asset in the exchange
          * the account whos collateral will be modified

         **Important**, If no ``account`` is given, then the
         ``default_account`` according to the settings in ``config`` is
         used instead.

.. code-block:: python

   from morphenepython import MorpheneClient
   mph = MorpheneClient()
   mph.wallet.unlock("wallet-passphrase")
   account = Account("test", morphene_instance=mph)
   account.transfer("<to>", "<amount>", "<asset>", "<memo>")

.. code-block:: python

   from morphenepython.blockchain import Blockchain
   blockchain = Blockchain()
   for op in blockchain.stream():
       print(op)

.. code-block:: python

   from morphenepython.block import Block
   print(Block(1))

.. code-block:: python

   from morphenepython.account import Account
   account = Account("test")
   print(account.balances)
   for h in account.history():
       print(h)

.. code-block:: python

   from morphenepython.morphene import MorpheneClient
   stm = MorpheneClient()
   mph.wallet.wipe(True)
   mph.wallet.create("wallet-passphrase")
   mph.wallet.unlock("wallet-passphrase")
   mph.wallet.addPrivateKey("512345678")
   mph.wallet.lock()


General
-------
.. toctree::
   :maxdepth: 1

   installation
   quickstart
   tutorials
   cli
   configuration
   apidefinitions
   modules
   contribute
   support
   indices



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
