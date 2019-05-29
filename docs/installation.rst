Installation
============
The minimal working python version is 2.7.x. or 3.4.x

For Debian and Ubuntu, please ensure that the following packages are installed:
        
.. code:: bash

    sudo apt-get install build-essential libssl-dev python-dev curl

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

Install pip (https://pip.pypa.io/en/stable/installing/):

.. code:: bash

   curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
   
   python get-pip.py

Signing and Verify can be fasten (200 %) by installing cryptography. Install cryptography with pip:

.. code:: bash

    pip install -U cryptography
    
Install morphenepython with pip:

.. code:: bash

    pip install -U morphenepython

Sometimes this does not work. Please try::

    pip3 install -U morphenepython

or::

    python -m pip install morphenepython

Manual installation
-------------------
    
You can install morphenepython from this repository if you want the latest
but possibly non-compiling version::

    git clone https://github.com/morphene/morphene-python.git
    cd morphene-python
    python setup.py build
    
    python setup.py install --user

Run tests after install::

    pytest


Enable Logging
--------------

Add the following for enabling logging in your python script::

    import logging
    log = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

When you want to see only critical errors, replace the last line by::

    logging.basicConfig(level=logging.CRITICAL)
