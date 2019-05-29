*************
Configuration
*************

The morphenepython library comes with its own local configuration database
that stores information like

* API node URLs
* default account name
* the encrypted master password
* the default voting weight
* if keyring should be used for unlocking the wallet

and potentially more.

You can access those variables like a regular dictionary by using

.. code-block:: python

    from morphenepython import MorpheneClient
    mph = MorpheneClient()
    print(mph.config.items())

Keys can be added and changed like they are for regular dictionaries.

If you don't want to load the :class:`morphenepython.morphene.MorpheneClient` class, you
can load the configuration directly by using:

.. code-block:: python

    from morphenepython.storage import configStorage as config

It is also possible to access the configuration with the commandline tool `morphenepy`:

.. code-block:: bash

    morphenepy config

API node URLs
-------------

The default node URLs which will be used when  `node` is  `None` in :class:`morphenepython.morphene.MorpheneClient` class
is stored in `config["nodes"]` as string. The list can be get and set by:

.. code-block:: python

    from morphenepython import MorpheneClient
    mph = MorpheneClient()
    node_list = mph.get_default_nodes()
    node_list = node_list[1:] + [node_list[0]]
    mph.set_default_nodes(node_list)

morphenepy can also be used to set nodes:

.. code-block:: bash

        morphenepy set nodes wss://morphene.io/rpc
        morphenepy set nodes "['wss://morphene.io/rpc', 'wss://morphene.io/rpc2']"

The default nodes can be reset to the default value. When the first node does not
answer, mph should be set to the offline mode. This can be done by:

.. code-block:: bash

        morphenepy -o set nodes ""

or

.. code-block:: python

    from morphenepython import MorpheneClient
    mph = MorpheneClient(offline=True)
    mph.set_default_nodes("")

Default account
---------------

The default account name is used in some functions, when no account name is given.
It is also used in  `morphenepy` for all account related functions.

.. code-block:: python

    from morphenepython import MorpheneClient
    mph = MorpheneClient()
    mph.set_default_account("test")
    mph.config["default_account"] = "test"

or by morphenepy with

.. code-block:: bash

        morphenepy set default_account test


Setting password_storage
------------------------

The password_storage can be set to:

* environment, this is the default setting. The master password for the wallet can be provided in the environment variable `UNLOCK`.
* keyring (when set with morphenepy, it asks for the wallet password)

.. code-block:: bash

        morphenepy set password_storage environment
        morphenepy set password_storage keyring



Environment variable for storing the master password
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When `password_storage` is set to `environment`, the master password can be stored in `UNLOCK`
for unlocking automatically the wallet.

Keyring support for morphenepy and wallet
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to use keyring for storing the wallet password, the following steps are necessary:

* Install keyring: `pip install keyring`
* Change `password_storage` to `keyring` with `morphenepy` and enter the wallet password.

It also possible to change the password in the keyring by

.. code-block:: bash

    python -m keyring set morphene wallet

The stored master password can be displayed in the terminal by

.. code-block:: bash

    python -m keyring get morphene wallet

When keyring is set as `password_storage` and the stored password in the keyring
is identically to the set master password of the wallet, the wallet is automatically
unlocked everytime it is used.

Testing if unlocking works
~~~~~~~~~~~~~~~~~~~~~~~~~~

Testing if the master password is correctly provided by keyring or the `UNLOCK` variable:

.. code-block:: python

    from morphenepython import MorpheneClient
    mph = MorpheneClient()
    print(mph.wallet.locked())

When the output is False, automatic unlocking with keyring or the `UNLOCK` variable works.
It can also tested by morphenepy with

.. code-block:: bash

        morphenepy walletinfo --test-unlock

When no password prompt is shown, unlocking with keyring or the `UNLOCK` variable works.
