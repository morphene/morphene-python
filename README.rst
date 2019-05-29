Morphene-Python - Official Python Library for the Morphene Blockchain
===============================================

Morphene-Python is the official python library for Morphene, which is forked from beem and heavily modified for Morphene. Morphene-Python includes `python-graphenelib`_.

Support & Documentation
=======================
You may find help in the  `morphene-telegram-channel`_. The Telegram channel can also be used to discuss things about Morphene.

Features of Morphene-Python
=================================================

* High unit test coverage
* Support for websocket nodes
* Node error handling and automatic node switching
* Complete documentation of morphenepy and all classes including all functions
* Works on read-only systems
* Own BlockchainObject class with cache
* Contains all broadcast operations
* Estimation of virtual account operation index from date or block number
* The command line tool morphenepy uses click and has more commands
* MorpheneNodeRPC can be used to execute even not implemented RPC-Calls

Installation
============
The minimal working python version is 2.7.x. or 3.4.x

For Debian and Ubuntu, please ensure that the following packages are installed:

.. code:: bash

    sudo apt-get install build-essential libssl-dev python-dev

For Fedora and RHEL-derivatives, please ensure that the following packages are installed:

.. code:: bash

    sudo yum install gcc openssl-devel python-devel

For OSX, please do the following::

    brew install openssl
    export CFLAGS="-I$(brew --prefix openssl)/include $CFLAGS"
    export LDFLAGS="-L$(brew --prefix openssl)/lib $LDFLAGS"

For Termux on Android, please install the following packages:

.. code:: bash

    pkg install clang openssl-dev python-dev

Signing and Verify can be fasten (200 %) by installing cryptography:

.. code:: bash

    pip install -U cryptography

or:

.. code:: bash

    pip install -U secp256k1prp

Install or update morphenepython by pip::

    pip install -U morphenepython

You can install morphenepython from this repository if you want the latest
but possibly non-compiling version::

    git clone https://github.com/morphene/morphene-python.git
    cd morphenepython
    python setup.py build

    python setup.py install --user

Run tests after install::

    pytest


Installing morphenepython with conda-forge
--------------------------------

Installing morphenepython from the conda-forge channel can be achieved by adding conda-forge to your channels with::

    conda config --add channels conda-forge

Once the conda-forge channel has been enabled, morphenepython can be installed with::

    conda install morphenepython

Signing and Verify can be fasten (200 %) by installing cryptography::

    conda install cryptography

morphenepython can be updated by::

    conda update morphenepython

CLI tool morphenepy
---------------
A command line tool is available. The help output shows the available commands:

    morphenepy --help

Stand alone version of CLI tool morphenepy
--------------------------------------
With the help of pyinstaller, a stand alone version of morphenepy was created for Windows, OSX and linux.
Each version has just to be unpacked and can be used in any terminal. The packed directories
can be found under release. Each release has a hash sum, which is created directly in the build-server
before transmitting the packed file. Please check the hash-sum after downloading.

Changelog
=========
Can be found in CHANGELOG.rst.

License
=======
This library is licensed under the MIT License.

Acknowledgements
================
`python-graphenelib`_ was created by Fabian Schuh (xeroc).


.. _python-graphenelib: https://github.com/xeroc/python-graphenelib
.. _Python: http://python.org
.. _morphene-telegram-channel: https://t.me/morphene_chat
