morphenepy CLI
~~~~~~~~~~
`morphenepy` is a convenient CLI utility that enables you to manage your wallet, transfer funds, check
balances and more.

Using the Wallet
----------------
`morphenepy` lets you leverage your BIP38 encrypted wallet to perform various actions on your accounts.

The first time you use `morphenepy`, you will be prompted to enter a password. This password will be used to encrypt
the `morphenepy` wallet, which contains your private keys.

You can change the password via `changewalletpassphrase` command.

::

    morphenepy changewalletpassphrase


From this point on, every time an action requires your private keys, you will be prompted ot enter
this password (from CLI as well as while using `morphenepython` library).

To bypass password entry, you can set an environment variable ``UNLOCK``.

::

    UNLOCK=mysecretpassword morphenepy transfer <recipient_name> 100 MORPH

Common Commands
---------------
First, you may like to import your Morphene account:

::

    morphenepy importaccount


You can also import individual private keys:

::

   morphenepy addkey <private_key>

Listing accounts:

::

   morphenepy listaccounts

Show balances:

::

   morphenepy balance account_name1 account_name2

Sending funds:

::

   morphenepy transfer --account <account_name> <recipient_name> 100 MORPH memo


Setting Defaults
----------------
For a more convenient use of ``morphenepy`` as well as the ``morphene-python`` library, you can set some defaults.
This is especially useful if you have a single Morphene account.

::

   morphenepy set default_account test

   morphenepy config
    +---------------------+--------+
    | Key                 | Value  |
    +---------------------+--------+
    | default_account     | test   |
    +---------------------+--------+

If you've set up your `default_account`, you can now send funds by omitting this field:

::

    morphenepy transfer <recipient_name> 100 MORPH memo

Commands
--------

.. click:: morphenepython.cli:cli
    :prog: morphenepy
    :show-nested:

morphenepy --help
-------------
You can see all available commands with ``morphenepy --help``

::

    ~ % morphenepy --help
   Usage: cli.py [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...

   Options:
     -n, --node TEXT        URL for public Morphene API (e.g.
                            https://morphene.io/rpc)
     -o, --offline          Prevent connecting to network
     -d, --no-broadcast     Do not broadcast
     -p, --no-wallet        Do not load the wallet
     -x, --unsigned         Nothing will be signed
     -e, --expires INTEGER  Delay in seconds until transactions are supposed to
                            expire (defaults to 60)
     -v, --verbose INTEGER  Verbosity
     --version              Show the version and exit.
     --help                 Show this message and exit.

   Commands:
     addkey                  Add key to wallet When no [OPTION] is given,...
     allow                   Allow an account/key to interact with your...
     approvewitness          Approve a witnesses
     balance                 Shows balance
     broadcast               broadcast a signed transaction
     changewalletpassphrase  Change wallet password
     config                  Shows local configuration
     createwallet            Create new wallet with a new password
     currentnode             Sets the currently working node at the first...
     delkey                  Delete key from the wallet PUB is the public...
     delprofile              Delete a variable in an account's profile
     disallow                Remove allowance an account/key to interact...
     disapprovewitness       Disapprove a witnesses
     importaccount           Import an account using a passphrase
     info                    Show basic blockchain info General...
     listaccounts            Show stored accounts
     listkeys                Show stored keys
     newaccount              Create a new account
     nextnode                Uses the next node in list
     parsewif                Parse a WIF private key without importing
     permissions             Show permissions of an account
     pingnode                Returns the answer time in milliseconds
     power                   Shows vote power and bandwidth
     powerdown               Power down (start withdrawing VESTS from...
     powerdownroute          Setup a powerdown route
     powerup                 Power up (MORPH to VESTS)
     set                     Set default_account or other values
     setprofile              Set a variable in an account's profile
     sign                    Sign a provided transaction with available...
     transfer                Transfer MORPH
     updatememokey           Update an account's memo key
     walletinfo              Show info about wallet
     witnesscreate           Create a witness
     witnesses               List witnesses
     witnessupdate           Change witness properties
