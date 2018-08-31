import logging
import asyncio
import json

import websockets

from pysher.asyncio.constants import SYSTEM_CHANNEL, ConnectionState
from pysher.exceptions import (
    ReconnectRequired,
    ReconnectRequiredLater,
    PusherConnectionError,
    PusherServiceUnavailable,
)


log = logging.getLogger(__name__)


class PusherWebsocketProtocol(websockets.WebSocketClientProtocol):
    """Protocol Version 7."""

    VERSION = 7

    def __init__(self, *args, **kwargs):
        super(PusherWebsocketProtocol, self).__init__(*args, **kwargs)
        self.pusher_state = ConnectionState()
        self.pusher_system_events = {
            'pusher:connection_established': self._pusher_conn_opened,
            'pusher:connection_failed': self._pusher_conn_failed,
            'pusher:ping': self._ping_handler,
            'pusher:error': self._pusher_error,
        }
    # Protocol extensions to update the pusher state.

    def _pusher_conn_opened(self, data):
        self.socket_id = data['socket_id']
        self.pusher_state.update(ConnectionState.CONNECTED)

    def _pusher_conn_failed(self, data):
        self.pusher_state.update(ConnectionState.FAILED)

    def _pusher_error(self, data):
        """Handle ``pusher:error`` event messages.

        We call PusherProtocol.close() if the code is < 4300, and also update the
        ``PusherProtocol.pusher_state`` attribute in this case. If the code is >4299,
        we log the ``code`` and its ``description`` and return without raising or
        updating the ``pusher_state`` attribute.

        ``PusherProtocol.close()`` called with any code other than 1000 or 1001
        will raise a ``websockets.ConnectionClosed`` exception. We will wrap this
        exception in our own exceptions, according to the status code.

        :raises pysher.exceptions.PusherConnectionError:
            If the error code is in range(4000, 4100).
        :raises pysher.exceptions.ReconnectRequired:
            If the error code is in range(4100, 4200).
        :raises pysher.exceptions.ReconnectRequiredLater:
            If the error code is in range(4200, 4300).
        """
        code, description = data['code'], data['description']
        code_to_exception_mapping = {
            (4000, 4100): (PusherConnectionError, ConnectionState.FAILED),
            (4100, 4200): (ReconnectRequired, ConnectionState.UNAVAILABLE),
            (4200, 4300): (ReconnectRequiredLater, ConnectionState.UNAVAILABLE),
        }

        if code not in range(4300, 4400):
            # Error codes outside of this range require us to either disconnect
            # entirely or reconnect immediately or a later time. To indicate this,
            # we'll use pysher's custom exceptions to make acting on these codes
            # easier.
            self.pusher_state.update(ConnectionState.UNAVAILABLE)
            for code_range, exception_and_state in code_to_exception_mapping.items():
                exception, new_state = exception_and_state
                if code in range(*code_range):
                    try:
                        self.close(code, reason=description)
                    except websockets.ConnectionClosed as exc:
                        self.pusher_state.update(new_state)
                        raise exception from exc

        # There was another type of error - likely an issue with the payload.
        # A reconnect is not required, hence we log this and leave it to the
        # user to act on it.
        log.error("Code {} - {}".format(code, description))

    # Pusher Protocol Extensions

    @asyncio.coroutine
    def _ping_handler(self, data):
        """Respond with a 'pusher:pong' message on emulated pings.

        This shouldn't be necessary as the websockets library implements a
        websocket draft that supports ping and pong messages. However, we keep
        this as a fall-back.
        """
        payload = {'event': 'pusher:pong', 'data': ''}
        self.send(json.dumps(payload))

    # Public API

    @asyncio.coroutine
    def send(self, data):
        """Send the given data via the websocket connection.

        :raises pysher.exceptions.PusherServiceUnavailable:
            If we're currently not connected to the Pusher service. Stores the
            current pusher state, as well as the weboscket state in the exception
            instance.

        .. Note::

            This does not imply that we are not connected to the pusher server.
            An established websocket connection may exist at this point - however,
            it is possible that the pusher application is currently unavailable.

        :raises websocket.ConnectionClosed: If the weboscket is closed already.
        """
        pusher_state = self.pusher_state.current()
        if pusher_state is ConnectionState.CONNECTED:
            return super(PusherWebsocketProtocol, self).send(data)
        else:
            raise PusherServiceUnavailable(pusher_state, self.state)

    @asyncio.coroutine
    def recv(self):
        """Receive a message from the websocket.

        Handle Pusher Protocol-related messages here, if able.

        :raises websockets.exceptions.ConnectionClosed:
            If there was an error during the super().recv() call.
        :raises pysher.exceptions.PusherConnectionError:
            There was an error when connecting to pusher services, and we cannot
            reconnect without a change to the configuration.
        :raises pysher.exceptions.ReconnectRequired:
            If we need to reconnect and can do so immediately.
        :raises pysher.exceptions.ReconnectRequiredLater:
            If we need to reconnect, but need to wait some time to do so. The
            default wait time is 2s, and this is stored in the exception's
            ``after`` attribute.
        :rtype: Tuple[str, str, Any]
        """
        try:
            message = super(PusherWebsocketProtocol, self).recv()
        except websockets.ConnectionClosed:
            # This exception may be raised due to normal disconnect,
            # protocol error or network error.
            self.pusher_state.update(ConnectionState.CONNECTION_CLOSED)
            raise

        # Pusher sends json-encoded strings, and double-encodes each message's
        # `data` field as json as well.
        # Each message has at least an event and a data field (albeit the latter
        # may be empty). `channel` fields are optional.
        # Reference:
        #     https://pusher.com/docs/pusher_protocol#events
        parsed_msg = json.loads(message)
        channel, event = parsed_msg.get('channel', SYSTEM_CHANNEL), parsed_msg['event']
        data = json.loads(parsed_msg['data'])

        if channel is SYSTEM_CHANNEL:
            # This may be a system message we can handle right away.
            log_str = "Received:: event:{!r} - data:{!r}".format(event, data)
            try:
                self.pusher_system_events[event](data)
            except KeyError:
                log.info("{} (unhandled)".format(log_str))
            else:
                log.info("{} (handled)".format(log_str))
        return channel, event, data
