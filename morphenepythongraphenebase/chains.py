from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
default_prefix = "MPH"
known_chains = {
    "MORPHENE": {
        "chain_id": "720fc3f4eb2480c104539739bd9cb84db9e92c3a63cdf78254887d5ac2978a2f",
        "min_version": '0.1.0',
        "prefix": "MPH",
        "chain_assets": [
            {"asset": "MORPH", "symbol": "MORPH", "precision": 3, "id": 1},
            {"asset": "VESTS", "symbol": "VESTS", "precision": 6, "id": 2}
            # {"asset": "@@000000021", "symbol": "MORPH", "precision": 3, "id": 1},
            # {"asset": "@@000000037", "symbol": "VESTS", "precision": 6, "id": 2}
        ],
    },
    "MORPHTESTNET": {
        "chain_id": "720fc3f4eb2480c104539739bd9cb84db9e92c3a63cdf78254887d5ac2978a2f",
        "min_version": '0.2.0',
        "prefix": "TST",
        "chain_assets": [
            {"asset": "MORPH", "symbol": "TESTS", "precision": 3, "id": 1},
            {"asset": "VESTS", "symbol": "VESTS", "precision": 6, "id": 2}
        ],
    }
}
