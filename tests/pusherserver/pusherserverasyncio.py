# Python >3.4
import asyncio

from autobahn.asyncio.websocket import WebSocketServerFactory


class Pusher():
    def __init__(self, protocol, port=9000):
        self.factory = WebSocketServerFactory()
        self.factory.protocol = protocol

        self.port = port

        # ASYNCIO server params
        self.loop = None
        self.coro = None
        self.server = None

    def run(self):
        self.loop = asyncio.get_event_loop()
        self.coro = self.loop.create_server(self.factory, '127.0.0.1', self.port)
        self.server = self.loop.run_until_complete(self.coro)

        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.server.close()
            self.loop.close()

    def stop(self, **kwargs):
        if self.loop and self.loop.is_running():
            self.loop.stop()
