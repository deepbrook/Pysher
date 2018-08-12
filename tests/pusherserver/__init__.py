import sys

import json

from .pusherserverasyncio import Pusher
from autobahn.asyncio.websocket import WebSocketServerProtocol


class PusherTestServerProtocol(WebSocketServerProtocol):
    def onConnect(self, request):
        print("Server: onConnect")

    def onOpen(self):
        print("Server: onOpen")
        self.sendEvent('pusher:connection_established', data={'socket_id':'testid'})

    def onMessage(self, payload, isBinary):
        print("Server: onMessage")

        payload = json.loads(payload.decode('utf8'))

        self.handleEvent(payload)

    def onClose(self, wasClean, code, reason):
        print("Server: onClose")

    def sendEvent(self, event, data='', channel=None):
        print("Server: sendEvent %s" % event)

        message = {
            'event': event,
            'data': json.dumps(data)
        }

        if channel is not None:
            message['channel'] = channel

        self.sendMessage(json.dumps(message, ensure_ascii=False).encode('utf8'))

    def handleEvent(self, payload):
        if 'event' in payload:
            if payload['event'] == 'pusher:ping':
                self.sendEvent('pusher:pong')
            elif payload['event'] == 'pusher:subscribe':
                if ('data' in payload) and ('channel' in payload['data']):
                    ## For testing send a test message on subscription
                    if payload['data']['channel'] == 'test_channel':
                        self.sendEvent('test_event', {'message': 'test'}, 'test_channel')
            else:
                pass
        else:
            pass
