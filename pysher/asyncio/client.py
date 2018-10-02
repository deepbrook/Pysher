import logging
import json
import asyncio

from typing import Dict, Optional, Any, Union, Type

import websockets

from pysher.asyncio.connection import PusherWebsocketProtocol
from pysher.asyncio.channel import AsyncChannel, PrivateChannel, PresenceChannel
from pysher.asyncio.constants import SYSTEM_CHANNEL, ConnectionState

log = logging.getLogger(__name__)

VERSION = '0.6.0'

Channel = Union[PrivateChannel, PresenceChannel, AsyncChannel]


class Pysher:
    """Pusher Channel Factory and client.

    Connects to the pusher services and spawns channel objects, which users may
    add callbacks to.
    """
    #: Client name as we register with Pusher.
    client_id = "Pysher"

    #: Protocol Version.
    protocol = 7

    def __init__(self, key: Union[str, bytes],
                 secret: str="",
                 host: str="ws.pusher.app",
                 secure: bool=True,
                 cluster: Optional[str]=None,
                 custom_port: Optional[int]=None,
                 user_data: Optional[Dict]=None,
                 loop: Optional[asyncio.AbstractEventLoop]=None,
                 custom_auth: Optional[Any]=None,
                 **conn_ops: Any):
        """Initialize the Pusher instance.

        :param str or bytes key: The pusher app key.
        :param bytes or str secret: secret required for authentication on private channels.
        :param str host: the host the pusher app you're trying to connect to is located at.
        :param bool secure: Whether or not to use a WebsocketSecure connection.
        :param Optional[str] cluster: The name of the cluster you'd like to use.
        :param Optional[int] custom_port: A custom port number you want to connect over.
        :param Optional[Dict] user_data: User data for presence channels.
        :param Optional[asyncio.EventLoop] loop: Custom asyncio event loop to use.
        :param Optional[Any] custom_auth: Custom auth value to pass on authentication.
        :param Any conn_ops:
            Kwargs supported by asyncio.create_connection() or websockets.connect().
        """
        # https://pusher.com/docs/clusters
        if cluster:
            self.host = "ws-{cluster}.pusher.com".format(cluster=cluster)
        else:
            self.host = host

        self.key = key
        self.secret = secret
        self.auth = custom_auth

        self.user_data = user_data or {}

        self.url = self._build_url(secure, custom_port)
        self.conn_ops = conn_ops

        self.connection = None
        self.channels = {}

        self.loop = loop or asyncio.get_event_loop()
        self._run_task = None

    def _setup_connection(self):
        """Create a websocket connection object."""
        self.connection = websockets.connect(
            self.url, create_protocol=PusherWebsocketProtocol, **self.conn_ops
        )

    def connect(self):
        """Create a websocket connection object and request a connection from Pusher."""
        self._setup_connection()
        self._run_task = self.loop.ensure_future(self.run)

    def disconnect(self):
        """Disconnect from Pusher and close the connection."""
        self._run_task.cancel()
        self.connection.close()

    @@property
    def state(self) -> str:
        """Get the current connection state.

        :returns:
            connection state; if no connection object exists, we return
            :attr:``ConnectionState.NOT_INITIALIZED``.
        :rtype: str
        """
        if self.connection:
            return self.connection.pusher_state()
        return ConnectionState.NOT_INITIALIZED

    @property
    def key_as_bytes(self) -> bytes:
        return self.key if isinstance(self.key, bytes) else self.key.encode('UTF-8')

    @property
    def secret_as_bytes(self) -> bytes:
        return self.secret if isinstance(self.secret, bytes) else self.secret.encode('UTF-8')

    def _build_url(self, secure: bool=True, custom_port: Optional[int]=None) -> str:
        """Build the url via which we're supposed to contact Pusher."""
        path = f"/app/{self.key}?client={self.client_id}&version={VERSION}&protocol={self.protocol}"
        protocol = "wss" if secure else "ws"
        port = custom_port or (443 if secure else 80)

        return f"{protocol}://{self.host}:{port}{path}"

    def _configure_channel(self, channel_cls: Type[Channel], channel_name: str) -> Channel:
        """Configure a new channel object."""
        channel_obj = channel_cls(
            channel_name,
            asyncio.Queue(),
            self.key,
            self.secret,
            self.connection.socket_id,
            loop=self.loop,
        )
        if channel_name.startswith('presence-'):
            channel_obj.user_data = self.user_data
        return channel_obj

    def _generate_subscription_payload_for_channel(self, channel_obj: Channel) -> dict:
        """Generate a subscription payload for the given channel."""
        payload = {'channel': channel_obj.name, 'event': 'pusher:subscribe'}
        if channel_obj.name.startswith(('presence-', 'private')):
            payload.update({'auth': self.auth or channel_obj.generate_toke()})
            if channel_obj.name.startswith('presence-'):
                payload.update({'user_data': self.user_data})
        return payload

    def subscribe(self, channel_name: str) -> Channel:
        """Subscribe to the given channel name and spawn a Channel instance."""
        if channel_name.startswith('private-'):
            channel_obj = self._configure_channel(PrivateChannel, channel_name)
        elif channel_name.startswith('presence-'):
            channel_obj = self._configure_channel(PresenceChannel, channel_name)
        else:
            channel_q = asyncio.Queue()
            channel_obj = AsyncChannel(channel_name, channel_q, self.loop)
        payload = self._generate_subscription_payload_for_channel(channel_obj)
        channel_obj.start_processing()
        self.connection.send(json.dumps(payload))
        self.channels[channel_name] = channel_obj

        return channel_obj

    async def run(self):
        """Execute the client main loop."""
        if not SYSTEM_CHANNEL in self.channels:
            sys_channel = AsyncChannel(SYSTEM_CHANNEL, asyncio.Queue(), self.loop)
            self.channels[SYSTEM_CHANNEL] = sys_channel
        while True:
            try:
                channel, event, data = await self.connection.recv()
            except websockets.ConnectionClosed:
                break
            log.info("RECEIVED: {'channel': {!r}, 'event': {!r}, 'data': {!r}")
            try:
                self.channels[channel].put((channel, event, data))
            except KeyError:
                continue

        for channel in self.channels:
            channel.stop_processing()
