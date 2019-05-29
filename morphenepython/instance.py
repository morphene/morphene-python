# This Python file uses the following encoding: utf-8
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import object
import morphenepython as mph


class SharedInstance(object):
    """Singelton for the MorpheneClient Instance"""
    instance = None
    config = {}


def shared_morphene_instance():
    """ This method will initialize ``SharedInstance.instance`` and return it.
        The purpose of this method is to have offer single default
        MorpheneClient instance that can be reused by multiple classes.

        .. code-block:: python

            from morphenepython.account import Account
            from morphenepython.instance import shared_morphene_instance

            account = Account("test")
            # is equivalent with
            account = Account("test", morphene_instance=shared_morphene_instance())

    """
    if not SharedInstance.instance:
        clear_cache()
        SharedInstance.instance = mph.MorpheneClient(**SharedInstance.config)
    return SharedInstance.instance


def set_shared_morphene_instance(morphene_instance):
    """ This method allows us to override default MorpheneClient instance for all users of
        ``SharedInstance.instance``.

        :param MorpheneClient morphene_instance: MorpheneClient instance
    """
    clear_cache()
    SharedInstance.instance = morphene_instance


def clear_cache():
    """ Clear Caches
    """
    from .blockchainobject import BlockchainObject
    BlockchainObject.clear_cache()


def set_shared_config(config):
    """ This allows to set a config that will be used when calling
        ``shared_morphene_instance`` and allows to define the configuration
        without requiring to actually create an instance
    """
    if not isinstance(config, dict):
        raise AssertionError()
    SharedInstance.config.update(config)
    # if one is already set, delete
    if SharedInstance.instance:
        clear_cache()
        SharedInstance.instance = None
