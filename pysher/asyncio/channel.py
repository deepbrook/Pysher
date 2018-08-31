import asyncio
import hashlib
import hmac
import json

from collections import defaultdict
from typing import Callable, Tuple, Any

from pysher.asyncio.constants import SIG_SHUTDOWN


class AsyncChannel:
    """Asynchonous Consumer class processing pusher messages.

    It feeds off data coming over ``AsyncChannel.pipe``.
    """
    def __init__(self, name, queue, loop=None):
        """Instantiate an AsyncChannel instance.

        :param str name: name of the channel.
        :param asyncio.Queue queue:
            The queue over which we receive messages from the websocket.
        :param Optional[asyncio.EventLoop] loop: Optional asyncio.EventLoop() instance.
        """
        self.loop = loop or asyncio.get_event_loop()
        self.name = name
        self.q = queue

        self.callbacks = defaultdict(list)
        self._task = None

    def register_callback(self, event: str, func: Callable) -> None:
        """Register the given callback for the given event."""
        self.callbacks[event].append(func)

    def stop_processing(self):
        """Stop this channel, ceasing processing of events."""
        if self._task:
            self._task.cancel()

    def start_processing(self):
        """Start this channel, continuing processing of events."""
        self._task = self.loop.ensure_future(self.process)

    async def process(self):
        while True:
            channel, event, data = await self.q.get()
            for callback in self.callbacks[event]:
                self.loop.call_soon(callback, data)


class PrivateChannel(AsyncChannel):
    def __init__(self, name, queue, app_key, secret, socket_id, loop=None):
        """Instantiate a PrivateChannel instance.

        :param str name: name of the channel.
        :param asyncio.Queue queue:
            The queue over which we receive messages from the websocket.
        :param str app_key: The pusher app's key.
        :param bytes or str secret: Secret to use for authentication.
        :param str socket_id: Socket id, as assigned by pusher on connection.
        :param Optional[asyncio.EventLoop] loop: Optional asyncio.EventLoop() instance.
        """
        super(PrivateChannel, self).__init__(name, queue, loop)
        self.socket_id = socket_id
        self.secret = secret.encode('UTF-8') if isinstance(secret, str) else secret
        self.key = app_key

    def _generate_subject(self) -> bytes:
        return "{}:{}".format(self.socket_id, self.name).encode('UTF-8')

    def generate_token(self) -> str:
        """Generate a token for authentication on this channel."""
        subject = self._generate_subject()
        h = hmac.new(self.secret, subject, hashlib.sha256)
        auth_key = "{}:{}".format(self.key, h.hexdigest())

        return auth_key


class EncryptedPrivateChannel(PrivateChannel):
    def __init__(self, name, queue, app_key, secret, socket_id, master_key, loop=None):
        super(EncryptedPrivateChannel, self).__init__(name, queue, app_key, secret, socket_id, loop)
        self.master_key = master_key
        raise NotImplementedError


class PresenceChannel(PrivateChannel):
    def __init__(self, name, queue, app_key, secret, socket_id, user_data=None, loop=None):
        """Instantiate a PresenceChannel instance.

        :param str name: name of the channel.
        :param asyncio.Queue queue:
            The queue over which we receive messages from the websocket.
        :param str app_key: The pusher app's key.
        :param bytes or str secret: Secret to use for authentication.
        :param str socket_id: Socket id, as assigned by pusher on connection.
        :param Optional[Dict] user_data: User data to assign to the current user.
        :param Optional[asyncio.EventLoop] loop: Optional asyncio.EventLoop() instance.
        """
        super(PresenceChannel, self).__init__(name, queue, app_key, secret, socket_id, loop)
        self.user_data = user_data or {}

    def _generate_subject(self) -> bytes:
        subject = "{}:{}:{}".format(self.socket_id, self.name, json.dumps(self.user_data))
        return subject.encode('UTF-8')
