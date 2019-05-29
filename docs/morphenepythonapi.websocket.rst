morphenepythonapi\.websocket
==================

This class allows subscribe to push notifications from the Morphene
node.

.. code-block:: python

    from pprint import pprint
    from morphenepythonapi.websocket import MorpheneWebSocket

    ws = MorpheneWebSocket(
        "wss://morphene.io/rpc",
        accounts=["initwitness"],
        on_block=print,
    )

    ws.run_forever()


.. autoclass:: morphenepythonapi.websocket.MorpheneWebSocket
    :members:
    :undoc-members:
    :private-members:
    :special-members:


