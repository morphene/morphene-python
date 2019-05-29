Quickstart
==========

Morphene-Python
-----
The MorpheneClient object is the connection to the Morphene Blockchain.
By creating this object different options can be set.

.. note:: All init methods of morphenepython classes can be given
          the ``morphene_instance=`` parameter to assure that
          all objects use the same MorpheneClient object. When the
          ``morphene_instance=`` parameter is not used, the 
          MorpheneClient object is taken from get_shared_morphene_instance().

          :func:`morphenepython.instance.shared_morphene_instance` returns a global instance of MorpheneClient.
          It can be set by :func:`morphenepython.instance.set_shared_morphene_instance` otherwise it is created
          on the first call.

.. code-block:: python

   from morphenepython import MorpheneClient
   from morphenepython.account import Account
   stm = MorpheneClient()
   account = Account("test", morphene_instance=stm)

.. code-block:: python

   from morphenepython import MorpheneClient
   from morphenepython.account import Account
   from morphenepython.instance import set_shared_morphene_instance
   stm = MorpheneClient()
   set_shared_morphene_instance(stm)
   account = Account("test")

Wallet and Keys
---------------
Each account has the following keys:

* Active key (allows accounts to transfer, power up/down, voting for witness, create auctions, place bids)
* Memo key (Can be used to encrypt/decrypt memos)
* Owner key (The most important key, should not be used with morphenepython)

Outgoing operation, which will be stored in the Morphene Blockchain, have to be
signed by a private key. Private keys can be provided to morphenepython temporary or can be
stored encrypted in a sql-database (wallet).

.. note:: Before using the wallet the first time, it has to be created and a password has
          to set. The wallet content is available to morphenepy and all python scripts, which have
          access to the sql database file.

Creating a wallet
~~~~~~~~~~~~~~~~~
``mph.wallet.wipe(True)`` is only necessary when there was already an wallet created.

.. code-block:: python

   from morphenepython import MorpheneClient
   mph = MorpheneClient()
   mph.wallet.wipe(True)
   mph.wallet.unlock("wallet-passphrase")

Adding keys to the wallet
~~~~~~~~~~~~~~~~~~~~~~~~~
.. code-block:: python

   from morphenepython import MorpheneClient
   mph = MorpheneClient()
   mph.wallet.unlock("wallet-passphrase")
   mph.wallet.addPrivateKey("xxxxxxx")
   mph.wallet.addPrivateKey("xxxxxxx")

Using the keys in the wallet
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from morphenepython import MorpheneClient
   mph = MorpheneClient()
   mph.wallet.unlock("wallet-passphrase")
   account = Account("test", morphene_instance=mph)
   account.transfer("<to>", "<amount>", "<asset>", "<memo>")

Private keys can also set temporary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from morphenepython import MorpheneClient
   mph = MorpheneClient(keys=["xxxxxxxxx"])
   account = Account("test", morphene_instance=mph)
   account.transfer("<to>", "<amount>", "<asset>", "<memo>")

Receiving information about blocks, accounts, and witness
---------------------------------------------------------------------------------

Receive all Blocks from the Blockchain

.. code-block:: python

   from morphenepython.blockchain import Blockchain
   blockchain = Blockchain()
   for op in blockchain.stream():
       print(op)

Access one Block

.. code-block:: python

   from morphenepython.block import Block
   print(Block(1))

Access an account

.. code-block:: python

   from morphenepython.account import Account
   account = Account("test")
   print(account.balances)
   for h in account.history():
       print(h)

Access a witness

.. code-block:: python

   from morphenepython.witness import Witness
   witness = Witness("initwitness")
   print(witness.is_active)

Sending transaction to the blockchain
-------------------------------------

Sending a Transfer

.. code-block:: python

   from morphenepython import MorpheneClient
   mph = MorpheneClient()
   mph.wallet.unlock("wallet-passphrase")
   account = Account("test", morphene_instance=mph)
   account.transfer("null", 1, "MORPH", "test")
