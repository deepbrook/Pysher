#!/usr/bin/env python

import sys
import time
import threading

import pysher
import pusherserver

try:
    import simplejson as json
except ImportError:
    import json

# Add a logging handler so we can see the raw communication data
import logging
root = logging.getLogger()
root.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
root.addHandler(ch)

PORT = 9000

SUCCESS = 0
ERR_FAILED = 1
ERR_TIMEOUT = 2

global client
global server
global exit_code


def test_channel_callback(data):
    global exit_code
    print("Client: %s" % data)

    data = json.loads(data)

    if 'message' in data:
        if data['message'] == "test":
            # Test successful
            exit_code = SUCCESS
            server.stop()
            sys.exit(exit_code)


def connect_handler(data):
    channel = client.subscribe("test_channel")
    channel.bind('test_event', test_channel_callback)


def stop_test():
    global exit_code

    exit_code = ERR_TIMEOUT

    client.disconnect()
    server.stop(fromThread=True)


if __name__ == '__main__':
    global client
    global server
    global exit_code

    exit_code = ERR_FAILED

    # If testing taking longer than N seconds, we have an issue.  This time
    # depends on the client reconnect interval most of all.
    timer = threading.Timer(10, stop_test)
    timer.daemon = True
    timer.start()

    # Set up our client and attempt to connect to the server
    appkey = 'appkey'
    pysher.Pusher.host = "127.0.0.1"
    client = pysher.Pusher(appkey, port=PORT, secure=False, reconnect_interval=1)

    print(client._build_url(secure=False, port=PORT))
    client.connection.bind('pusher:connection_established', connect_handler)
    client.connect()

    # Sleep a bit before starting the server - this will cause the clients
    # initial connect to fail, forcing it to use the retry mechanism
    time.sleep(2)

    # Start our pusher server on localhost
    server = pusherserver.Pusher(pusherserver.PusherTestServerProtocol, port=PORT)
    server.run()

    sys.exit(exit_code)
