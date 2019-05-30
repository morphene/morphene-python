from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
#: Operation ids
ops = [
    'transfer',
    'transfer_to_vesting',
    'withdraw_vesting',
    'account_create',
    'account_update',
    'witness_update',
    'account_witness_vote',
    'account_witness_proxy',
    'pow',
    'set_withdraw_vesting_route',
    'claim_account',
    'create_claimed_account',
    'request_account_recovery',
    'recover_account',
    'change_recovery_account',
    'escrow_transfer',
    'escrow_dispute',
    'escrow_release',
    'escrow_approve',
    'decline_voting_rights',
    'reset_account',
    'set_reset_account',
    'delegate_vesting_shares',
    'account_create_with_delegation',
    'witness_set_properties',
    'producer_reward',
    'fill_vesting_withdraw',
    'shutdown_witness',
    'hardfork',
    'return_vesting_delegation',
]
operations = {o: ops.index(o) for o in ops}

ops_wls = [
    'transfer',
    'transfer_to_vesting',
    'withdraw_vesting',
    'account_create',
    'account_update',
    'account_forsale',
    'account_buying',
    'witness_update',
    'account_witness_vote',
    'account_witness_proxy',
    'set_withdraw_vesting_route',
    'shutdown_witness',
    'hardfork',
]
operations_wls = {o: ops_wls.index(o) for o in ops_wls}


def getOperationNameForId(i):
    """ Convert an operation id into the corresponding string
    """
    for key in operations:
        if int(operations[key]) is int(i):
            return key
    return "Unknown Operation ID %d" % i
