[![PyPI version](https://badge.fury.io/py/Pysher.svg)](https://badge.fury.io/py/Pysher)

# Pysher

`pysher` is a python module for handling pusher websockets. It is based on @ekulyk's `PythonPusherClient`. 
 A key difference is the dropped support for pre-3.5 Python versions.

This fork is meant as a continuation of the project, and is currently in **maintenance mode**.

The author is no longer actively using the library, but PRs including fixes, updates and features
are welcome and encouraged.

## Installation

Simply run `python setup.py install` - or install via pip `pip install pysher`.

This module depends on websocket-client module available from: <http://github.com/websocket-client/websocket-client>

## Example

Example of using this pusher client to consume websockets:

```python

import pysher

# Add a logging handler so we can see the raw communication data
import logging

root = logging.getLogger()
root.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
root.addHandler(ch)

pusher = pysher.Pusher(appkey)


def my_func(*args, **kwargs):
 print("processing Args:", args)
 print("processing Kwargs:", kwargs)


# We can't subscribe until we've connected, so we use a callback handler
# to subscribe when able
def connect_handler(data):
 channel = pusher.subscribe('mychannel')
 channel.bind('myevent', my_func)


pusher.connection.bind('pusher:connection_established', connect_handler)
pusher.connect()

while True:
 # Do other things in the meantime here...
 time.sleep(1)
```

Sending pusher events to a channel can be done simply using the pusher client supplied by pusher.  You can get it here: <https://github.com/pusher/pusher-http-python>

    import pusher
    pusher.app_id = app_id
    pusher.key = appkey

    p = pusher.Pusher()
    p['mychannel'].trigger('myevent', 'mydata')
    
## Performance
Pysher relies on websocket-client (websocket-client on pyPI, websocket import in code), which by default does utf5 validation in pure python. This is somewhat cpu hungry for lot's of messages (100's of KB/s or more). To optimize this validation consider installing the wsaccel module from pyPI to let websocket-client use C-compiled utf5 validation methods (websocket does this automatically once wsaccel is present and importable).

## Thanks
A big thanks to @ekulyk for developing the [PythonPusherClient](https://github.com/ekulyk/PythonPusherClient) library,
as well as the developers contributing bug-fixes, patches and other PRs to the project <3.
You can find them listed next to their contributed change in the Changelog section.

## Copyright

MTI License - See LICENSE for details.

# Changelog
## Version 1.0.8
### Fixed
 - #70 Allow remote authentication without need of secret, thanks to @[Matisilva](https://github.com/matisilva)

## Version 1.0.6
### Fixed
 - #55 Allow data fields to be empty for other events, too, thanks to @[Rubensei](https://github.com/Rubensei)

## Version 1.0.5
### Fixed
 - #53 Allow data fields to be empty, thanks to @[Rubensei](https://github.com/Rubensei)

## Version 1.0.4
### Fixed
 - Reverts a patch introduced in 1.0.3 

## Version 1.0.2
### Fixed
 - #38 Fix missing `ẁs` arg for websocket app callbacks, thanks to @[squgeim](https://github.com/squgeim)

## Version 1.0.0
### Updated
- #35 Support websocket-client >0.48 only and fix reconnect error, thanks to @[agronholm](https://github.com/agronholm)

**This change may break existing setups and is backwards-incompatible!**

## Version 0.5.0
### Added
 - #14 Added support for cluster configuration, thanks to @[Yvictor](https://github.com/Yvictor)

### Fixed
 - #30 Require websocket-client version 0.48 or earlier.
 - #24 Signature generation now works as expected, thanks to @[agronholm](https://github.com/agronholm)
 - #31 Name threads of the pysher lib for better debugging, thanks to @[caliloo](https://github.com/caliloo)

## Version 0.4.2
### Fixed:
 - #11 Global Logger settings no longer overridden in Connection logger

## Version 0.4.0
### Added:
 - #8 Add support for WebSocket over HTTP proxy, thanks to @[1tgr](https://github.com/1tgr)

## Version 0.3.0
### Added:
 - #7 Auto-resubscribe to channels after reconnecting, thanks to @[pinealan](https://github.com/pinealan)

### Fixed:
- #4, #5 Updated references to the library name, thanks to @[deanmaniatis](https://github.com/deanmaniatis)

## Version 0.2.0  
### Added:
- #2 Allow for token generated by auth endpoint, thanks to @[wardcraigj](https://github.com/wardcraigj)
- #3 Allow instantiation with custom host, thanks to @[wardcraigj](https://github.com/wardcraigj)
