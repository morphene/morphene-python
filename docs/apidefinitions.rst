Api Definitions
===============

broadcast_block
~~~~~~~~~~~~~~~
not implemented

broadcast_transaction
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.transactionbuilder import TransactionBuilder
    t = TransactionBuilder()
    t.broadcast()

broadcast_transaction_synchronous
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.transactionbuilder import TransactionBuilder
    t = TransactionBuilder()
    t.broadcast()

get_account_count
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.blockchain import Blockchain
    b = Blockchain()
    b.get_account_count()

get_account_history
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.account import Account
    acc = Account("initwitness")
    for h in acc.get_account_history(1,0):
        print(h)

get_active_witnesses
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.witness import Witnesses
    w = Witnesses()
    w.printAsTable()

get_block
~~~~~~~~~

.. code-block:: python

    from morphenepython.block import Block
    print(Block(1))

get_block_header
~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.block import BlockHeader
    print(BlockHeader(1))

get_chain_properties
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython import MorpheneClient
    stm = MorpheneClient()
    print(mph.get_chain_properties())

get_config
~~~~~~~~~~

.. code-block:: python

    from morphenepython import MorpheneClient
    stm = MorpheneClient()
    print(mph.get_config())

get_dynamic_global_properties
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython import MorpheneClient
    stm = MorpheneClient()
    print(mph.get_dynamic_global_properties())

get_escrow
~~~~~~~~~~

.. code-block:: python

    from morphenepython.account import Account
    acc = Account("initwitness")
    print(acc.get_escrow())

get_expiring_vesting_delegations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.account import Account
    acc = Account("initwitness")
    print(acc.get_expiring_vesting_delegations())

get_hardfork_version
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython import MorpheneClient
    stm = MorpheneClient()
    print(mph.get_hardfork_properties()["hf_version"])

get_key_references
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.account import Account
    from morphenepython.wallet import Wallet
    acc = Account("initwitness")
    w = Wallet()
    print(w.getAccountFromPublicKey(acc["posting"]["key_auths"][0][0]))

get_next_scheduled_hardfork
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython import MorpheneClient
    stm = MorpheneClient()
    print(mph.get_hardfork_properties())

get_ops_in_block
~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.block import Block
    b = Block(2e6, only_ops=True)
    print(b)

get_owner_history
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.account import Account
    acc = Account("initwitness")
    print(acc.get_owner_history())

get_potential_signatures
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.transactionbuilder import TransactionBuilder
    from morphenepython.blockchain import Blockchain
    b = Blockchain()
    block = b.get_current_block()
    trx = block.json()["transactions"][0]
    t = TransactionBuilder(trx)
    print(t.get_potential_signatures())

get_recovery_request
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.account import Account
    acc = Account("initwitness")
    print(acc.get_recovery_request())

get_required_signatures
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.transactionbuilder import TransactionBuilder
    from morphenepython.blockchain import Blockchain
    b = Blockchain()
    block = b.get_current_block()
    trx = block.json()["transactions"][0]
    t = TransactionBuilder(trx)
    print(t.get_required_signatures())

get_transaction
~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.blockchain import Blockchain
    b = Blockchain()
    print(b.get_transaction("6fde0190a97835ea6d9e651293e90c89911f933c"))

get_transaction_hex
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.blockchain import Blockchain
    b = Blockchain()
    block = b.get_current_block()
    trx = block.json()["transactions"][0]
    print(b.get_transaction_hex(trx))

get_version
~~~~~~~~~~~
not implemented

get_vesting_delegations
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.account import Account
    acc = Account("initwitness")
    for v in acc.get_vesting_delegations():
        print(v)

get_withdraw_routes
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.account import Account
    acc = Account("initwitness")
    print(acc.get_withdraw_routes())

get_witness_by_account
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.witness import Witness
    w = Witness("initwitness")
    print(w)

get_witness_count
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.witness import Witnesses
    w = Witnesses()
    print(w.witness_count)

get_witness_schedule
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython import MorpheneClient
    stm = MorpheneClient()
    print(mph.get_witness_schedule())

get_witnesses
~~~~~~~~~~~~~
not implemented
    
get_witnesses_by_vote
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.witness import WitnessesRankedByVote
    for w in WitnessesRankedByVote():
        print(w)

lookup_account_names
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.account import Account
    acc = Account("initwitness", full=False)
    print(acc.json())

lookup_accounts
~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.account import Account
    acc = Account("initwitness")
    for a in acc.get_similar_account_names(limit=100):
        print(a)

lookup_witness_accounts
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.witness import ListWitnesses
    for w in ListWitnesses():
        print(w)

verify_account_authority
~~~~~~~~~~~~~~~~~~~~~~~~
disabled and not implemented

verify_authority
~~~~~~~~~~~~~~~~

.. code-block:: python

    from morphenepython.transactionbuilder import TransactionBuilder
    from morphenepython.blockchain import Blockchain
    b = Blockchain()
    block = b.get_current_block()
    trx = block.json()["transactions"][0]
    t = TransactionBuilder(trx)
    t.verify_authority()
    print("ok")
