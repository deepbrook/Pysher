[![Build Status](https://travis-ci.org/nlsdfnbch/Pysher.svg?branch=master)](https://travis-ci.org/nlsdfnbch/Pysher)
Pysher
=============

`pysher` is a python module for handling pusher websockets. It is based on @ekulyk's `PythonPusherClient`. This fork is meant as 
a continuation of the project and is actively maintained. A key difference is the dropped support for pre-3.5 Python versions.

Installation
------------

Simply run `python setup.py install` - or install via pip `pip install pysher`.

This module depends on websocket-client module available from: <http://github.com/liris/websocket-client>

Example
-------

Example of using this pusher client to consume websockets::

    import pysher

    # Add a logging handler so we can see the raw communication data
    import logging
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    root.addHandler(ch)

    pusher = pysher.Pusher(appkey)

    # We can't subscribe until we've connected, so we use a callback handler
    # to subscribe when able
    def connect_handler(data):
        channel = pusher.subscribe('mychannel')
        channel.bind('myevent', callback)

    pusher.connection.bind('pusher:connection_established', connect_handler)
    pusher.connect()

    while True:
        # Do other things in the meantime here...
        time.sleep(1)

Sending pusher events to a channel can be done simply using the pusher client supplied by pusher.  You can get it here: <https://github.com/pusher/pusher-http-python>

    import pusher
    pusher.app_id = app_id
    pusher.key = appkey

    p = pusher.Pusher()
    p['mychannel'].trigger('myevent', 'mydata')

Thanks
------
A big thanks to @ekulyk for developing the [PythonPusherClient](https://github.com/ekulyk/PythonPusherClient) library.


Copyright
---------

MTI License - See LICENSE for details.

